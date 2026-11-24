"""BDD steps for debit bank-transfer gateway-common — thin orchestration only."""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, then, when

from tests.services.debit import bank_transfer_asserts as bt_assert
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow

scenarios("../features/debit/gateway_common.feature")

pytestmark = pytest.mark.xdist_group("debit_bank_transfer")


@when("DSH clears every cash-out gateway weight then pins Mellat")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    bt_flow.store_zero_weight_block_then_pin(bt_ctx)


@when("DSH deactivates the bank client used for routing")
def _(bt_flow: BankTransferFlow) -> None:
    bt_flow.deactivate_bank_client()


@when("a customer requests a bank transfer route")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    bt_flow.store_route_attempt(bt_ctx)


@when("a customer routes a bank transfer")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    bt_flow.store_route_success(bt_ctx)


@when("the customer inquires that transfer")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    bt_flow.store_inquiry(bt_ctx)


@when("the customer inquires without executing the transfer")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    bt_flow.store_inquiry(bt_ctx)


@then("the route is rejected because no gateway is available")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_route_rejected_no_gateway(bt_ctx)


@then("routing is blocked with no gateway and then succeeds on Mellat")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_zero_weight_block_then_pin(bt_ctx)


@then("the inquiry reports the active gateway")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_inquiry_reports_active_gateway(bt_ctx)


@then("the transfer remains initiated without a transfer journal")
def _(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_transfer_remains_initiated(bt_ctx)
