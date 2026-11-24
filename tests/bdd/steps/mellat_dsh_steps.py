"""BDD steps for Mellat DSH (SET-T448..T475) — thin orchestration only."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow
from tests.services.debit.mellat_dsh_gherkin import (
    assert_mellat_dsh_outcome,
    run_mellat_dsh_act,
    run_mellat_dsh_concurrent,
    run_mellat_dsh_request,
    run_mellat_dsh_requests,
    run_mellat_dsh_staff,
    run_mellat_dsh_tracking,
)

scenarios("../features/debit/mellat_dsh.feature")

pytestmark = pytest.mark.xdist_group("debit_bank_transfer")


@when(parsers.re(r"^the customer requests a Mellat cash-out (?P<mode>[A-Za-z0-9 -]+)$"))
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_mellat_dsh_request(bt_flow, bt_ctx, mode)


@when(parsers.re(r"^the customer requests Mellat cash-outs (?P<mode>[A-Za-z0-9 -]+)$"))
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_mellat_dsh_requests(bt_flow, bt_ctx, mode)


@when(
    parsers.re(
        r"^the customer (?P<mode>(?:inquires|reuses|routes) "
        r"[A-Za-z0-9 -]*Mellat[A-Za-z0-9 -]*tracking[A-Za-z0-9 -]*)$"
    )
)
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_mellat_dsh_tracking(bt_flow, bt_ctx, mode)


@when(
    parsers.re(
        r"^the customer (?P<mode>(?:executes|completes) "
        r"[A-Za-z0-9 -]*Mellat cash-out[A-Za-z0-9 -]*)$"
    )
)
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_mellat_dsh_act(bt_flow, bt_ctx, mode)


@when(
    parsers.re(
        r"^DSH (?P<mode>(?!splits |checks that |looks up |audits )"
        r"[A-Za-z0-9 -]*Mellat[A-Za-z0-9 -]*)$"
    )
)
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_mellat_dsh_staff(bt_flow, bt_ctx, mode)


@when("customers concurrently execute the same Mellat cash-out")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_mellat_dsh_concurrent(bt_flow, bt_ctx)


@then(parsers.re(r"^the Mellat cash-out (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, bt_ctx: BankTransferContext) -> None:
    assert_mellat_dsh_outcome(bt_ctx, outcome)
