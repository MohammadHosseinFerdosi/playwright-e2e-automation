"""BDD steps for debit Mellat ACH PAYA — thin orchestration only."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow
from tests.services.debit.mellat_ach_gherkin import (
    assert_mellat_ach_outcome,
    run_mellat_ach,
)

scenarios("../features/debit/mellat_ach.feature")

pytestmark = pytest.mark.xdist_group("debit_bank_transfer")


@when(
    parsers.re(
        r"^a customer (?P<mode>(?:routes|executes|inquires) "
        r"[A-Za-z0-9 -]*(?:PAYA|ACH)[A-Za-z0-9 -]*)$"
    )
)
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_mellat_ach(bt_flow, bt_ctx, mode)


@when("customers concurrently route the same ACH tracking code")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    bt_flow.store_ach_concurrent_routes(bt_ctx)


@then(parsers.re(r"^the PAYA cash-out (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, bt_ctx: BankTransferContext) -> None:
    assert_mellat_ach_outcome(bt_ctx, outcome)
