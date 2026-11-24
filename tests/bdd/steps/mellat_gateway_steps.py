"""BDD steps for debit Mellat INTERNAL gateway — thin orchestration only."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from tests.services.debit import bank_transfer_asserts as bt_assert
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow
from tests.services.debit.mellat_gateway_gherkin import (
    assert_mellat_internal_route,
    run_mellat_gateway,
)

scenarios("../features/debit/mellat_gateway.feature")

pytestmark = pytest.mark.xdist_group("debit_bank_transfer")


@when("DSH runs the bank-transfer environment preflight")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    bt_flow.run_environment_preflight(bt_ctx)


@when("DSH checks that the Mellat internal gateway client is active")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    bt_flow.store_mellat_client_active(bt_ctx)


@when(
    parsers.re(
        r"^a customer (?P<mode>(?:routes (?!a Mellat transfer with )|"
        r"executes |inquires |reuses )[A-Za-z0-9 -]*Mellat[A-Za-z0-9 -]*)$"
    )
)
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_mellat_gateway(bt_flow, bt_ctx, mode)


@when(parsers.re(r"^a customer routes a Mellat transfer with (?P<invalid_input>[A-Za-z0-9 ]+)$"))
def _(invalid_input: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    bt_flow.store_invalid_route(bt_ctx, case=invalid_input)


@when("DSH triggers the ACH scheduler test endpoints")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    bt_flow.store_scheduler_triggers(bt_ctx)


@then("the bank-transfer environment preflight succeeds")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_environment_preflight(bt_ctx)


@then("the Mellat internal gateway client is active")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_mellat_client_active(bt_ctx)


@then("the Mellat route contract includes a route journal")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_route_contract_with_journal(bt_ctx)


@then(parsers.re(r"^the Mellat internal route (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, bt_ctx: BankTransferContext) -> None:
    assert_mellat_internal_route(bt_ctx, outcome)


@then("the marker Mellat route stays initiated")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_mongo_initiated_after_marker_route(bt_ctx)


@then("the call is rejected because the transfer was not found")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_title_rejected(bt_ctx, expected_title="TRANSACTION_NOT_FOUND")


@then("the Mellat call does not return a server error")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_no_server_error(bt_ctx)


@then("none of the Mellat routes select ACH")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_never_ach_types(bt_ctx)


@then("the ACH scheduler test triggers succeed")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_scheduler_triggers_ok(bt_ctx)


@then("the same-bank Mellat route stays internal")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_same_bank_internal(bt_ctx)
