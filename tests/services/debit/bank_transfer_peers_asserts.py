"""Assertions for Parsian ACH and Mellat RTGS."""

from __future__ import annotations

import pytest

from tests.api.debit.bank_transfer.models import TransferRouteBody
from tests.services.assert_report import AssertionReport, attach_api_result
from tests.services.debit.bank_transfer import (
    ACH_TYPE_TOKENS,
    RTGS_TYPE_TOKENS,
    BankTransferContext,
    route_body_fields,
    title_of,
)
from tests.services.debit.bank_transfer_peers import (
    BLOCK_TITLES,
    PLATFORM_REJECT,
    NO_GATEWAY_TITLES,
)
from tests.services.debit.bank_transfer_routing import skip_if_switch_setup

INQ_ROUTED = 0
HTTP_SERVER_ERROR_MIN = 500


def _skip_outage(ctx: BankTransferContext, prefix: str) -> None:
    if ctx.flags.get("outage"):
        pytest.skip(f"{prefix}: {ctx.flags.get('outage_reason') or 'UAT outage'}")


def assert_parsian_route(ctx: BankTransferContext) -> None:
    """Ordinary Parsian PAYA route."""
    attach_api_result("parsian route", ctx.route_result)
    report = AssertionReport("parsian ACH route")
    report.equals("HTTP", actual=ctx.route_result.get("status_code"), expected=200)
    body = route_body_fields(ctx.route_result)
    report.check("typed", isinstance(body, TransferRouteBody))
    if isinstance(body, TransferRouteBody):
        report.equals("client", actual=body.client_code, expected="bn_parsian")
        report.check("type ACH", body.type in ACH_TYPE_TOKENS)
    doc = ctx.mongo_doc or {}
    report.check("mongo ACH", doc.get("type") in ACH_TYPE_TOKENS | {"ACH", 0, "0"})
    report.equals("mongo client", actual=doc.get("clientCode"), expected="bn_parsian")
    txs = doc.get("transactions") or []
    report.equals("tx count", actual=len(txs), expected=1)
    if txs:
        iban = txs[0].get("iban") or txs[0].get("targetIban")
        report.equals(
            "tx iban",
            actual=iban,
            expected=ctx.secrets.parsian_cross_bank_iban or ctx.secrets.mellat_cross_bank_iban,
        )
    report.assert_all()


def assert_parsian_inquiry(ctx: BankTransferContext) -> None:
    """Inquiry after Parsian route stays ROUTED."""
    assert_parsian_route(ctx)
    attach_api_result("inquiry", ctx.inquiry_result)
    report = AssertionReport("parsian inquiry")
    report.equals("HTTP", actual=ctx.inquiry_result.get("status_code"), expected=200)
    body = route_body_fields(ctx.inquiry_result)
    status = body.status if body is not None else None
    report.equals("inquiry ROUTED", actual=status, expected=INQ_ROUTED)
    report.assert_all()


def assert_parsian_zero_pin(ctx: BankTransferContext) -> None:
    """Zero weights block then pin succeeds."""
    raw = ctx.flags.get("off_title")
    off_title = raw if isinstance(raw, str) else None
    skip_if_switch_setup(off_title, reason="no-gateway Switch setup")
    report = AssertionReport("parsian zero then pin")
    report.equals("off HTTP", actual=ctx.flags.get("off_status"), expected=422)
    report.check("off title", off_title in NO_GATEWAY_TITLES)
    report.check("off no doc", ctx.flags.get("off_doc_missing") is True)
    report.assert_all()
    assert_parsian_route(ctx)


def assert_parsian_fee(ctx: BankTransferContext) -> None:
    """Fee present and non-negative."""
    assert_parsian_route(ctx)
    body = route_body_fields(ctx.route_result)
    fee = ctx.flags.get("fee")
    if fee is None and body is not None:
        fee = body.fee
    report = AssertionReport("parsian fee")
    report.check("fee present", fee is not None and int(fee) >= 0)
    report.assert_all()


def assert_parsian_live(ctx: BankTransferContext) -> None:
    """Live Parsian settle evidence."""
    attach_api_result("execute", ctx.last_result)
    report = AssertionReport("parsian live")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=200)
    report.truthy("bank_ref", ctx.flags.get("bank_ref"))
    report.check(
        "mongo status",
        ctx.flags.get("mongo_status") in ("IN_PROGRESS", "DONE", "SUCCEED"),
    )
    report.assert_all()


