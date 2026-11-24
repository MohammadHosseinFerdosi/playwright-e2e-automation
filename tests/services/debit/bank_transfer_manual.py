"""Manual portal (bn_manual) scenario orchestration."""

from __future__ import annotations

import concurrent.futures
from typing import Any

import pytest

from tests.api.debit.bank_transfer.ach_scheduler import (
    post_trigger_resume_suspend,
    post_trigger_transfer_report,
)
from tests.config.constants import PLATFORM_VERSION_2023
from tests.services.debit.bank_transfer import (
    TYPE_ACH,
    BankTransferContext,
    BankTransferFlow,
    route_body_fields,
    title_of,
)
from tests.services.debit.nemo_secrets import require_nemo_secrets
from tests.services.debit.nemo_wallet_db import NemoWalletDb

# Inquiry API numeric enums (not mongo string ordinals).
INQ_SUCCEED = 1
INQ_PENDING = 2
MANUAL_CLIENT = "bn_manual"
MANUAL_BANK = "MANUAL"
PROVIDER_JOURNAL_ACTIONS = frozenset({"SETTLE", "INQUIRY", "REVERSE", "REPORT"})
DSH_SETTLE_DONE = "dsh settle done inquiry"
DSH_DONE_SCHEMA = "dsh done row schema"


def store_manual_case(
    flow: BankTransferFlow, ctx: BankTransferContext, case: str
) -> None:
    """Dispatch Manual When by case key."""
    dispatch = {
        "ach route pinned": store_ach_route_pinned,
        "never internal type": store_never_internal,
        "mongo row fields": store_mongo_fields,
        "route transfer in progress": store_route_transfer_ip,
        "inquiry preserves in progress": store_inquiry_preserves_ip,
        "scheduler preserves in progress": store_scheduler_preserves_ip,
        "routing consistency": store_routing_consistency,
        "mellat split fifty fifty": store_mellat_split,
        "cross bank blocked mellat only": store_cross_bank_mellat_only,
        "rtgs inactive": store_rtgs_inactive,
        "ach fee zero": store_fee_zero,
        "accepts every bank iban": store_every_bank_iban,
        "route journal": store_route_journal,
        "transfer journal": store_transfer_journal,
        "inquiry matches mongo": store_inquiry_matches_mongo,
        "tx accepted after transfer": store_tx_accepted,
        "reconcile without statement": store_reconcile,
        "duplicate route single row": store_dup_route,
        "duplicate transfer rejected": store_dup_transfer,
        "concurrent transfer race": store_concurrent_race,
        "production crisis checklist": store_crisis,
        DSH_SETTLE_DONE: store_dsh_settle_done,
        DSH_DONE_SCHEMA: store_dsh_done_schema,
        "nemo settlement reference": store_nemo_reference,
    }
    dispatch[case](flow, ctx)


def _manual_iban(flow: BankTransferFlow) -> str:
    return flow.secrets.melli_target_iban or flow.secrets.mellat_cross_bank_iban


def _tc(flow: BankTransferFlow, tag: str) -> str:
    return flow.new_tracking_code(tag, prefix="QA-MAN")


def _pin(flow: BankTransferFlow) -> None:
    flow.routing.pin_manual_ach(100)


