"""Parsian / Mellat RTGS orchestration."""

from __future__ import annotations

import pytest

from tests.services.debit.bank_transfer import (
    TYPE_ACH,
    TYPE_RTGS,
    BankTransferContext,
    BankTransferFlow,
    route_body_fields,
    title_of,
)
from tests.services.debit.bank_transfer_secrets import (
    require_live_transfer,
)

RTGS_OUTAGE_TITLES = frozenset({"SWCH_BANK_SERVICE_NOT_AVAILABLE", "BANKPROXY_BANK_UNKNOWN_ERROR"})
BLOCK_TITLES = frozenset(
    {
        "INVALID_PARAMETER",
        "FAILURE",
        "BAD_REQUEST",
        "BANKPROXY_NO_GATEWAY",
    }
)
PLATFORM_REJECT = frozenset(
    {
        "INVALID_PARAMETER",
        "FAILURE",
        "BAD_REQUEST",
        "TRANSACTION_NOT_FOUND",
        "BANKPROXY_DUPLICATE_TRANSACTION",
        "BANKPROXY_NO_GATEWAY",
    }
)
NO_GATEWAY_TITLES = frozenset({"BANKPROXY_NO_GATEWAY"})


def store_parsian_case(flow: BankTransferFlow, ctx: BankTransferContext, case: str) -> None:
    """Dispatch Parsian ACH When."""
    {
        "ordinary paya route": _parsian_route,
        "paya inquiry after route": _parsian_inquiry,
        "zero weights then pin": _parsian_zero_then_pin,
        "fee on route": _parsian_fee,
        "live transfer journey": _parsian_live,
        "zero amount rejected": _parsian_zero,
        "bad iban rejected": _parsian_bad_iban,
    }[case](flow, ctx)


def store_rtgs_case(flow: BankTransferFlow, ctx: BankTransferContext, case: str) -> None:
    """Dispatch Mellat RTGS When."""
    {
        "satna route contract": _rtgs_route,
        "satna inquiry after route": _rtgs_inquiry,
        "satna live transfer": _rtgs_live,
        "reference satna reconcile": _rtgs_reference,
    }[case](flow, ctx)


