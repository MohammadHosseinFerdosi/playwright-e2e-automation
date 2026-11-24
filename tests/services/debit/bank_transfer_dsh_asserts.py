"""Assertions for Mellat DSH (SET-T448..T475)."""

from __future__ import annotations

import pytest

from tests.services.assert_report import AssertionReport, attach_api_result
from tests.services.debit import bank_transfer_statements as stmts
from tests.services.debit.bank_transfer import (
    BankTransferContext,
    route_body_fields,
    title_of,
)
from tests.services.debit.bank_transfer_routing import skip_if_switch_setup

CROSS_BANK_REJECT_TITLES = frozenset(
    {
        "INVALID_PARAMETER",
        "FAILURE",
        "BAD_REQUEST",
        "BANKPROXY_NO_GATEWAY",
    }
)
PLATFORM_REJECT_TITLES = frozenset(
    {
        "INVALID_PARAMETER",
        "FAILURE",
        "BAD_REQUEST",
        "TRANSACTION_NOT_FOUND",
        "BANKPROXY_DUPLICATE_TRANSACTION",
        "BANKPROXY_NO_GATEWAY",
        "BANKPROXY_BANK_UNKNOWN_ERROR",
        "BANKPROXY_AMOUNT_INVALID",
        "BANKPROXY_CREDIT_NOT_ENOUGH",
        "UNKNOWN",
        "SECURE_STORE_GENERIC_ERROR",
    }
)
IDEMPOTENT_SECOND = frozenset(
    {"BANKPROXY_DUPLICATE_TRANSACTION", "INVALID_PARAMETER", "FAILURE"}
)
PROGRESS_STATES = frozenset(
    {"DONE", "REJECT", "CANCEL", "IN_PROGRESS", "SUCCEED", "PENDING"}
)
HTTP_SERVER_ERROR_MIN = 500
HTTP_CLIENT_ERROR_MIN = 400


def assert_dsh_case(ctx: BankTransferContext, case: str) -> None:
    """Dispatch Then for a Mellat DSH case key."""
    dispatch = {
        "cross-bank iban matrix": assert_cross_bank_matrix,
        "owner xss payloads": assert_no_server_error_probes,
        "description sql injection": assert_description_sql,
        "injection tracking inquiry": assert_tracking_injection,
        "oversized payload": assert_ok_or_client_error,
        "decimal amount": assert_decimal_amount,
        "negative amount": assert_negative_amount,
        "iban with spaces": assert_iban_spaces,
        "duplicate different amount": assert_duplicate_different_amount,
        "duplicate same tracking": assert_duplicate_same_tracking,
        "missing iban": assert_missing_iban,
        "string amount": assert_string_amount,
        "minimum amount": assert_minimum_amount,
        "weight switch live transfer": assert_weight_switch_live,
        "prod route transfer settle": assert_prod_settle,
        "max client amount": assert_max_client_amount,
        "concurrent duplicate execute": assert_concurrent_execute,
        "duplicate execute": assert_duplicate_execute,
        "transfer after route": assert_transfer_in_progress,
        "statements apis smoke": assert_statements_apis,
        "creditor statement rows": assert_creditor_rows,
        "invalid statements dates": assert_invalid_dates,
        "invalid account statement dates": assert_invalid_dates,
        "live transfer on provider statement": assert_live_on_statement,
        "configured done statement amounts": assert_configured_amounts,
        "statements pagination": assert_pagination,
        "live reconcile journey": assert_live_reconcile,
    }
    dispatch[case](ctx)


def _skip_outage(ctx: BankTransferContext, prefix: str) -> None:
    if ctx.flags.get("outage"):
        pytest.skip(f"{prefix}: {ctx.flags.get('outage_reason') or 'UAT outage'}")


def assert_cross_bank_matrix(ctx: BankTransferContext) -> None:
    """Three foreign IBANs rejected with Platform titles."""
    for title in ctx.probe_titles:
        skip_if_switch_setup(title, reason="cross-bank matrix Switch setup")
    report = AssertionReport("cross-bank IBAN matrix rejected")
    report.equals("count", actual=ctx.flags.get("rejected_count"), expected=3)
    report.equals("codes len", actual=len(ctx.probe_codes), expected=3)
    report.check("all 422", all(c == 422 for c in ctx.probe_codes))
    report.check(
        "titles",
        all(t in CROSS_BANK_REJECT_TITLES for t in ctx.probe_titles),
    )
    report.assert_all()