def assert_reject_invalid(ctx: BankTransferContext) -> None:
    """422 INVALID_PARAMETER + no mongo."""
    attach_api_result("reject", ctx.last_result)
    report = AssertionReport("invalid reject")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=422)
    report.equals("title", actual=title_of(ctx.last_result), expected="INVALID_PARAMETER")
    report.check("no mongo", ctx.flags.get("doc_missing") is True)
    report.assert_all()


def assert_xss(ctx: BankTransferContext) -> None:
    """XSS probes stay below HTTP 500."""
    report = AssertionReport("owner XSS")
    report.check(
        "status below 500",
        int(ctx.flags.get("max_status") or 0) < HTTP_SERVER_ERROR_MIN,
    )
    for code, title in zip(ctx.probe_codes, ctx.probe_titles, strict=True):
        if 400 <= code < 500:
            report.check(
                f"title {code}",
                title in PLATFORM_REJECT,
                detail=f"got {title!r}",
            )
    report.assert_all()


def assert_blocked(ctx: BankTransferContext) -> None:
    """Cross-gateway IBAN blocked."""
    attach_api_result("blocked", ctx.last_result)
    title = title_of(ctx.last_result)
    skip_if_switch_setup(title, reason="blocked-destination Switch setup")
    report = AssertionReport("iban blocked")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=422)
    report.check(
        "title",
        title in BLOCK_TITLES,
        detail=f"got {title!r}",
    )
    report.check("no mongo", ctx.flags.get("doc_missing") is True)
    report.assert_all()


def assert_rtgs_route(ctx: BankTransferContext) -> None:
    """SATNA route contract or soft outage."""
    _skip_outage(ctx, "Mellat RTGS outage")
    attach_api_result("rtgs route", ctx.route_result)
    report = AssertionReport("mellat RTGS route")
    report.equals("HTTP", actual=ctx.route_result.get("status_code"), expected=200)
    body = route_body_fields(ctx.route_result)
    if isinstance(body, TransferRouteBody):
        report.equals("client", actual=body.client_code, expected="bn_mellat")
        report.check("type RTGS", body.type in RTGS_TYPE_TOKENS)
    doc = ctx.mongo_doc or {}
    report.check(
        "mongo RTGS",
        doc.get("type") in RTGS_TYPE_TOKENS | {"RTGS", "RTGS_TRANSFER", 1, "1"},
    )
    report.assert_all()


def assert_rtgs_inquiry(ctx: BankTransferContext) -> None:
    """Inquiry after RTGS route."""
    _skip_outage(ctx, "Mellat RTGS outage")
    assert_rtgs_route(ctx)
    attach_api_result("inquiry", ctx.inquiry_result)
    report = AssertionReport("rtgs inquiry")
    report.equals("HTTP", actual=ctx.inquiry_result.get("status_code"), expected=200)
    body = route_body_fields(ctx.inquiry_result)
    report.equals("ROUTED", actual=body.status if body else None, expected=INQ_ROUTED)
    report.assert_all()


def assert_rtgs_live(ctx: BankTransferContext) -> None:
    """Live RTGS settle."""
    _skip_outage(ctx, "Mellat RTGS outage")
    report = AssertionReport("rtgs live")
    report.equals("DONE", actual=ctx.flags.get("mongo_status"), expected="DONE")
    amt = ctx.flags.get("tx_amount")
    report.check(
        "amount floor",
        amt is not None and int(amt) >= ctx.secrets.mellat_rtgs_min_amount,
    )
    report.assert_all()


def assert_rtgs_reference(ctx: BankTransferContext) -> None:
    """Reference DONE SATNA transfer."""
    report = AssertionReport("rtgs reference")
    report.equals("DONE", actual=ctx.flags.get("mongo_status"), expected="DONE")
    report.check(
        "type RTGS",
        ctx.flags.get("mongo_type") in RTGS_TYPE_TOKENS | {"RTGS", "RTGS_TRANSFER", 1, "1"},
    )
    report.equals(
        "inquiry HTTP",
        actual=ctx.inquiry_result.get("status_code"),
        expected=200,
    )
    report.assert_all()