def store_peer_inquiry(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Inquiry for the scenario tracking code (no extra route)."""
    if ctx.flags.get("outage"):
        return
    tc = ctx.tracking_code or ""
    ctx.inquiry_result = flow.inquiry(tc)
    ctx.last_result = ctx.inquiry_result
    ctx.mongo_doc = flow.find_transfer(tc)
    ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")
    ctx.flags["client_code"] = (ctx.mongo_doc or {}).get("clientCode")


def _parsian_iban(flow: BankTransferFlow) -> str:
    return flow.secrets.parsian_cross_bank_iban or flow.secrets.mellat_cross_bank_iban


def _parsian_route(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_parsian_ach(100)
    tc = flow.new_tracking_code("PACH", prefix="QA-PAR")
    ctx.tracking_code = tc
    ctx.route_result = flow.route(
        tc,
        amount=flow.secrets.ach_probe_amount,
        iban=_parsian_iban(flow),
        preferred_type=str(TYPE_ACH),
        description=f"QA|PARSIAN|ACH|{tc}",
    )
    ctx.last_result = ctx.route_result
    ctx.mongo_doc = flow.find_transfer(tc)


def _parsian_inquiry(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    _parsian_route(flow, ctx)
    ctx.inquiry_result = flow.inquiry(ctx.tracking_code or "")
    ctx.last_result = ctx.inquiry_result
    ctx.mongo_doc = flow.find_transfer(ctx.tracking_code or "")


def _parsian_zero_then_pin(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.clear_all_gateway_weights()
    tc_off = flow.new_tracking_code("POFF", prefix="QA-PAR")
    off = flow.route(
        tc_off,
        amount=flow.secrets.ach_probe_amount,
        iban=_parsian_iban(flow),
        preferred_type=str(TYPE_ACH),
    )
    ctx.flags["off_status"] = off.get("status_code")
    ctx.flags["off_title"] = title_of(off)
    ctx.flags["off_doc_missing"] = flow.find_transfer(tc_off) is None
    flow.routing.pin_parsian_ach(100)
    tc = flow.new_tracking_code("PON", prefix="QA-PAR")
    ctx.tracking_code = tc
    ctx.route_result = flow.route(
        tc,
        amount=flow.secrets.ach_probe_amount,
        iban=_parsian_iban(flow),
        preferred_type=str(TYPE_ACH),
        description=f"QA|PARSIAN|PIN|{tc}",
    )
    ctx.last_result = ctx.route_result
    ctx.mongo_doc = flow.find_transfer(tc)


def _parsian_fee(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    _parsian_route(flow, ctx)
    body = route_body_fields(ctx.route_result)
    ctx.flags["fee"] = body.fee if body is not None else None


def _parsian_live(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    require_live_transfer(flow.secrets)
    _parsian_route(flow, ctx)
    tc = ctx.tracking_code or ""
    ctx.last_result = flow.execute(tc)
    ctx.inquiry_result = flow.inquiry(tc)
    ctx.mongo_doc = flow.find_transfer(tc)
    xfer_body = ctx.last_result.get("body")
    bank_ref = None
    if isinstance(xfer_body, dict):
        bank_ref = (xfer_body.get("payResponse") or {}).get("bankTrackingCode")
    ctx.flags["bank_ref"] = bank_ref
    ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")


def _parsian_zero(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_parsian_ach(100)
    tc = flow.new_tracking_code("P0", prefix="QA-PAR")
    ctx.tracking_code = tc
    ctx.last_result = flow.route(
        tc,
        amount=0,
        iban=_parsian_iban(flow),
        preferred_type=str(TYPE_ACH),
    )
    ctx.flags["doc_missing"] = flow.find_transfer(tc) is None


def _parsian_bad_iban(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_parsian_ach(100)
    tc = flow.new_tracking_code("PBAD", prefix="QA-PAR")
    ctx.tracking_code = tc
    ctx.last_result = flow.route(
        tc,
        amount=flow.secrets.ach_probe_amount,
        iban="IR00INVALID",
        preferred_type=str(TYPE_ACH),
    )
    ctx.flags["doc_missing"] = flow.find_transfer(tc) is None


def _rtgs_route(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_mellat_rtgs(100)
    tc = flow.new_tracking_code("RTGS", prefix="QA-MEL")
    ctx.tracking_code = tc
    amount = max(flow.secrets.mellat_rtgs_probe_amount, flow.secrets.mellat_rtgs_min_amount)
    ctx.route_result = flow.route(
        tc,
        amount=amount,
        iban=flow.secrets.mellat_rtgs_target_iban,
        preferred_type=str(TYPE_RTGS),
        description=f"QA|MELLAT|RTGS|{tc}",
    )
    ctx.last_result = ctx.route_result
    title = title_of(ctx.route_result)
    if ctx.route_result.get("status_code") == 422 and title in RTGS_OUTAGE_TITLES:
        ctx.flags["outage"] = True
        ctx.flags["outage_reason"] = f"RTGS outage title={title}"
        return
    ctx.flags["outage"] = False
    ctx.mongo_doc = flow.find_transfer(tc)


def _rtgs_inquiry(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    _rtgs_route(flow, ctx)
    if ctx.flags.get("outage"):
        return
    ctx.inquiry_result = flow.inquiry(ctx.tracking_code or "")
    ctx.mongo_doc = flow.find_transfer(ctx.tracking_code or "")


def _rtgs_live(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    require_live_transfer(flow.secrets)
    _rtgs_route(flow, ctx)
    if ctx.flags.get("outage"):
        return
    tc = ctx.tracking_code or ""
    ctx.last_result = flow.execute(tc)
    ctx.mongo_doc = flow.wait_mongo_settled(tc, timeout_sec=120.0)
    ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")
    txs = (ctx.mongo_doc or {}).get("transactions") or []
    ctx.flags["tx_amount"] = txs[0].get("amount") if txs else None


def _rtgs_reference(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    tc = (flow.secrets.mellat_rtgs_reference_tc or "").strip()
    if not tc:
        doc = flow.routing.db.ach_transfers.find_one(
            {
                "trackingCode": {"$regex": "^QA-MEL"},
                "status": "DONE",
                "type": {"$in": [TYPE_RTGS, "RTGS", "RTGS_TRANSFER", 1, "1"]},
            },
            sort=[("creationDate", -1)],
        )
        if doc is None:
            pytest.skip("No DONE Mellat RTGS reference transfer in mongo")
        tc = str(doc.get("trackingCode"))
        ctx.mongo_doc = doc
    else:
        ctx.mongo_doc = flow.find_transfer(tc)
        if ctx.mongo_doc is None or ctx.mongo_doc.get("status") != "DONE":
            pytest.skip(f"RTGS reference TC {tc} missing or not DONE")
    ctx.tracking_code = tc
    ctx.inquiry_result = flow.inquiry(tc)
    ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")
    ctx.flags["mongo_type"] = (ctx.mongo_doc or {}).get("type")