def assert_no_server_error_probes(ctx: BankTransferContext) -> None:
    """XSS / security probes stay below HTTP 500; client errors carry Platform titles."""
    report = AssertionReport("owner XSS probes no server error")
    max_status = int(ctx.flags.get("max_status") or 0)
    report.check("status below 500", max_status < HTTP_SERVER_ERROR_MIN)
    report.equals(
        "pairs", actual=len(ctx.probe_titles), expected=len(ctx.probe_codes)
    )
    for code, title in zip(ctx.probe_codes, ctx.probe_titles, strict=True):
        if HTTP_CLIENT_ERROR_MIN <= code < HTTP_SERVER_ERROR_MIN:
            report.check(f"title {code}", title in PLATFORM_REJECT_TITLES)
    report.assert_all()


def assert_description_sql(ctx: BankTransferContext) -> None:
    """SQL description leaves mongo collections intact; status below 500."""
    attach_api_result("sql description route", ctx.last_result)
    report = AssertionReport("description SQL injection safe")
    report.check("collections_ok", ctx.flags.get("collections_ok") is True)
    code = int(ctx.last_result.get("status_code") or 0)
    report.check("status below 500", code < HTTP_SERVER_ERROR_MIN)
    if HTTP_CLIENT_ERROR_MIN <= code < HTTP_SERVER_ERROR_MIN:
        report.check("reject title", title_of(ctx.last_result) in PLATFORM_REJECT_TITLES)
    report.assert_all()


def assert_tracking_injection(ctx: BankTransferContext) -> None:
    """Injection inquiries stay below HTTP 500 and do not leak foreign transactions."""
    report = AssertionReport("tracking injection inquiry safe")
    report.check(
        "status below 500",
        int(ctx.flags.get("max_status") or 0) < HTTP_SERVER_ERROR_MIN,
    )
    report.check("no leak", ctx.flags.get("leaked") is False)
    report.assert_all()


def assert_ok_or_client_error(ctx: BankTransferContext) -> None:
    """Single route: HTTP 200 or Platform client reject; status below 500."""
    attach_api_result("route", ctx.last_result)
    report = AssertionReport("route handled without server error")
    code = int(ctx.last_result.get("status_code") or 0)
    report.check("status below 500", code < HTTP_SERVER_ERROR_MIN)
    if HTTP_CLIENT_ERROR_MIN <= code < HTTP_SERVER_ERROR_MIN:
        report.check("reject title", title_of(ctx.last_result) in PLATFORM_REJECT_TITLES)
    report.assert_all()


def _ok_or_reject(
    report: AssertionReport,
    *,
    code: int,
    title: str | None,
    on_ok: bool,
) -> None:
    if code == 200:
        report.check("ok branch", on_ok)
        return
    report.check("client error", HTTP_CLIENT_ERROR_MIN <= code < HTTP_SERVER_ERROR_MIN)
    report.check("reject title", title in PLATFORM_REJECT_TITLES)


def assert_decimal_amount(ctx: BankTransferContext) -> None:
    """Decimal amount never stores 10000.5 on success."""
    attach_api_result("decimal route", ctx.last_result)
    report = AssertionReport("decimal amount handled")
    code = int(ctx.last_result.get("status_code") or 0)
    ok = ctx.stored_amount != 10000.5
    _ok_or_reject(report, code=code, title=title_of(ctx.last_result), on_ok=ok)
    report.assert_all()


def assert_negative_amount(ctx: BankTransferContext) -> None:
    """Negative amount → 422 INVALID_PARAMETER."""
    attach_api_result("negative amount", ctx.last_result)
    report = AssertionReport("negative amount rejected")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=422)
    report.equals("title", actual=title_of(ctx.last_result), expected="INVALID_PARAMETER")
    report.assert_all()


def assert_iban_spaces(ctx: BankTransferContext) -> None:
    """Spaced IBAN OK on Mellat or Platform reject."""
    attach_api_result("spaced iban", ctx.last_result)
    report = AssertionReport("IBAN with spaces handled")
    code = int(ctx.last_result.get("status_code") or 0)
    body = route_body_fields(ctx.last_result)
    on_ok = False
    if code == 200 and body is not None:
        on_ok = body.client_code == "bn_mellat" and body.bank_code == "012"
    _ok_or_reject(report, code=code, title=title_of(ctx.last_result), on_ok=on_ok)
    report.assert_all()


def assert_duplicate_same_tracking(ctx: BankTransferContext) -> None:
    """First OK; second OK or idempotent reject; one mongo row."""
    attach_api_result("first", ctx.route_result)
    attach_api_result("second", ctx.second_result)
    report = AssertionReport("duplicate route single mongo row")
    report.equals("first HTTP", actual=ctx.route_result.get("status_code"), expected=200)
    code2 = int(ctx.second_result.get("status_code") or 0)
    title2 = title_of(ctx.second_result)
    if code2 != 200:
        report.check("second client error", HTTP_CLIENT_ERROR_MIN <= code2 < 500)
        report.check("second title", title2 in IDEMPOTENT_SECOND | PLATFORM_REJECT_TITLES)
    report.equals("mongo count", actual=ctx.mongo_count, expected=1)
    report.assert_all()


