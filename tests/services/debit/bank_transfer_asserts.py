"""Assertions for bank-transfer Debit BDD."""

from __future__ import annotations

from tests.api.debit.bank_transfer.models import TransferRouteBody
from tests.services.assert_report import AssertionReport, attach_api_result
from tests.services.debit.bank_transfer import (
    ACH_TYPE_TOKENS,
    INTERNAL_TYPE_TOKENS,
    NO_GATEWAY_TITLES,
    TYPE_INTERNAL,
    BankTransferContext,
    route_body_fields,
    title_of,
)
from tests.services.debit.bank_transfer_routing import skip_if_switch_setup


def _off_title(ctx: BankTransferContext) -> str | None:
    """Switch/product title stored on the zero-weight probe."""
    raw = ctx.flags.get("off_title")
    return raw if isinstance(raw, str) else None


def assert_route_rejected_no_gateway(ctx: BankTransferContext) -> None:
    """Route rejected when no active weighted gateway is available."""
    attach_api_result("route attempt", ctx.last_result)
    title = title_of(ctx.last_result)
    skip_if_switch_setup(title, reason="no-gateway Switch setup")
    report = AssertionReport("route rejected — no gateway")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=422)
    report.check("title", title in NO_GATEWAY_TITLES)
    report.assert_all()


def assert_zero_weight_block_then_pin(ctx: BankTransferContext) -> None:
    """Zero weights reject with no gateway; pin Mellat then route succeeds."""
    title = _off_title(ctx)
    skip_if_switch_setup(title, reason="no-gateway Switch setup")
    report = AssertionReport("zero weights block then pin")
    report.equals("off HTTP", actual=ctx.flags.get("off_status"), expected=422)
    report.check("off title", title in NO_GATEWAY_TITLES)
    report.check("off no doc", ctx.flags.get("off_doc_missing") is True)
    report.assert_all()
    assert_route_on_pinned_gateway(ctx)


def assert_route_on_pinned_gateway(ctx: BankTransferContext) -> None:
    """Successful route lands on Mellat INTERNAL with zero fee."""
    attach_api_result("pinned route", ctx.route_result)
    secrets = CHANGE_ME
    report = AssertionReport("route on pinned gateway")
    report.equals(
        "HTTP", actual=ctx.route_result.get("status_code"), expected=200
    )
    body = route_body_fields(ctx.route_result)
    report.check("route body typed", isinstance(body, TransferRouteBody))
    if isinstance(body, TransferRouteBody):
        report.equals(
            "clientCode", actual=body.client_code, expected=secrets.mellat_client_code
        )
        report.equals(
            "bankCode", actual=body.bank_code, expected=secrets.mellat_bank_code
        )
        report.equals("type", actual=body.type, expected=TYPE_INTERNAL)
        report.equals("fee", actual=body.fee, expected=0)
    report.truthy("tracking code", ctx.tracking_code)
    report.truthy("transfer row", ctx.mongo_doc is not None)
    if ctx.mongo_doc is not None:
        report.equals("fee", actual=ctx.mongo_doc.get("fee"), expected=0)
    report.assert_all()


def assert_internal_fee_zero(ctx: BankTransferContext) -> None:
    """Successful internal route has fee 0 on the body and mongo row."""
    result = ctx.route_result or ctx.last_result
    attach_api_result("fee", result)
    report = AssertionReport("internal fee is zero")
    report.equals("HTTP", actual=result.get("status_code"), expected=200)
    if result.get("status_code") != 200:
        report.note(f"route title={title_of(result)!r}")
    body = route_body_fields(result)
    report.check("typed route body", isinstance(body, TransferRouteBody))
    if isinstance(body, TransferRouteBody):
        report.equals("route fee", actual=body.fee, expected=0)
    report.truthy("transfer row", ctx.mongo_doc is not None)
    if ctx.mongo_doc is not None:
        report.equals("mongo fee", actual=ctx.mongo_doc.get("fee"), expected=0)
    report.assert_all()


def assert_inquiry_reports_active_gateway(ctx: BankTransferContext) -> None:
    """Inquiry after route shows the pinned Mellat client/bank."""
    attach_api_result("inquiry", ctx.inquiry_result)
    secrets = CHANGE_ME
    report = AssertionReport("inquiry reports active gateway")
    report.equals(
        "HTTP", actual=ctx.inquiry_result.get("status_code"), expected=200
    )
    body = route_body_fields(ctx.inquiry_result)
    report.check("typed body", isinstance(body, TransferRouteBody))
    if isinstance(body, TransferRouteBody):
        report.equals(
            "clientCode", actual=body.client_code, expected=secrets.mellat_client_code
        )
        report.equals(
            "bankCode", actual=body.bank_code, expected=secrets.mellat_bank_code
        )
    report.truthy("tracking code", ctx.tracking_code)
    report.assert_all()


def assert_transfer_remains_initiated(ctx: BankTransferContext) -> None:
    """After route+inquiry without execute, transfer stays initiated."""
    attach_api_result("inquiry", ctx.inquiry_result)
    report = AssertionReport("transfer remains initiated")
    report.equals(
        "HTTP", actual=ctx.inquiry_result.get("status_code"), expected=200
    )
    doc = ctx.mongo_doc or {}
    report.truthy("transfer row", bool(doc))
    report.equals("status", actual=doc.get("status"), expected="INITIATED")
    journals = doc.get("journals") or []
    actions = [item.get("action") for item in journals if isinstance(item, dict)]
    report.check("no TRANSFER journal", "TRANSFER" not in actions)
    report.assert_all()


