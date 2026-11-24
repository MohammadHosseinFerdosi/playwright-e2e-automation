"""BDD steps for ft shahin CASH_OUT and TREASURY rails."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow
from tests.services.debit.bank_transfer_direct import DirectRouteFlow
from tests.services.debit.bank_transfer_ft_shahin_gherkin import (
    assert_ft_shahin_direct_payout,
    assert_ft_shahin_outcome,
    request_ft_shahin_direct_payout,
    run_ft_shahin_dsh,
    run_ft_shahin_inquire,
    run_ft_shahin_request,
    run_ft_shahin_route,
)
from tests.services.debit.bank_transfer_routing import BankTransferRoutingDb
from tests.services.debit.bank_transfer_secrets import require_bank_transfer_secrets

scenarios("../features/debit/shahin_saderat_internal.feature")
scenarios("../features/debit/shahin_saderat_ach.feature")
scenarios("../features/debit/shahin_saderat_rtgs.feature")
scenarios("../features/debit/shahin_saderat_statements.feature")
scenarios("../features/debit/shahin_saderat_direct.feature")

pytestmark = pytest.mark.xdist_group("debit_bank_transfer")


@pytest.fixture
def ft_shahin_direct_flow(
    microservice_client: ApiClient,
) -> Generator[DirectRouteFlow, None, None]:
    """Snapshot and restore the ft shahin TREASURY account."""
    secrets = require_bank_transfer_secrets()
    routing = BankTransferRoutingDb(secrets)
    flow = DirectRouteFlow(microservice_client, routing, secrets, rail="ft_shahin")
    flow.prepare()
    yield flow
    flow.teardown()


@pytest.fixture
def bt_ctx_ft_shahin(ft_shahin_direct_flow: DirectRouteFlow) -> BankTransferContext:
    """Per-scenario context for ft shahin direct-route."""
    return BankTransferContext(secrets=ft_shahin_direct_flow.secrets)


@given(parsers.re(r"^ft shahin treasury can pay out over (?P<rail>ACH|internal)$"))
def _(ft_shahin_direct_flow: DirectRouteFlow, rail: str) -> None:
    ft_shahin_direct_flow.set_ft_shahin_kind(rail)
    ft_shahin_direct_flow.assert_ready()


@when(parsers.re(r"^the customer requests a ft shahin cash-out with (?P<mode>[A-Za-z0-9 -]+)$"))
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_ft_shahin_request(bt_flow, bt_ctx, mode)


@when(parsers.re(r"^the customer inquires that ft shahin cash-out$"))
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_ft_shahin_inquire(bt_flow, bt_ctx)


@when(
    parsers.re(
        r"^the customer routes the same ft shahin cash-out twice with (?P<mode>[A-Za-z0-9 -]+)$"
    )
)
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_ft_shahin_route(bt_flow, bt_ctx, mode)


@when(parsers.re(r"^DSH prepares a ft shahin cash-out with (?P<mode>[A-Za-z0-9 -]+)$"))
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_ft_shahin_dsh(bt_flow, bt_ctx, mode)


@when(parsers.re(r"^treasury requests a ft shahin payout with (?P<mode>[A-Za-z0-9 -]+)$"))
def _(
    mode: str,
    ft_shahin_direct_flow: DirectRouteFlow,
    bt_ctx_ft_shahin: BankTransferContext,
) -> None:
    request_ft_shahin_direct_payout(ft_shahin_direct_flow, bt_ctx_ft_shahin, mode)


@then(parsers.re(r"^the ft shahin cash-out (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, bt_ctx: BankTransferContext) -> None:
    assert_ft_shahin_outcome(bt_ctx, outcome)


@then(parsers.re(r"^the ft shahin payout (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(
    outcome: str,
    ft_shahin_direct_flow: DirectRouteFlow,
    bt_ctx_ft_shahin: BankTransferContext,
) -> None:
    assert_ft_shahin_direct_payout(ft_shahin_direct_flow, bt_ctx_ft_shahin, outcome)
