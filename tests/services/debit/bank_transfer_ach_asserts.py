"""Mellat ACH (PAYA) helpers and asserts for Debit BDD."""

from __future__ import annotations

import math
from typing import Any

from tests.api.debit.bank_transfer.models import TransferRouteBody
from tests.services.assert_report import AssertionReport, attach_api_result
from tests.services.debit.bank_transfer import (
    ACH_TYPE_TOKENS,
    BankTransferContext,
    route_body_fields,
)


def expected_batch_parts(total_amount: int, chunk_size: int) -> int:
    """How many ACH chunks a total amount needs."""
    return int(math.ceil(total_amount / chunk_size))


def assert_ach_single_chunk_route(ctx: BankTransferContext) -> None:
    """Ordinary PAYA: type ACH, one mongo transaction, fee 0."""
    attach_api_result("ach route", ctx.route_result)
    secrets = ctx.secrets
    report = AssertionReport("ordinary PAYA route")
    report.equals("HTTP", actual=ctx.route_result.get("status_code"), expected=200)
    body = route_body_fields(ctx.route_result)
    report.check("typed body", isinstance(body, TransferRouteBody))
    if isinstance(body, TransferRouteBody):
        report.check("type ACH", body.type in ACH_TYPE_TOKENS)
        report.equals("fee", actual=body.fee, expected=0)
    doc = ctx.mongo_doc or {}
    txs = doc.get("transactions") or []
    report.equals("tx count", actual=len(txs), expected=1)
    if txs:
        report.equals(
            "tx amount",
            actual=int(txs[0].get("amount") or 0),
            expected=secrets.ach_probe_amount,
        )
        iban = txs[0].get("targetIban") or txs[0].get("iban")
        report.equals("tx iban", actual=iban, expected=secrets.mellat_cross_bank_iban)
    report.assert_all()


def assert_ach_batch_route(ctx: BankTransferContext) -> None:
    """Batch PAYA: expected chunk count and amount sum."""
    attach_api_result("ach batch route", ctx.route_result)
    secrets = ctx.secrets
    total = int(ctx.flags["batch_total"])
    parts = expected_batch_parts(total, secrets.ach_chunk)
    report = AssertionReport("batch PAYA route")
    report.equals("HTTP", actual=ctx.route_result.get("status_code"), expected=200)
    body = route_body_fields(ctx.route_result)
    if isinstance(body, TransferRouteBody):
        report.check("type ACH", body.type in ACH_TYPE_TOKENS)
    doc = ctx.mongo_doc or {}
    txs = doc.get("transactions") or []
    report.equals("tx count", actual=len(txs), expected=parts)
    amount_sum = sum(int(tx.get("amount") or 0) for tx in txs if isinstance(tx, dict))
    report.equals("amount sum", actual=amount_sum, expected=total)
    for idx, tx in enumerate(txs):
        if not isinstance(tx, dict):
            continue
        report.check(
            f"tx[{idx}] <= chunk",
            int(tx.get("amount") or 0) <= secrets.ach_chunk,
        )
    report.assert_all()


def assert_ach_inquiry_routed(ctx: BankTransferContext) -> None:
    """Inquiry after ACH route stays available (ROUTED / txs on body or mongo)."""
    attach_api_result("ach inquiry", ctx.inquiry_result)
    report = AssertionReport("ACH inquiry routed")
    report.equals(
        "HTTP", actual=ctx.inquiry_result.get("status_code"), expected=200
    )
    body = route_body_fields(ctx.inquiry_result)
    txs: list[Any] = []
    if isinstance(body, TransferRouteBody) and body.transactions:
        txs = list(body.transactions)
    doc = ctx.mongo_doc or {}
    if not txs:
        txs = list(doc.get("transactions") or [])
    report.truthy("transactions present", bool(txs))
    report.assert_all()


def assert_ach_batch_inquiry_lists_splits(ctx: BankTransferContext) -> None:
    """Inquiry after batch PAYA stays routed and lists the split chunks."""
    assert_ach_batch_route(ctx)
    assert_ach_inquiry_routed(ctx)
    secrets = ctx.secrets
    total = int(ctx.flags["batch_total"])
    parts = expected_batch_parts(total, secrets.ach_chunk)
    body = route_body_fields(ctx.inquiry_result)
    txs: list[Any] = []
    if isinstance(body, TransferRouteBody) and body.transactions:
        txs = list(body.transactions)
    if not txs:
        txs = list((ctx.mongo_doc or {}).get("transactions") or [])
    report = AssertionReport("batch PAYA inquiry splits")
    report.equals("inquiry tx count", actual=len(txs), expected=parts)
    report.assert_all()


def assert_ach_fee_zero(ctx: BankTransferContext) -> None:
    """ACH route fee is zero."""
    assert_ach_single_chunk_route(ctx)


def assert_same_bank_not_ach(ctx: BankTransferContext) -> None:
    """Same-bank IBAN must not land on ACH type."""
    attach_api_result("same-bank ACH attempt", ctx.last_result)
    report = AssertionReport("same-bank not ACH")
    code = int(ctx.last_result.get("status_code") or 0)
    body = route_body_fields(ctx.last_result)
    if code >= 400:
        report.check("rejected", True)
    elif isinstance(body, TransferRouteBody):
        report.check("type not ACH", body.type not in ACH_TYPE_TOKENS)
    report.assert_all()


def assert_done_ach_inquiry_succeeds(ctx: BankTransferContext) -> None:
    """Inquiry of a DONE ACH transfer reports success."""
    attach_api_result("done ACH inquiry", ctx.inquiry_result)
    report = AssertionReport("DONE ACH inquiry")
    report.equals(
        "HTTP", actual=ctx.inquiry_result.get("status_code"), expected=200
    )
    report.truthy("tracking", ctx.tracking_code)
    report.assert_all()


def assert_ach_live_settled(ctx: BankTransferContext) -> None:
    """Live ACH settle left mongo DONE (or bank-accepted)."""
    attach_api_result("live settle inquiry", ctx.inquiry_result)
    report = AssertionReport("ACH live settle")
    doc = ctx.mongo_doc or {}
    status = doc.get("status")
    report.check(
        "mongo settled",
        status in ("DONE", "SUCCEEDED", "SUCCESS", "SETTLED"),
    )
    report.assert_all()
