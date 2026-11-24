"""BDD steps for Parsian / Mellat RTGS — thin orchestration."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from tests.services.debit import bank_transfer_peers as peers
from tests.services.debit import bank_transfer_peers_asserts as peers_assert
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow
from tests.services.debit.debit_peers_gherkin import (
    assert_peer_rejected,
    assert_peer_routed,
    execute_live_peer_cash_out,
    inquire_peer_cash_out,
    run_parsian_request,
)

scenarios("../features/debit/parsian_ach.feature")
scenarios("../features/debit/mellat_rtgs.feature")

pytestmark = pytest.mark.xdist_group("debit_bank_transfer")


@when("DSH clears every cash-out gateway weight then enables Parsian PAYA")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    peers.store_parsian_case(bt_flow, bt_ctx, "zero weights then pin")


@when(parsers.re(r"^the customer requests (?P<mode>[A-Za-z0-9 -]*Parsian[A-Za-z0-9 -]*)$"))
def _(mode: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    run_parsian_request(bt_flow, bt_ctx, mode)


@when(parsers.re(r"^the customer inquires that (?P<peer>Parsian|SATNA) cash-out$"))
def _(peer: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    inquire_peer_cash_out(bt_flow, bt_ctx, peer)


@when(parsers.re(r"^the customer executes a live (?P<rail>Parsian PAYA|Mellat SATNA) cash-out$"))
def _(rail: str, bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    execute_live_peer_cash_out(bt_flow, bt_ctx, rail)


@when("the customer requests a Mellat SATNA cash-out")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    peers.store_rtgs_case(bt_flow, bt_ctx, "satna route contract")


@when("DSH looks up a settled Mellat SATNA cash-out")
def _(bt_flow: BankTransferFlow, bt_ctx: BankTransferContext) -> None:
    peers.store_rtgs_case(bt_flow, bt_ctx, "reference satna reconcile")


@then(parsers.re(r"^the cash-out is routed (?P<route>[A-Za-z0-9 -]+)$"))
def _(route: str, bt_ctx: BankTransferContext) -> None:
    assert_peer_routed(bt_ctx, route)


@then(parsers.re(r"^the cash-out is rejected (?P<reason>[A-Za-z0-9 -]+)$"))
def _(reason: str, bt_ctx: BankTransferContext) -> None:
    assert_peer_rejected(bt_ctx, reason)


@then("none of the cash-out routes return a server error")
def _(bt_ctx: BankTransferContext) -> None:
    peers_assert.assert_xss(bt_ctx)


@then("the Parsian PAYA inquiry stays routed")
def _(bt_ctx: BankTransferContext) -> None:
    peers_assert.assert_parsian_inquiry(bt_ctx)


@then("PAYA is blocked with no gateway and then routes through Parsian")
def _(bt_ctx: BankTransferContext) -> None:
    peers_assert.assert_parsian_zero_pin(bt_ctx)


@then("the Parsian PAYA route reports a non-negative fee")
def _(bt_ctx: BankTransferContext) -> None:
    peers_assert.assert_parsian_fee(bt_ctx)


@then("the live Parsian PAYA cash-out settles")
def _(bt_ctx: BankTransferContext) -> None:
    peers_assert.assert_parsian_live(bt_ctx)


@then("the SATNA inquiry stays routed")
def _(bt_ctx: BankTransferContext) -> None:
    peers_assert.assert_rtgs_inquiry(bt_ctx)


@then("the live SATNA cash-out settles")
def _(bt_ctx: BankTransferContext) -> None:
    peers_assert.assert_rtgs_live(bt_ctx)


@then("the settled SATNA cash-out still inquires successfully")
def _(bt_ctx: BankTransferContext) -> None:
    peers_assert.assert_rtgs_reference(bt_ctx)