def _route_manual(
    flow: BankTransferFlow,
    tc: str,
    *,
    iban: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    return flow.route(
        tc,
        amount=flow.secrets.marker_amount,
        iban=iban or _manual_iban(flow),
        preferred_type=str(TYPE_ACH),
        description=description or f"QA|MANUAL|{tc}",
        owner_name=flow.secrets.mellat_owner_name,
    )


def _journal_actions(doc: dict[str, Any] | None) -> list[str]:
    journals = (doc or {}).get("journals") or []
    out: list[str] = []
    for item in journals:
        if isinstance(item, dict):
            action = item.get("action")
            if isinstance(action, str):
                out.append(action)
    return out


def store_ach_route_pinned(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Pin manual and route ACH."""
    _pin(flow)
    tc = _tc(flow, "ACH")
    ctx.tracking_code = tc
    ctx.route_result = _route_manual(flow, tc, description=f"QA|MANUAL|ACH|{tc}")
    ctx.last_result = ctx.route_result
    ctx.mongo_doc = flow.find_transfer(tc)


def store_never_internal(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Manual pin must never return INTERNAL type."""
    store_ach_route_pinned(flow, ctx)


def store_mongo_fields(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Route only; capture mongo row fields."""
    _pin(flow)
    tc = _tc(flow, "MONGO")
    ctx.tracking_code = tc
    ctx.route_result = _route_manual(flow, tc, description=f"QA|MANUAL|MONGO|{tc}")
    ctx.last_result = ctx.route_result
    ctx.mongo_doc = flow.find_transfer(tc)


def store_route_transfer_ip(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Route + execute → IN_PROGRESS."""
    _pin(flow)
    tc = _tc(flow, "XFER")
    ctx.tracking_code = tc
    _route_manual(flow, tc, description=f"QA|MANUAL|XFER|{tc}")
    ctx.last_result = flow.execute(tc)
    ctx.mongo_doc = flow.find_transfer(tc)


def store_inquiry_preserves_ip(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Inquiry must not advance IN_PROGRESS."""
    store_route_transfer_ip(flow, ctx)
    before = (ctx.mongo_doc or {}).get("status")
    ctx.inquiry_result = flow.inquiry(ctx.tracking_code or "")
    ctx.mongo_doc = flow.find_transfer(ctx.tracking_code or "")
    ctx.flags["status_before"] = before
    ctx.flags["status_after"] = (ctx.mongo_doc or {}).get("status")


def store_scheduler_preserves_ip(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """ACH scheduler triggers must not settle manual."""
    store_route_transfer_ip(flow, ctx)
    before = (ctx.mongo_doc or {}).get("status")
    secrets = flow.secrets
    post_trigger_transfer_report(
        flow.client,
        user_id=secrets.user_id,
        forwarded_for=secrets.forwarded_for,
        platform_version=PLATFORM_VERSION_2023,
    )
    post_trigger_resume_suspend(
        flow.client,
        user_id=secrets.user_id,
        forwarded_for=secrets.forwarded_for,
        platform_version=PLATFORM_VERSION_2023,
    )
    ctx.mongo_doc = flow.find_transfer(ctx.tracking_code or "")
    ctx.flags["status_before"] = before
    ctx.flags["status_after"] = (ctx.mongo_doc or {}).get("status")


def store_routing_consistency(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Repair + assert no inactive stale weights."""
    _pin(flow)
    flow.routing.repair_stale_weights()
    flow.routing.assert_routing_consistent()
    ctx.flags["routing_ok"] = True


def store_mellat_split(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Manual 50 / mellat 50 — cross-bank still manual ACH."""
    flow.routing.split_gateway_weights({"manual": 50, "mellat": 50})
    tc = _tc(flow, "SPLIT")
    ctx.tracking_code = tc
    ctx.route_result = _route_manual(flow, tc, description=f"QA|MANUAL|SPLIT|{tc}")
    ctx.last_result = ctx.route_result
    ctx.mongo_doc = flow.find_transfer(tc)


def store_cross_bank_mellat_only(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Only mellat INTERNAL pinned — cross-bank IBAN rejected."""
    flow.pin_active_gateway()
    tc = _tc(flow, "BLK-MEL")
    ctx.tracking_code = tc
    ctx.last_result = flow.route(
        tc,
        amount=flow.secrets.marker_amount,
        iban=_manual_iban(flow),
        preferred_type=str(TYPE_ACH),
        description=f"QA|MANUAL|BLK-MEL|{tc}",
    )


def store_rtgs_inactive(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """bn_manual RTGS row stays inactive weight 0."""
    _pin(flow)
    ctx.client_row = flow.routing.manual_rtgs_row()
    ctx.flags["rtgs_checked"] = True


def store_fee_zero(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Manual ACH route fee is 0."""
    store_ach_route_pinned(flow, ctx)


def store_every_bank_iban(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Manual accepts mellat/shahin/melli/parsian IBANs."""
    _pin(flow)
    secrets = flow.secrets
    ibans = {
        "mellat": secrets.mellat_target_iban,
        "shahin": secrets.shahin_target_iban,
        "melli": secrets.melli_target_iban,
        "parsian": secrets.parsian_target_iban,
    }
    codes: list[str | None] = []
    for key, iban in ibans.items():
        tc = _tc(flow, f"ANY-{key[:3].upper()}")
        result = _route_manual(
            flow, tc, iban=iban, description=f"QA|MANUAL|ANY-{key.upper()}|{tc}"
        )
        body = route_body_fields(result)
        codes.append(body.client_code if body is not None else None)
        ctx.probe_codes.append(int(result.get("status_code") or 0))
    ctx.flags["client_codes"] = codes


def store_route_journal(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """ROUTE journal after route."""
    store_mongo_fields(flow, ctx)
    ctx.flags["journal_phase"] = "route"
    ctx.flags["actions"] = _journal_actions(ctx.mongo_doc)


def store_transfer_journal(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """ROUTE+TRANSFER journals after execute."""
    store_route_transfer_ip(flow, ctx)
    ctx.flags["journal_phase"] = "transfer"
    ctx.flags["actions"] = _journal_actions(ctx.mongo_doc)


def store_inquiry_matches_mongo(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Inquiry PENDING when mongo IN_PROGRESS."""
    store_route_transfer_ip(flow, ctx)
    ctx.inquiry_result = flow.inquiry(ctx.tracking_code or "")
    body = route_body_fields(ctx.inquiry_result)
    raw = ctx.inquiry_result.get("body")
    status = body.status if body is not None else (
        raw.get("status") if isinstance(raw, dict) else None
    )
    ctx.flags["inquiry_status"] = status
    ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")


def store_tx_accepted(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """transactions[0].status ACCEPTED after transfer."""
    store_route_transfer_ip(flow, ctx)
    txs = (ctx.mongo_doc or {}).get("transactions") or []
    ctx.flags["tx_status"] = txs[0].get("status") if txs else None


def store_reconcile(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Amount+IBAN agree across mongo and inquiry (no statement)."""
    store_route_transfer_ip(flow, ctx)
    ctx.inquiry_result = flow.inquiry(ctx.tracking_code or "")
    doc = ctx.mongo_doc or {}
    txs = doc.get("transactions") or []
    mongo_amt = int(txs[0].get("amount") or 0) if txs else 0
    mongo_iban = (txs[0].get("iban") or txs[0].get("targetIban")) if txs else None
    body = route_body_fields(ctx.inquiry_result)
    raw = ctx.inquiry_result.get("body")
    inq_txs = (
        body.transactions
        if body is not None and body.transactions
        else (raw.get("transactions") if isinstance(raw, dict) else None)
    ) or []
    inq_amt = int(inq_txs[0].get("amount") or 0) if inq_txs else None
    inq_iban = None
    if inq_txs:
        inq_iban = inq_txs[0].get("iban") or inq_txs[0].get("targetIban")
    ctx.flags["amount_ok"] = inq_amt == mongo_amt
    ctx.flags["iban_ok"] = inq_iban == mongo_iban
    ctx.flags["mongo_status"] = doc.get("status")


def store_dup_route(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Duplicate route → one mongo row."""
    _pin(flow)
    tc = _tc(flow, "DUP-DOC")
    ctx.tracking_code = tc
    ctx.route_result = _route_manual(flow, tc, description=f"QA|MANUAL|DUP1|{tc}")
    ctx.second_result = _route_manual(flow, tc, description=f"QA|MANUAL|DUP2|{tc}")
    ctx.last_result = ctx.second_result
    ctx.mongo_count = flow.count_transfers(tc)


def store_dup_transfer(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Second execute rejected while IN_PROGRESS."""
    _pin(flow)
    tc = _tc(flow, "DUP-TX")
    ctx.tracking_code = tc
    _route_manual(flow, tc, description=f"QA|MANUAL|DUP-TX|{tc}")
    ctx.route_result = flow.execute(tc)
    ctx.second_result = flow.execute(tc)
    ctx.last_result = ctx.second_result
    ctx.mongo_doc = flow.find_transfer(tc)


def store_concurrent_race(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Concurrent execute — exactly one 200."""
    _pin(flow)
    tc = _tc(flow, "RACE")
    ctx.tracking_code = tc
    _route_manual(flow, tc, description=f"QA|MANUAL|RACE|{tc}")

    def _fire(_: int) -> tuple[int, str | None]:
        result = flow.execute(tc)
        return int(result.get("status_code") or 0), title_of(result)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pairs = list(pool.map(_fire, range(2)))
    ctx.probe_codes = [p[0] for p in pairs]
    ctx.probe_titles = [p[1] for p in pairs]
    doc = flow.find_transfer(tc)
    ctx.mongo_doc = doc
    actions = _journal_actions(doc)
    ctx.flags["transfer_journal_count"] = actions.count("TRANSFER")
    ctx.flags["mongo_status"] = (doc or {}).get("status")


def store_crisis(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Crisis checklist: ready + RTGS off + route/xfer/inq."""
    _pin(flow)
    rtgs = flow.routing.manual_rtgs_row()
    ctx.flags["rtgs_inactive"] = bool(
        rtgs is not None
        and rtgs.get("active") is False
        and int(rtgs.get("selectionWeight") or 0) == 0
    )
    tc = _tc(flow, "CRISIS")
    ctx.tracking_code = tc
    ctx.route_result = _route_manual(flow, tc, description=f"QA|MANUAL|CRISIS|{tc}")
    ctx.last_result = flow.execute(tc)
    ctx.mongo_doc = flow.find_transfer(tc)
    ctx.inquiry_result = flow.inquiry(tc)
    txs = (ctx.mongo_doc or {}).get("transactions") or []
    ctx.flags["tx_status"] = txs[0].get("status") if txs else None
    ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")
    body = route_body_fields(ctx.route_result)
    ctx.flags["fee"] = body.fee if body is not None else None
    ctx.flags["client_code"] = body.client_code if body is not None else None
    ctx.flags["type"] = body.type if body is not None else None


def _mark_done(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> tuple[str, dict[str, Any]]:
    """Route IN_PROGRESS, then write DONE / ACCEPTED. Caller restores."""
    store_route_transfer_ip(flow, ctx)
    tc = ctx.tracking_code or ""
    snap = flow.routing.simulate_manual_settle(
        tc, mongo_status="DONE", tx_status="ACCEPTED"
    )
    return tc, snap


def store_dsh_settle_done(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Mark the cash-out DONE, then inquire (expect SUCCEED)."""
    tc, snap = _mark_done(flow, ctx)
    try:
        ctx.mongo_doc = flow.find_transfer(tc)
        ctx.inquiry_result = flow.inquiry(tc)
        body = route_body_fields(ctx.inquiry_result)
        raw = ctx.inquiry_result.get("body")
        status = body.status if body is not None else (
            raw.get("status") if isinstance(raw, dict) else None
        )
        ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")
        ctx.flags["inquiry_status"] = status
    finally:
        flow.routing.qa_restore_transfer_doc(tc, snap)


def store_dsh_done_schema(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Inspect the DONE row after a simulated settle."""
    tc, snap = _mark_done(flow, ctx)
    try:
        ctx.mongo_doc = flow.find_transfer(tc)
        ctx.flags["actions"] = _journal_actions(ctx.mongo_doc)
        ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")
        ctx.flags["mongo_type"] = (ctx.mongo_doc or {}).get("type")
        ctx.inquiry_result = flow.inquiry(tc)
    finally:
        flow.routing.qa_restore_transfer_doc(tc, snap)


def store_nemo_reference(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Reference DONE row plus Nemo scheduler settlement."""
    tc = (flow.secrets.manual_settled_tc or "").strip()
    if not tc:
        pytest.skip("Set manual_settled_tc in secrets/uat_bank_transfer.yaml")
    doc = flow.find_transfer(tc)
    if doc is None:
        raise AssertionError(f"{tc} missing in ach_transfers")
    wallet = NemoWalletDb(require_nemo_secrets())
    wallet.open()
    try:
        wallet.assert_manual_settlement(tc)
    finally:
        wallet.close()
    ctx.tracking_code = tc
    ctx.mongo_doc = doc
    ctx.flags["client_code"] = doc.get("clientCode")
    ctx.flags["mongo_status"] = doc.get("status")
