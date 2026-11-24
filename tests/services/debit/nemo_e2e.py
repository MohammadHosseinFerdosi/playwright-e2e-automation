"""Live Nemo cash-out e2e / crisis / reference audits (SET-T531..T536)."""

from __future__ import annotations

import time
from typing import Any

import pytest

from tests.services.assert_report import AssertionReport
from tests.services.debit.bank_transfer import BankTransferFlow
from tests.services.debit.bank_transfer_routing import BankTransferRoutingDb
from tests.services.debit.nemo_cash_out import NemoCashOutContext, NemoCashOutFlow
from tests.services.debit.nemo_secrets import require_live_cash_out
from tests.services.debit.nemo_wallet_db import NemoWalletDb

DSH_SETTLE_ALIGN = "manual dsh settle align"


def store_e2e_case(
    flow: NemoCashOutFlow,
    bt_flow: BankTransferFlow,
    routing: BankTransferRoutingDb,
    ctx: NemoCashOutContext,
    case: str,
) -> None:
    """Dispatch live e2e When."""
    {
        "manual bt row": lambda: _bt_row(flow, bt_flow, routing, ctx, "manual"),
        "manual crisis in progress": lambda: _manual_crisis(flow, bt_flow, routing, ctx),
        DSH_SETTLE_ALIGN: lambda: _dsh_settle(flow, bt_flow, routing, ctx),
        "mellat bt row": lambda: _bt_row(flow, bt_flow, routing, ctx, "mellat"),
        "mellat poll terminal": lambda: _mellat_poll(flow, routing, ctx),
        "mellat reference audit": lambda: _reference_audit(flow, bt_flow, ctx),
    }[case]()


def _pin(routing: BankTransferRoutingDb, gateway: str) -> None:
    if gateway == "mellat":
        routing.pin_mellat_internal(100)
    elif gateway == "manual":
        routing.pin_manual_ach(100)
    else:
        raise KeyError(gateway)


def _require_wallet(flow: NemoCashOutFlow, reason: str) -> NemoWalletDb:
    wallet = flow.wallet
    if wallet is None:
        pytest.skip(reason)
    return wallet


def _bt_row(
    flow: NemoCashOutFlow,
    bt_flow: BankTransferFlow,
    routing: BankTransferRoutingDb,
    ctx: NemoCashOutContext,
    gateway: str,
) -> None:
    require_live_cash_out(flow.secrets)
    flow.prepare_wallet()
    wallet = _require_wallet(flow, "Nemo wallet Mongo required for live e2e")
    _pin(routing, gateway)
    result = flow.register()
    tracking = flow.register_or_skip_kyc(result, label=f"register {gateway}")
    wallet.assert_cash_out_persisted(tracking, amount=flow.secrets.safe_amount)
    doc = bt_flow.wait_mongo_settled(tracking, timeout_sec=120.0) or bt_flow.find_transfer(
        tracking
    )
    if doc is None:
        doc = routing.find_transfer(tracking)
    expected = {
        "mellat": ("bn_mellat", "012", ("INTERNAL", 2)),
        "manual": ("bn_manual", "MANUAL", ("ACH", 0)),
    }[gateway]
    actions = [j.get("action") for j in ((doc or {}).get("journals") or []) if isinstance(j, dict)]
    txs = (doc or {}).get("transactions") or []
    tx_iban = None
    if txs and isinstance(txs[0], dict):
        tx_iban = txs[0].get("iban") or txs[0].get("targetIban")
    ctx.tracking_code = tracking
    ctx.last_result = result
    ctx.flags = {
        "gateway": gateway,
        "client_code": (doc or {}).get("clientCode"),
        "bank_code": (doc or {}).get("bankCode"),
        "expected_client_code": expected[0],
        "expected_bank_code": expected[1],
        "bt_type": (doc or {}).get("type"),
        "expected_types": expected[2],
        "tx_iban": tx_iban,
        "expected_iban": flow.secrets.require_target_iban(),
        "journal_actions": actions,
    }


