"""BDD steps for Nemo gateway + live e2e — thin orchestration."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.services.debit import nemo_cash_out_fixtures as co_fix
from tests.services.debit import nemo_e2e as e2e
from tests.services.debit import nemo_gateway as gw
from tests.services.debit import nemo_gateway_asserts as gw_assert
from tests.services.debit.bank_transfer import BankTransferFlow
from tests.services.debit.bank_transfer_routing import (
    BankTransferRoutingDb,
    bank_transfer_routing_session,
)
from tests.services.debit.bank_transfer_secrets import require_bank_transfer_secrets
from tests.services.debit.nemo_cash_out import NemoCashOutContext, NemoCashOutFlow
from tests.services.debit.nemo_e2e_gherkin import (
    assert_e2e_register_outcome,
    register_e2e_cash_out,
)
from tests.services.debit.nemo_gateway_gherkin import (
    ask_app_cash_out,
    ask_cash_out_route,
    assert_app_cash_out,
    assert_predicted_cash_out_route,
)
from tests.services.debit.nemo_secrets import NemoSecrets
from tests.services.debit.nemo_wallet_db import NemoWalletDb

scenarios("../features/debit/nemo_gateway.feature")
scenarios("../features/debit/nemo_e2e.feature")

pytestmark = pytest.mark.xdist_group("debit_bank_transfer")


@pytest.fixture
def nemo_secrets_ready() -> NemoSecrets:
    """Load Nemo secrets or skip."""
    return co_fix.load_nemo_secrets_or_skip()


@pytest.fixture
def nemo_wallet(
    nemo_secrets_ready: CHANGE_ME
) -> Generator[NemoWalletDb | None, None, None]:
    """Open wallet_db when mongo_uri is set."""
    yield from co_fix.open_nemo_wallet(nemo_secrets_ready)


@pytest.fixture
def nemo_flow(
    microservice_client: ApiClient,
    nemo_secrets_ready: CHANGE_ME
    nemo_wallet: NemoWalletDb | None,
) -> NemoCashOutFlow:
    """Nemo cash-out flow for e2e."""
    return co_fix.build_nemo_flow(microservice_client, nemo_secrets_ready, nemo_wallet)


@pytest.fixture
def nemo_ctx(nemo_flow: NemoCashOutFlow) -> NemoCashOutContext:
    """Per-scenario cash-out context."""
    return NemoCashOutContext(secrets=nemo_flow.secrets)


@pytest.fixture
def bt_routing() -> Generator[BankTransferRoutingDb, None, None]:
    """Bank-transfer routing Mongo with weight snapshot restore."""
    with bank_transfer_routing_session(require_bank_transfer_secrets()) as routing:
        yield routing


@pytest.fixture
def bt_flow(
    microservice_client: ApiClient,
    bt_routing: BankTransferRoutingDb,
) -> BankTransferFlow:
    """MS bank-transfer helpers sharing routing."""
    return BankTransferFlow(microservice_client, bt_routing, require_bank_transfer_secrets())


@pytest.fixture
def gateway_flow(
    app_client: ApiClient,
    microservice_client: ApiClient,
    nemo_secrets_ready: CHANGE_ME
) -> Generator[gw.NemoGatewayFlow, None, None]:
    """App-gateway prediction flow with weight snapshot restore."""
    bt = require_bank_transfer_secrets()
    routing = BankTransferRoutingDb(bt)
    flow = gw.NemoGatewayFlow(app_client, microservice_client, nemo_secrets_ready, bt, routing)
    flow.prepare()
    yield flow
    flow.teardown()


@pytest.fixture
def gateway_ctx(gateway_flow: gw.NemoGatewayFlow) -> gw.NemoGatewayContext:
    """Per-scenario gateway context."""
    return gw.NemoGatewayContext(nemo=gateway_flow.nemo, bt=gateway_flow.bt)


@given("the customer is signed in to the Nemo app")
def _(gateway_flow: gw.NemoGatewayFlow) -> None:
    gateway_flow.assert_ready()


@given(parsers.re(r"^the Nemo app will cash out through (?P<gateway>Mellat|Shahin|Manual)$"))
def _(gateway: str, gateway_flow: gw.NemoGatewayFlow) -> None:
    gateway_flow.pin_named_gateway(gateway)


@when(parsers.re(r"^the customer asks which cash-out route (?P<mode>[A-Za-z0-9 -]+)$"))
def _(mode: str, gateway_flow: gw.NemoGatewayFlow, gateway_ctx: gw.NemoGatewayContext) -> None:
    ask_cash_out_route(gateway_flow, gateway_ctx, mode)


@when(parsers.re(r"^the customer asks the app (?P<mode>[A-Za-z0-9 -]+)$"))
def _(mode: str, gateway_flow: gw.NemoGatewayFlow, gateway_ctx: gw.NemoGatewayContext) -> None:
    ask_app_cash_out(gateway_flow, gateway_ctx, mode)


@when("DSH splits Nemo cash-out weights evenly between Manual and Mellat")
def _(gateway_flow: gw.NemoGatewayFlow) -> None:
    gateway_flow.split_manual_mellat()


@when("the customer prepares a Mellat cash-out via the app then routes it")
def _(gateway_flow: gw.NemoGatewayFlow, gateway_ctx: gw.NemoGatewayContext) -> None:
    gw.store_gateway_case(gateway_flow, gateway_ctx, "gateway prep then mellat route")


@when(
    parsers.re(
        r"^the customer registers "
        r"(?P<mode>[A-Za-z0-9 -]*(?: onto | on the )[A-Za-z0-9 -]*)$"
    )
)
def _(
    mode: str,
    nemo_flow: NemoCashOutFlow,
    bt_flow: BankTransferFlow,
    bt_routing: BankTransferRoutingDb,
    nemo_ctx: NemoCashOutContext,
) -> None:
    register_e2e_cash_out(nemo_flow, bt_flow, bt_routing, nemo_ctx, mode)


@when("DSH settles the manual cash-out and compares Nemo detail")
def _(
    nemo_flow: NemoCashOutFlow,
    bt_flow: BankTransferFlow,
    bt_routing: BankTransferRoutingDb,
    nemo_ctx: NemoCashOutContext,
) -> None:
    e2e.store_e2e_case(nemo_flow, bt_flow, bt_routing, nemo_ctx, e2e.DSH_SETTLE_ALIGN)


@when("DSH audits a reference Mellat cash-out journey")
def _(
    nemo_flow: NemoCashOutFlow,
    bt_flow: BankTransferFlow,
    bt_routing: BankTransferRoutingDb,
    nemo_ctx: NemoCashOutContext,
) -> None:
    e2e.store_e2e_case(nemo_flow, bt_flow, bt_routing, nemo_ctx, "mellat reference audit")


@then(parsers.re(r"^the predicted cash-out route (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, gateway_ctx: gw.NemoGatewayContext) -> None:
    assert_predicted_cash_out_route(gateway_ctx, outcome)


@then(parsers.re(r"^the app cash-out (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, gateway_ctx: gw.NemoGatewayContext) -> None:
    assert_app_cash_out(gateway_ctx, outcome)


@then("the app-prepared Mellat cash-out routes successfully")
def _(gateway_ctx: gw.NemoGatewayContext) -> None:
    gw_assert.assert_gateway_case(gateway_ctx, "gateway prep then mellat route")


@then(parsers.re(r"^the registered cash-out (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, nemo_ctx: NemoCashOutContext) -> None:
    assert_e2e_register_outcome(nemo_ctx, outcome)


@then("Nemo detail aligns with bank-transfer inquiry")
def _(nemo_ctx: NemoCashOutContext) -> None:
    e2e.assert_e2e_case(nemo_ctx, e2e.DSH_SETTLE_ALIGN)


@then("the reference cash-out journey audits clean")
def _(nemo_ctx: NemoCashOutContext) -> None:
    e2e.assert_e2e_case(nemo_ctx, "mellat reference audit")
