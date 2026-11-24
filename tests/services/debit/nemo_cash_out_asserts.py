"""Assertions for Nemo cash-out predict + register."""

from __future__ import annotations

import pytest

from tests.services.assert_report import AssertionReport, attach_api_result
from tests.services.debit.nemo_cash_out import NemoCashOutContext
from tests.services.debit.nemo_secrets import PLATFORM_CLIENT_REJECT_TITLES

HTTP_CLIENT_ERROR_MIN = 400


def assert_predict_case(ctx: NemoCashOutContext, case: str) -> None:
    """Dispatch predict Then."""
    {
        "configured card fee": assert_predict_success,
        "marker amount fee": assert_predict_success,
        "min boundary fee": assert_predict_success,
        "max boundary fee": assert_predict_success,
        "unknown user rejected": assert_predict_unknown,
        "missing target pan rejected": assert_invalid_parameter,
        "zero amount rejected": assert_invalid_parameter,
        "negative amount rejected": assert_invalid_parameter,
        "empty pan value rejected": assert_invalid_parameter,
        "missing pan value field rejected": assert_client_error,
        "invalid pan type rejected": assert_client_error,
        "huge amount not amount range": assert_predict_huge,
        "card secure store diagnostic": assert_secure_store_diag,
    }[case](ctx)


def assert_register_case(ctx: NemoCashOutContext, case: str) -> None:
    """Dispatch register Then."""
    {
        "success and detail": assert_register_success,
        "min amount boundary": assert_register_min,
        "max amount boundary": assert_register_max,
        "poll to terminal": assert_register_terminal,
        "unknown user rejected": assert_register_unknown,
        "invalid iban rejected": assert_invalid_parameter,
        "iban with spaces rejected": assert_invalid_parameter,
        "missing iban rejected": assert_invalid_parameter,
        "missing birth date rejected": assert_invalid_parameter,
        "invalid birth date rejected": assert_invalid_parameter,
        "amount below min rejected": assert_amount_range,
        "amount above max rejected": assert_amount_range,
        "detail unknown tracking": assert_detail_unknown,
    }[case](ctx)


def assert_predict_success(ctx: NemoCashOutContext) -> None:
    """Predict SUCCESS with fee present."""
    attach_api_result("predict", ctx.last_result)
    title = ctx.flags.get("title")
    if (
        ctx.flags.get("status_code") == 422
        and title == "SECURE_STORE_GENERIC_ERROR"
    ):
        pytest.skip(
            "Nemo card predict blocked by SECURE_STORE_GENERIC_ERROR on UAT "
            "(same outage covered by SET-T551 diagnostic)"
        )
    report = AssertionReport("nemo predict success")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=200)
    report.equals("title", actual=title, expected="SUCCESS")
    report.check("fee present", ctx.flags.get("fee") is not None)
    report.assert_all()


def assert_predict_unknown(ctx: NemoCashOutContext) -> None:
    """Unknown user predict reject."""
    attach_api_result("predict unknown", ctx.last_result)
    report = AssertionReport("nemo predict unknown user")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=422)
    report.check(
        "title",
        ctx.flags.get("title") in ("USER_NOT_FOUND", "SECURE_STORE_GENERIC_ERROR"),
    )
    report.assert_all()


def assert_invalid_parameter(ctx: NemoCashOutContext) -> None:
    """422 INVALID_PARAMETER."""
    attach_api_result("reject", ctx.last_result)
    report = AssertionReport("nemo invalid parameter")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=422)
    report.equals("title", actual=ctx.flags.get("title"), expected="INVALID_PARAMETER")
    report.assert_all()


def assert_client_error(ctx: NemoCashOutContext) -> None:
    """HTTP 400 or 422 client error."""
    attach_api_result("client error", ctx.last_result)
    code = int(ctx.flags.get("status_code") or 0)
    report = AssertionReport("nemo client error")
    report.check("HTTP 400 or 422", code in (HTTP_CLIENT_ERROR_MIN, 422))
    report.assert_all()