def _mellat_poll(
    flow: NemoCashOutFlow,
    routing: BankTransferRoutingDb,
    ctx: NemoCashOutContext,
) -> None:
    require_live_cash_out(flow.secrets)
    flow.prepare_wallet()
    _pin(routing, "mellat")
    from tests.services.debit import nemo_cash_out as co

    co.store_register_case(flow, ctx, "poll to terminal")
    doc = routing.find_transfer(ctx.tracking_code or "")
    ctx.flags["client_code"] = (doc or {}).get("clientCode")
    ctx.flags["bank_code"] = (doc or {}).get("bankCode")
    ctx.flags["expected_client_code"] = "bn_mellat"
    ctx.flags["expected_bank_code"] = "012"


def _manual_crisis(
    flow: NemoCashOutFlow,
    bt_flow: BankTransferFlow,
    routing: BankTransferRoutingDb,
    ctx: NemoCashOutContext,
) -> None:
    require_live_cash_out(flow.secrets)
    flow.prepare_wallet()
    wallet = _require_wallet(flow, "Nemo wallet Mongo required for crisis path")
    _pin(routing, "manual")
    result = flow.register()
    tracking = flow.register_or_skip_kyc(result, label="manual crisis")
    wallet.assert_cash_out_persisted(tracking, amount=flow.secrets.safe_amount)
    doc = bt_flow.find_transfer(tracking) or routing.find_transfer(tracking)
    if doc and doc.get("status") == "INITIATED":
        bt_flow.execute(tracking)
        doc = bt_flow.find_transfer(tracking)
    inquiry = bt_flow.inquiry(tracking)
    detail = flow.detail(tracking)
    ctx.tracking_code = tracking
    ctx.flags = {
        "client_code": (doc or {}).get("clientCode"),
        "bt_http": inquiry.get("status_code"),
        "nemo_http": detail.get("status_code"),
        "has_cash_out": wallet.find_cash_out(tracking) is not None,
        "mongo_status": (doc or {}).get("status"),
    }


def _wait_bt_row(
    bt_flow: BankTransferFlow,
    routing: BankTransferRoutingDb,
    tracking: str,
) -> dict[str, Any] | None:
    """Poll until the bank-transfer row exists."""
    deadline = time.time() + 120.0
    last: dict[str, Any] | None = None
    while time.time() < deadline:
        last = bt_flow.find_transfer(tracking) or routing.find_transfer(tracking)
        if last is not None:
            return last
        time.sleep(2.0)
    return last


def _dsh_settle(
    flow: NemoCashOutFlow,
    bt_flow: BankTransferFlow,
    routing: BankTransferRoutingDb,
    ctx: NemoCashOutContext,
) -> None:
    """Register on manual, mark DONE, compare Nemo detail with BT inquiry."""
    require_live_cash_out(flow.secrets)
    flow.prepare_wallet()
    wallet = _require_wallet(flow, "Nemo wallet Mongo required for settle align")
    _pin(routing, "manual")
    result = flow.register()
    tracking = flow.register_or_skip_kyc(result, label="manual settle align")
    wallet.assert_cash_out_persisted(tracking, amount=flow.secrets.safe_amount)
    if _wait_bt_row(bt_flow, routing, tracking) is None:
        raise AssertionError(f"{tracking} never appeared in ach_transfers")
    snap = routing.simulate_manual_settle(
        tracking, mongo_status="DONE", tx_status="ACCEPTED"
    )
    try:
        inquiry = bt_flow.inquiry(tracking)
        detail = flow.detail(tracking)
        ctx.tracking_code = tracking
        ctx.flags = {
            "has_cash_out": wallet.find_cash_out(tracking) is not None,
            "bt_http": inquiry.get("status_code"),
            "nemo_http": detail.get("status_code"),
        }
    finally:
        routing.qa_restore_transfer_doc(tracking, snap)