def assert_duplicate_different_amount(ctx: BankTransferContext) -> None:
    """First OK; second rejected; still one mongo row."""
    attach_api_result("first", ctx.route_result)
    attach_api_result("second", ctx.second_result)
    report = AssertionReport("duplicate route different amount rejected")
    report.equals("first HTTP", actual=ctx.route_result.get("status_code"), expected=200)
    code2 = int(ctx.second_result.get("status_code") or 0)
    title2 = title_of(ctx.second_result)
    report.check("second rejected", code2 != 200)
    report.check("second client error", HTTP_CLIENT_ERROR_MIN <= code2 < 500)
    report.check("second title", title2 in IDEMPOTENT_SECOND | PLATFORM_REJECT_TITLES)
    report.equals("mongo count", actual=ctx.mongo_count, expected=1)
    report.assert_all()


def assert_missing_iban(ctx: BankTransferContext) -> None:
    """Empty IBAN rejected; no mongo row."""
    attach_api_result("missing iban", ctx.last_result)
    report = AssertionReport("route without IBAN rejected")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=422)
    report.equals("title", actual=title_of(ctx.last_result), expected="INVALID_PARAMETER")
    report.check("mongo missing", ctx.flags.get("mongo_missing") is True)
    report.assert_all()


def assert_string_amount(ctx: BankTransferContext) -> None:
    """String amount coerces to numeric on success."""
    attach_api_result("string amount", ctx.last_result)
    report = AssertionReport("string amount handled")
    code = int(ctx.last_result.get("status_code") or 0)
    amt = ctx.stored_amount
    on_ok = isinstance(amt, (int, float)) and not isinstance(amt, bool)
    _ok_or_reject(report, code=code, title=title_of(ctx.last_result), on_ok=on_ok)
    report.assert_all()


def assert_minimum_amount(ctx: BankTransferContext) -> None:
    """Amount=1 stores 1 on success."""
    attach_api_result("min amount", ctx.last_result)
    report = AssertionReport("minimum amount boundary")
    code = int(ctx.last_result.get("status_code") or 0)
    on_ok = ctx.stored_amount == 1
    _ok_or_reject(report, code=code, title=title_of(ctx.last_result), on_ok=on_ok)
    report.assert_all()


def assert_weight_switch_live(ctx: BankTransferContext) -> None:
    """Blocked while zeroed; then DONE with bankTrackingCode."""
    report = AssertionReport("weight switch live settle")
    report.equals("block HTTP", actual=ctx.flags.get("block_status"), expected=422)
    report.equals("mongo DONE", actual=ctx.flags.get("mongo_status"), expected="DONE")
    report.equals("client", actual=ctx.flags.get("client_code"), expected="bn_mellat")
    report.truthy("bankTrackingCode", ctx.flags.get("bank_ref"))
    report.assert_all()


def assert_prod_settle(ctx: BankTransferContext) -> None:
    """Production path settles DONE on bn_mellat."""
    report = AssertionReport("prod route transfer settle")
    report.equals("mongo DONE", actual=ctx.flags.get("mongo_status"), expected="DONE")
    report.equals("client", actual=ctx.flags.get("client_code"), expected="bn_mellat")
    report.assert_all()


def assert_max_client_amount(ctx: BankTransferContext) -> None:
    """Huge amount rejected on route or on execute."""
    report = AssertionReport("max client amount boundary")
    route_status = int(ctx.flags.get("route_status") or 0)
    route_title = ctx.flags.get("route_title")
    if route_status == 200:
        report.equals(
            "transfer HTTP",
            actual=ctx.flags.get("transfer_status"),
            expected=422,
        )
        report.check(
            "transfer title",
            ctx.flags.get("transfer_title") in PLATFORM_REJECT_TITLES,
        )
    else:
        report.check(
            "route client error",
            HTTP_CLIENT_ERROR_MIN <= route_status < HTTP_SERVER_ERROR_MIN,
        )
        report.check("route title", route_title in PLATFORM_REJECT_TITLES)
    report.assert_all()