def assert_predict_huge(ctx: NemoCashOutContext) -> None:
    """Huge amount is not AMOUNT_IS_NOT_IN_RANGE."""
    attach_api_result("predict huge", ctx.last_result)
    report = AssertionReport("nemo predict huge")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=422)
    title = ctx.flags.get("title")
    report.check("not amount range", title != "AMOUNT_IS_NOT_IN_RANGE")
    report.check("reject title", title in PLATFORM_CLIENT_REJECT_TITLES)
    report.assert_all()


def assert_secure_store_diag(ctx: NemoCashOutContext) -> None:
    """Diagnostic: UAT may return SECURE_STORE_GENERIC_ERROR."""
    attach_api_result("predict secure-store diag", ctx.last_result)
    title = ctx.flags.get("title")
    code = int(ctx.flags.get("status_code") or 0)
    if code == 200 and title == "SUCCESS":
        pytest.skip(
            "Card predict succeeded — SECURE_STORE diagnostic not triggered on UAT"
        )
    report = AssertionReport("nemo secure-store diagnostic")
    report.equals("HTTP", actual=code, expected=422)
    report.equals("title", actual=title, expected="SECURE_STORE_GENERIC_ERROR")
    report.assert_all()


def assert_register_success(ctx: NemoCashOutContext) -> None:
    """Register creates cash_out and detail succeeds."""
    attach_api_result("register", ctx.last_result)
    attach_api_result("detail", ctx.detail_result)
    report = AssertionReport("nemo register success")
    report.check("delta", int(ctx.flags.get("cash_out_delta") or 0) >= 1)
    report.equals(
        "detail HTTP",
        actual=ctx.flags.get("detail_status_code"),
        expected=200,
    )
    report.equals("detail title", actual=ctx.flags.get("detail_title"), expected="SUCCESS")
    report.assert_all()


def assert_register_min(ctx: NemoCashOutContext) -> None:
    """Min amount register SUCCESS."""
    attach_api_result("register min", ctx.last_result)
    report = AssertionReport("nemo register min")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=200)
    report.equals("title", actual=ctx.flags.get("title"), expected="SUCCESS")
    report.check("not amount range", ctx.flags.get("title") != "AMOUNT_IS_NOT_IN_RANGE")
    report.assert_all()


def assert_register_max(ctx: NemoCashOutContext) -> None:
    """Max amount SUCCESS or non-range failure."""
    attach_api_result("register max", ctx.last_result)
    code = int(ctx.flags.get("status_code") or 0)
    title = ctx.flags.get("title")
    report = AssertionReport("nemo register max")
    if ctx.flags.get("is_max") and code != 200:
        report.check(
            "not range/invalid",
            title not in ("AMOUNT_IS_NOT_IN_RANGE", "INVALID_PARAMETER"),
        )
        report.assert_all()
        return
    report.equals("HTTP", actual=code, expected=200)
    report.equals("title", actual=title, expected="SUCCESS")
    report.assert_all()


def assert_register_terminal(ctx: NemoCashOutContext) -> None:
    """Cash-out reaches a terminal wallet status."""
    report = AssertionReport("nemo register terminal")
    report.equals("detail title", actual=ctx.flags.get("detail_title"), expected="SUCCESS")
    report.check("terminal", ctx.flags.get("terminal_ok") is True)
    report.assert_all()


def assert_register_unknown(ctx: NemoCashOutContext) -> None:
    """Unknown user register reject."""
    attach_api_result("register unknown", ctx.last_result)
    report = AssertionReport("nemo register unknown")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=422)
    report.equals("title", actual=ctx.flags.get("title"), expected="USER_NOT_FOUND")
    report.assert_all()


def assert_amount_range(ctx: NemoCashOutContext) -> None:
    """Amount out of product range."""
    attach_api_result("amount range", ctx.last_result)
    report = AssertionReport("nemo amount range")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=422)
    report.equals(
        "title",
        actual=ctx.flags.get("title"),
        expected="AMOUNT_IS_NOT_IN_RANGE",
    )
    report.assert_all()


def assert_detail_unknown(ctx: NemoCashOutContext) -> None:
    """Unknown tracking detail reject."""
    attach_api_result("detail unknown", ctx.last_result)
    report = AssertionReport("nemo detail unknown")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=422)
    report.check(
        "title",
        ctx.flags.get("title") in ("FAILURE", "PAYMENT_NOT_FOUND"),
    )
    report.assert_all()
