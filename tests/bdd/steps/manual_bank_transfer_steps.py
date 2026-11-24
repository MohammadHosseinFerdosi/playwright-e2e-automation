"""BDD steps for Manual portal gateway + DSH — thin orchestration only."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow
from tests.services.debit.manual_gherkin import (
    assert_manual_outcome,
    run_manual_act,
    run_manual_concurrent,
    run_manual_execute,
    run_manual_inquire,
    run_manual_request,
    run_manual_staff,
)

scenarios("../features/debit/manual_gateway.feature")
scenarios("../features/debit/manual_dsh.feature")

pytestmark = pytest.mark.xdist_group("debit_bank_transfer")


@when(parsers.re(r"^the customer requests (?P<mode>[A-Za-z0-9 -]*manual[A-Za-z0-9 -]*)$"))
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_manual_request(bt_flow, bt_ctx, mode)


@when(parsers.re(r"^the customer executes (?P<mode>[A-Za-z0-9 -]*manual[A-Za-z0-9 -]*)$"))
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_manual_execute(bt_flow, bt_ctx, mode)


@when(parsers.re(r"^the customer inquires (?P<mode>[A-Za-z0-9 -]*manual[A-Za-z0-9 -]*)$"))
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_manual_inquire(bt_flow, bt_ctx, mode)


@when(
    parsers.re(
        r"^the customer (?P<mode>(?:completes|routes) "
        r"[A-Za-z0-9 -]*manual[A-Za-z0-9 -]*)$"
    )
)
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_manual_act(bt_flow, bt_ctx, mode)


@when(
    parsers.re(
        r"^DSH (?P<mode>(?!splits |settles the manual cash-out and)"
        r"[A-Za-z0-9 -]*manual[A-Za-z0-9 -]*)$"
    )
)
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_manual_staff(bt_flow, bt_ctx, mode)


@when("DSH splits cash-out weights evenly between Manual and Mellat")
def _(bt_flow: BankTransferFlow) -> None:
    bt_flow.routing.split_gateway_weights({"manual": 50, "mellat": 50})


@when("customers concurrently execute the same manual cash-out")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_manual_concurrent(bt_flow, bt_ctx)


@then(parsers.re(r"^the manual cash-out (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, bt_ctx: BankTransferContext) -> None:
    assert_manual_outcome(bt_ctx, outcome)