def assert_concurrent_execute(ctx: BankTransferContext) -> None:
    """Exactly one concurrent execute succeeds."""
    report = AssertionReport("concurrent duplicate execute race")
    codes = ctx.probe_codes
    report.check("has codes", bool(codes))
    report.equals("exactly one 200", actual=codes.count(200), expected=1)
    for code, title in zip(codes, ctx.probe_titles, strict=True):
        if code == 200:
            continue
        report.check(
            f"loser {code}",
            HTTP_CLIENT_ERROR_MIN <= code < HTTP_SERVER_ERROR_MIN,
        )
        report.check(f"loser title {title}", title in IDEMPOTENT_SECOND | PLATFORM_REJECT_TITLES)
    report.check(
        "journals",
        int(ctx.flags.get("transfer_journal_count") or 0) <= 1,
    )
    report.assert_all()


def assert_duplicate_execute(ctx: BankTransferContext) -> None:
    """Second execute is 422 duplicate/failure."""
    attach_api_result("second execute", ctx.second_result)
    report = AssertionReport("duplicate execute rejected")
    report.equals("HTTP", actual=ctx.second_result.get("status_code"), expected=422)
    title = (title_of(ctx.second_result) or "").upper()
    report.check(
        "title",
        "DUPLICATE" in title
        or title_of(ctx.second_result) in ("FAILURE", "INVALID_PARAMETER"),
    )
    report.assert_all()


def assert_transfer_in_progress(ctx: BankTransferContext) -> None:
    """Mongo status after execute is progress/end, not INITIATED."""
    report = AssertionReport("transfer after route in progress")
    status = ctx.flags.get("mongo_status")
    report.check("progress", status in PROGRESS_STATES)
    report.check("not INITIATED", status != "INITIATED")
    report.assert_all()


def assert_statements_apis(ctx: BankTransferContext) -> None:
    """Account statements smoke returns SUCCESS."""
    _skip_outage(ctx, "Mellat statements API outage")
    attach_api_result("account statements", ctx.last_result)
    report = AssertionReport("statements APIs succeed")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=200)
    report.equals("title", actual=ctx.flags.get("title"), expected="SUCCESS")
    report.assert_all()


def assert_creditor_rows(ctx: BankTransferContext) -> None:
    """Creditor rows validated."""
    _skip_outage(ctx, "Mellat creditor statements outage")
    report = AssertionReport("creditor PAYA amounts")
    report.check("creditor_ok", ctx.flags.get("creditor_ok") is True)
    report.check("item_count", int(ctx.flags.get("item_count") or 0) >= 0)
    report.assert_all()


def assert_invalid_dates(ctx: BankTransferContext) -> None:
    """Invalid date window is HTTP 422 Platform title (status below 500)."""
    title = str(ctx.flags.get("title") or "")
    code = int(ctx.flags.get("status_code") or 0)
    if stmts.is_outage_text(title) or stmts.is_outage_text(str(code)):
        pytest.skip(
            f"Cannot prove invalid-date contract while statements outage "
            f"(status={code} title={title})"
        )
    report = AssertionReport("invalid statement date range rejected")
    report.equals("HTTP", actual=code, expected=422)
    report.check(
        "title",
        title in ("INVALID_PARAMETER", "BAD_REQUEST", "FAILURE"),
    )
    report.assert_all()


def assert_live_on_statement(ctx: BankTransferContext) -> None:
    """Live transfer DONE on provider statement."""
    _skip_outage(ctx, "Mellat provider statement outage")
    report = AssertionReport("transfer on provider statement")
    report.equals("mongo DONE", actual=ctx.flags.get("mongo_status"), expected="DONE")
    report.equals("client", actual=ctx.flags.get("client_code"), expected="bn_mellat")
    report.assert_all()


def assert_configured_amounts(ctx: BankTransferContext) -> None:
    """Configured DONE TC statement amounts hold."""
    _skip_outage(ctx, "Mellat statement amount outage")
    report = AssertionReport("configured DONE statement amounts")
    report.equals("mongo DONE", actual=ctx.flags.get("mongo_status"), expected="DONE")
    report.truthy("tracking", ctx.tracking_code)
    report.check("amount_ok", ctx.flags.get("amount_ok") is True)
    report.assert_all()


def assert_pagination(ctx: BankTransferContext) -> None:
    """Pagination contract held."""
    _skip_outage(ctx, "Mellat statements pagination outage")
    report = AssertionReport("statements pagination")
    report.check("pagination_ok", ctx.flags.get("pagination_ok") is True)
    report.assert_all()


def assert_live_reconcile(ctx: BankTransferContext) -> None:
    """Live reconcile: DONE on mellat (statement soft)."""
    report = AssertionReport("live reconcile mongo inquiry statement")
    report.equals("mongo DONE", actual=ctx.flags.get("mongo_status"), expected="DONE")
    report.equals("client", actual=ctx.flags.get("client_code"), expected="bn_mellat")
    report.equals(
        "inquiry HTTP",
        actual=ctx.inquiry_result.get("status_code"),
        expected=200,
    )
    report.assert_all()
