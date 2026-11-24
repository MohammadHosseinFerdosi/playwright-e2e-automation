"""BDD steps for Nemo cash-out predict + register — thin orchestration."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_bdd import parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.services.debit import nemo_cash_out_asserts as nemo_assert
from tests.services.debit import nemo_cash_out_fixtures as fixtures
from tests.services.debit.nemo_cash_out import (
    NemoCashOutContext,
    NemoCashOutFlow,
    store_predict_case,
)
from tests.services.debit.nemo_predict_gherkin import (
    assert_cash_out_fee_prediction,
    predict_cash_out_fee,
)
from tests.services.debit.nemo_register_gherkin import (
    assert_cash_out_register,
    register_iban_cash_out,
    register_unknown_cash_out_detail,
)
from tests.services.debit.nemo_secrets import NemoSecrets
from tests.services.debit.nemo_wallet_db import NemoWalletDb

scenarios("../features/debit/nemo_predict.feature")
scenarios("../features/debit/nemo_cash_out.feature")

pytestmark = pytest.mark.xdist_group("debit_bank_transfer")


@pytest.fixture
def nemo_secrets_ready() -> NemoSecrets:
    """Load Nemo secrets or skip."""
    return fixtures.load_nemo_secrets_or_skip()


@pytest.fixture
def nemo_wallet(
    nemo_secrets_ready: NemoSecrets,
) -> Generator[NemoWalletDb | None, None, None]:
    """Open wallet_db when mongo_uri is set."""
    yield from fixtures.open_nemo_wallet(nemo_secrets_ready)


@pytest.fixture
def nemo_flow(
    microservice_client: ApiClient,
    nemo_secrets_ready: NemoSecrets,
    nemo_wallet: NemoWalletDb | None,
) -> NemoCashOutFlow:
    """Nemo cash-out flow bound to MS client."""
    return fixtures.build_nemo_flow(microservice_client, nemo_secrets_ready, nemo_wallet)


@pytest.fixture
def nemo_ctx(nemo_flow: NemoCashOutFlow) -> NemoCashOutContext:
    """Per-scenario context."""
    return NemoCashOutContext(secrets=nemo_flow.secrets)


@when(parsers.re(r"^the customer predicts a cash-out fee (?P<mode>[A-Za-z0-9 -]+)$"))
def _(mode: str, nemo_flow: NemoCashOutFlow, nemo_ctx: NemoCashOutContext) -> None:
    predict_cash_out_fee(nemo_flow, nemo_ctx, mode)


@when("DSH runs the cash-out fee secure-store diagnostic")
def _(nemo_flow: NemoCashOutFlow, nemo_ctx: NemoCashOutContext) -> None:
    store_predict_case(nemo_flow, nemo_ctx, "card secure store diagnostic")


@when(
    parsers.re(
        r"^the customer registers "
        r"(?P<mode>(?:(?! onto | on the )[A-Za-z0-9 -])+)$"
    )
)
def _(mode: str, nemo_flow: NemoCashOutFlow, nemo_ctx: NemoCashOutContext) -> None:
    register_iban_cash_out(nemo_flow, nemo_ctx, mode)


@when("the customer asks for cash-out detail with an unknown tracking code")
def _(nemo_flow: NemoCashOutFlow, nemo_ctx: NemoCashOutContext) -> None:
    register_unknown_cash_out_detail(nemo_flow, nemo_ctx)


@then(parsers.re(r"^the cash-out fee prediction (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, nemo_ctx: NemoCashOutContext) -> None:
    assert_cash_out_fee_prediction(nemo_ctx, outcome)


@then("the secure-store diagnostic is recorded")
def _(nemo_ctx: NemoCashOutContext) -> None:
    nemo_assert.assert_predict_case(nemo_ctx, "card secure store diagnostic")


@then(parsers.re(r"^the Nemo cash-out (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, nemo_ctx: NemoCashOutContext) -> None:
    assert_cash_out_register(nemo_ctx, outcome)