def _reference_audit(
    flow: NemoCashOutFlow,
    bt_flow: BankTransferFlow,
    ctx: NemoCashOutContext,
) -> None:
    tc = (flow.secrets.cashout_bt_reference_tc or "").strip()
    if not tc:
        pytest.skip("Set cashout_bt_reference_tc in secrets/uat_nemo.yaml")
    wallet = _require_wallet(flow, "Nemo wallet Mongo required for reference audit")
    co = wallet.find_cash_out(tc)
    doc = bt_flow.find_transfer(tc)
    cell = None
    if co:
        cell = co.get("destCellNumber") or (co.get("owner") or {}).get("cellNumber")
    ctx.tracking_code = tc
    ctx.flags = {
        "passed": bool(co) and bool(doc) and (doc or {}).get("status") in (
            "DONE",
            "SUCCEED",
            "IN_PROGRESS",
        ),
        "has_cash_out": bool(co),
        "cell": cell,
        "expected_cells": (flow.secrets.cell_number,),
        "errors": [] if co and doc else ["missing cash_out or bt row"],
    }


def assert_e2e_case(ctx: NemoCashOutContext, case: str) -> None:
    """Dispatch live e2e Then."""
    {
        "manual bt row": assert_bt_row,
        "manual crisis in progress": assert_crisis,
        DSH_SETTLE_ALIGN: assert_dsh_settle,
        "mellat bt row": assert_bt_row,
        "mellat poll terminal": assert_mellat_poll,
        "mellat reference audit": assert_reference,
    }[case](ctx)


def assert_bt_row(ctx: NemoCashOutContext) -> None:
    """BT row matches pinned gateway."""
    report = AssertionReport("nemo e2e bt row")
    report.equals(
        "client",
        actual=ctx.flags.get("client_code"),
        expected=ctx.flags.get("expected_client_code"),
    )
    report.equals(
        "bank",
        actual=ctx.flags.get("bank_code"),
        expected=ctx.flags.get("expected_bank_code"),
    )
    bt_type = ctx.flags.get("bt_type")
    expected_types = ctx.flags.get("expected_types") or ()
    report.check("type", bt_type in expected_types)
    if ctx.flags.get("gateway") == "mellat":
        report.equals(
            "iban",
            actual=ctx.flags.get("tx_iban"),
            expected=ctx.flags.get("expected_iban"),
        )
        report.check("ROUTE", "ROUTE" in (ctx.flags.get("journal_actions") or []))
    report.assert_all()


def assert_crisis(ctx: NemoCashOutContext) -> None:
    """Manual crisis stays inquiry-able."""
    report = AssertionReport("nemo manual crisis")
    report.equals("client", actual=ctx.flags.get("client_code"), expected="bn_manual")
    report.equals("bt HTTP", actual=ctx.flags.get("bt_http"), expected=200)
    report.equals("nemo HTTP", actual=ctx.flags.get("nemo_http"), expected=200)
    report.check("cash_out", ctx.flags.get("has_cash_out") is True)
    report.assert_all()


def assert_dsh_settle(ctx: NemoCashOutContext) -> None:
    """Nemo detail and BT inquiry both succeed after settle."""
    report = AssertionReport("nemo settle vs inquiry")
    report.check("cash_out", ctx.flags.get("has_cash_out") is True)
    report.equals("bt HTTP", actual=ctx.flags.get("bt_http"), expected=200)
    report.equals("nemo HTTP", actual=ctx.flags.get("nemo_http"), expected=200)
    report.assert_all()


def assert_mellat_poll(ctx: NemoCashOutContext) -> None:
    """Terminal + mellat routing."""
    from tests.services.debit.nemo_cash_out_asserts import assert_register_terminal

    assert_register_terminal(ctx)
    report = AssertionReport("mellat poll routing")
    report.equals(
        "client",
        actual=ctx.flags.get("client_code"),
        expected=ctx.flags.get("expected_client_code"),
    )
    report.equals(
        "bank",
        actual=ctx.flags.get("bank_code"),
        expected=ctx.flags.get("expected_bank_code"),
    )
    report.assert_all()


def assert_reference(ctx: NemoCashOutContext) -> None:
    """Reference cash-out audit."""
    report = AssertionReport("mellat reference audit")
    report.check("passed", ctx.flags.get("passed") is True)
    report.check("cash_out", ctx.flags.get("has_cash_out") is True)
    expected = ctx.flags.get("expected_cells") or ()
    if expected and expected[0]:
        report.check("cell", ctx.flags.get("cell") in expected)
    report.assert_all()
