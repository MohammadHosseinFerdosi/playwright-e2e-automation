"""BDD steps for Melli + Mellat TREASURY direct-route — thin orchestration."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.services.debit.bank_transfer import BankTransferContext
from tests.services.debit.bank_transfer_direct import DirectRouteFlow
from tests.services.debit.bank_transfer_routing import BankTransferRoutingDb
from tests.services.debit.bank_transfer_secrets import require_bank_transfer_secrets
from tests.services.debit.direct_route_gherkin import (
    assert_mellat_direct_payout,
    assert_melli_direct_payout,
    request_direct_payout,
)

scenarios("../features/debit/melli_direct_route.feature")
scenarios("../features/debit/mellat_direct_route.feature")

pytestmark = pytest.mark.xdist_group("debit_bank_transfer")


@pytest.fixture
def melli_direct_flow(
    microservice_client: ApiClient,
) -> Generator[DirectRouteFlow, None, None]:
    """Melli TREASURY account snapshot/restore."""
    secrets = require_bank_transfer_secrets()
    routing = BankTransferRoutingDb(secrets)
    flow = DirectRouteFlow(microservice_client, routing, secrets, rail="melli")
    flow.prepare()
    yield flow
    flow.teardown()


@pytest.fixture
def mellat_direct_flow(
    microservice_client: ApiClient,
) -> Generator[DirectRouteFlow, None, None]:
    """Mellat direct-route clientIds snapshot/restore."""
    secrets = require_bank_transfer_secrets()
    routing = BankTransferRoutingDb(secrets)
    flow = DirectRouteFlow(microservice_client, routing, secrets, rail="mellat")
    flow.prepare()
    yield flow
    flow.teardown()


@pytest.fixture
def bt_ctx_melli(melli_direct_flow: DirectRouteFlow) -> BankTransferContext:
    """Per-scenario context for Melli direct-route."""
    return BankTransferContext(secrets=melli_direct_flow.secrets)


@pytest.fixture
def bt_ctx_mellat(mellat_direct_flow: DirectRouteFlow) -> BankTransferContext:
    """Per-scenario context for Mellat direct-route."""
    return BankTransferContext(secrets=mellat_direct_flow.secrets)


@given("Melli treasury can pay out over ACH")
def _(melli_direct_flow: DirectRouteFlow) -> None:
    melli_direct_flow.assert_ready()


@given("Mellat treasury can pay out over ACH")
def _(mellat_direct_flow: DirectRouteFlow) -> None:
    mellat_direct_flow.assert_ready()


@when(parsers.re(r"^treasury (?P<mode>[A-Za-z0-9 -]*Melli(?!t)[A-Za-z0-9 -]*)$"))
def _(
    mode: str,
    melli_direct_flow: DirectRouteFlow,
    bt_ctx_melli: BankTransferContext,
) -> None:
    request_direct_payout(melli_direct_flow, bt_ctx_melli, mode)


@when(parsers.re(r"^treasury (?P<mode>[A-Za-z0-9 -]*Mellat[A-Za-z0-9 -]*)$"))
def _(
    mode: str,
    mellat_direct_flow: DirectRouteFlow,
    bt_ctx_mellat: BankTransferContext,
) -> None:
    request_direct_payout(mellat_direct_flow, bt_ctx_mellat, mode)


@then(parsers.re(r"^the Melli payout (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(
    outcome: str,
    melli_direct_flow: DirectRouteFlow,
    bt_ctx_melli: BankTransferContext,
) -> None:
    assert_melli_direct_payout(melli_direct_flow, bt_ctx_melli, outcome)


@then(parsers.re(r"^the Mellat payout (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(
    outcome: str,
    mellat_direct_flow: DirectRouteFlow,
    bt_ctx_mellat: BankTransferContext,
) -> None:
    assert_mellat_direct_payout(mellat_direct_flow, bt_ctx_mellat, outcome)