def assert_environment_preflight(ctx: BankTransferContext) -> None:
    """CASH_OUT mongo is reachable for Debit QA."""
    report = AssertionReport("environment preflight")
    report.check("preflight ok", ctx.preflight_ok)
    report.assert_all()


def assert_mellat_client_active(ctx: BankTransferContext) -> None:
    """Mellat INTERNAL client is active after pin."""
    report = AssertionReport("mellat client active")
    report.truthy("client row", ctx.client_row is not None)
    if ctx.client_row is not None:
        weight = ctx.client_row.get("selectionWeight")
        report.check("weight >= 0", weight is not None and int(weight) >= 0)
    report.assert_all()


def assert_route_contract_with_journal(ctx: BankTransferContext) -> None:
    """Route contract: Mellat INTERNAL, fee 0, ROUTE journal present."""
    assert_route_on_pinned_gateway(ctx)
    report = AssertionReport("route journal")
    doc = ctx.mongo_doc or {}
    journals = doc.get("journals") or []
    actions = [item.get("action") for item in journals if isinstance(item, dict)]
    report.check("ROUTE journal", "ROUTE" in actions)
    report.assert_all()


def assert_duplicate_route_single_mongo_row(ctx: BankTransferContext) -> None:
    """First route OK; Mongo keeps a single row for the tracking code."""
    attach_api_result("first route", ctx.route_result)
    attach_api_result("second route", ctx.second_result)
    report = AssertionReport("duplicate route single row")
    report.equals(
        "first HTTP", actual=ctx.route_result.get("status_code"), expected=200
    )
    second = int(ctx.second_result.get("status_code") or 0)
    report.check("second OK or client error", second == 200 or 400 <= second < 500)
    report.equals("mongo count", actual=ctx.mongo_count, expected=1)
    report.assert_all()


def assert_mongo_initiated_after_marker_route(ctx: BankTransferContext) -> None:
    """Marker route leaves transfer INITIATED."""
    attach_api_result("marker route", ctx.route_result)
    report = AssertionReport("marker route initiated")
    report.equals(
        "HTTP", actual=ctx.route_result.get("status_code"), expected=200
    )
    doc = ctx.mongo_doc or {}
    report.equals("status", actual=doc.get("status"), expected="INITIATED")
    report.assert_all()


def assert_title_rejected(
    ctx: BankTransferContext, *, expected_title: str
) -> None:
    """HTTP 422 with a specific result title."""
    attach_api_result("rejected call", ctx.last_result)
    report = AssertionReport(f"rejected — {expected_title}")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=422)
    report.equals("title", actual=title_of(ctx.last_result), expected=expected_title)
    report.assert_all()


def assert_no_server_error(ctx: BankTransferContext) -> None:
    """Response status is below 500."""
    attach_api_result("injection probe", ctx.last_result)
    code = int(ctx.last_result.get("status_code") or 0)
    report = AssertionReport("no server error")
    report.check("status < 500", code < 500)
    report.assert_all()


def assert_never_ach_types(ctx: BankTransferContext) -> None:
    """No ACH type appears when Mellat INTERNAL is pinned."""
    report = AssertionReport("never ACH under pin")
    report.truthy("observed types", bool(ctx.route_types))
    report.check(
        "no ACH type",
        not any(t in ACH_TYPE_TOKENS for t in ctx.route_types),
    )
    report.check(
        "all INTERNAL or unset",
        all(t is None or t in INTERNAL_TYPE_TOKENS for t in ctx.route_types),
    )
    report.assert_all()


def assert_duplicate_iban_second_handled(ctx: BankTransferContext) -> None:
    """First route HTTP 200; second same tracking/different IBAN is 200 or 400-499."""
    attach_api_result("first", ctx.route_result)
    attach_api_result("second", ctx.second_result)
    report = AssertionReport("duplicate tracking different iban")
    report.equals(
        "first HTTP", actual=ctx.route_result.get("status_code"), expected=200
    )
    second = int(ctx.second_result.get("status_code") or 0)
    report.check("second OK or client error", second == 200 or 400 <= second < 500)
    report.equals("mongo count", actual=ctx.mongo_count, expected=1)
    report.assert_all()


def assert_scheduler_triggers_ok(ctx: BankTransferContext) -> None:
    """Both ACH scheduler triggers return HTTP 200."""
    report = AssertionReport("scheduler triggers")
    for name, result in ctx.scheduler_results.items():
        attach_api_result(name, result)
        report.equals(f"{name} HTTP", actual=result.get("status_code"), expected=200)
    report.assert_all()


def assert_same_bank_internal(ctx: BankTransferContext) -> None:
    """Same-bank Mellat route stays INTERNAL."""
    assert_route_on_pinned_gateway(ctx)
    report = AssertionReport("same bank internal")
    doc = ctx.mongo_doc or {}
    report.check(
        "mongo type INTERNAL",
        doc.get("type") in INTERNAL_TYPE_TOKENS,
    )
    report.assert_all()
