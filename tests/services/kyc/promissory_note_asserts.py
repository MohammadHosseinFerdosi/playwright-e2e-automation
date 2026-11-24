"""Assertions for promissory-note BDD."""

from __future__ import annotations

from typing import Any

from tests.api.kyc.models import KycResultBody
from tests.api.kyc.promissory_notes.models import (
    InquiryBody,
    ProviderSettingsBody,
    RouteBody,
    SettingsSearchBody,
    SuccessRateSearchBody,
    SuccessRateStatItem,
)
from tests.services.assert_report import (
    AssertionReport,
    attach_api_result,
    attach_json,
)
from tests.services.kyc.promissory_note import (
    INIT_DETAIL_FIELDS,
    INJECTED_FIELDS,
    PROVIDER_KUKNOS,
    PROVIDER_SADERAT,
    STATUS_CANCELED,
    STATUS_ROUTED,
    PromissoryNoteContext,
    PromissoryNoteFlow,
    note_generate_date,
)

_SUCCESS = "SUCCESS"
_SUCCESS_STATUS = 0
_NOT_FOUND = "PROMISSORY_NOTE_NOT_FOUND"
_INVALID_NOTE_STATUS = "PROMISSORY_NOTE_INVALID_STATUS"
_INVALID_REFUND = "PROMISSORY_NOTE_INVALID_REFUND_STATUS"
_PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
_FAILURE = "FAILURE"
_INVALID_PARAMETER = "INVALID_PARAMETER"
_FAILURE_STATUS = 1000
_FAILURE_LEVEL = "BLOCKER"
_NOT_FOUND_STATUS = 17709
_INVALID_NOTE_STATUS_CODE = 17711
_INVALID_PARAMETER_STATUS = 1054
_INVALID_REFUND_STATUS = 17741
_PAYMENT_NOT_FOUND_STATUS = 1042
_WARN_LEVEL = "WARN"
_FAILURE_MESSAGE = "عملیات ناموفق بود لطفا مجددا تلاش کنید"
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNPROCESSABLE = 422
HTTP_SERVER_ERROR = 500


def _result_obj(body: Any) -> Any:
    if isinstance(
        body,
        (KycResultBody, RouteBody, InquiryBody, SettingsSearchBody, SuccessRateSearchBody),
    ):
        return getattr(body, "result", None)
    if not isinstance(body, dict):
        return None
    return body.get("result")


def _result_field(body: Any, name: str) -> Any:
    result = _result_obj(body)
    if result is None:
        return None
    if isinstance(result, dict):
        return result.get(name)
    return getattr(result, name, None)


def result_title(body: Any) -> str | None:
    """``result.title`` from typed or raw body."""
    value = _result_field(body, "title")
    return value if isinstance(value, str) else None


def result_status(body: Any) -> int | None:
    """``result.status`` from typed or raw body."""
    value = _result_field(body, "status")
    return value if isinstance(value, int) else None


def result_level(body: Any) -> str | None:
    """``result.level`` from typed or raw body."""
    value = _result_field(body, "level")
    return value if isinstance(value, str) else None


def result_message(body: Any) -> str | None:
    """``result.message`` from typed or raw body."""
    value = _result_field(body, "message")
    return value if isinstance(value, str) else None


def _check_success_envelope(
    report: AssertionReport, envelope: dict[str, Any], *, http_label: str
) -> None:
    body = envelope.get("body")
    report.equals(http_label, actual=envelope.get("status_code"), expected=HTTP_OK)
    report.equals("result.title", actual=result_title(body), expected=_SUCCESS)
    report.equals("result.status", actual=result_status(body), expected=_SUCCESS_STATUS)


def assert_init_missing_detail(ctx: PromissoryNoteContext, detail: str) -> None:
    """Missing-detail init oracles for business outline values."""
    assert_init_missing_field(ctx, INIT_DETAIL_FIELDS[detail])


def assert_init_missing_field(ctx: PromissoryNoteContext, field: str) -> None:
    """Expected titles when a required init field is missing."""
    if field == "iban":
        assert_promissory_not_found(ctx)
        return
    if field == "amount":
        assert_invalid_parameter(ctx)
        return
    assert_business_failure(ctx, http=HTTP_UNPROCESSABLE)


def assert_promissory_not_found(ctx: PromissoryNoteContext) -> None:
    """422 + PROMISSORY_NOTE_NOT_FOUND + business status."""
    attach_api_result("promissory not found", ctx.last_result)
    body = ctx.last_result.get("body")
    report = AssertionReport("promissory not found")
    report.equals(
        "HTTP status", actual=ctx.last_result.get("status_code"), expected=HTTP_UNPROCESSABLE
    )
    report.equals("result.title", actual=result_title(body), expected=_NOT_FOUND)
    report.equals("result.status", actual=result_status(body), expected=_NOT_FOUND_STATUS)
    report.assert_all()


def assert_success(ctx: PromissoryNoteContext) -> None:
    """HTTP 200 + SUCCESS title + result.status 0."""
    attach_api_result("success", ctx.last_result)
    report = AssertionReport("success")
    _check_success_envelope(report, ctx.last_result, http_label="HTTP status")
    report.assert_all()


def assert_refund_invalid_status(ctx: PromissoryNoteContext) -> None:
    """Refund on GENERATED → 422 + INVALID_REFUND_STATUS."""
    attach_api_result("refund invalid status", ctx.last_result)
    body = ctx.last_result.get("body")
    report = AssertionReport("refund invalid status")
    report.equals(
        "HTTP status", actual=ctx.last_result.get("status_code"), expected=HTTP_UNPROCESSABLE
    )
    report.equals("result.title", actual=result_title(body), expected=_INVALID_REFUND)
    report.equals("result.status", actual=result_status(body), expected=_INVALID_REFUND_STATUS)
    report.equals("result.level", actual=result_level(body), expected=_WARN_LEVEL)
    report.assert_all()


def assert_refund_payment_not_found(ctx: PromissoryNoteContext) -> None:
    """Refund forced PAID without payment → 422 + PAYMENT_NOT_FOUND."""
    attach_api_result("refund payment not found", ctx.last_result)
    body = ctx.last_result.get("body")
    report = AssertionReport("refund payment not found")
    report.equals(
        "HTTP status", actual=ctx.last_result.get("status_code"), expected=HTTP_UNPROCESSABLE
    )
    report.equals("result.title", actual=result_title(body), expected=_PAYMENT_NOT_FOUND)
    report.equals(
        "result.status",
        actual=result_status(body),
        expected=_PAYMENT_NOT_FOUND_STATUS,
    )
    report.equals("result.level", actual=result_level(body), expected=_WARN_LEVEL)
    report.assert_all()


def assert_business_failure(ctx: PromissoryNoteContext, *, http: int | None = None) -> None:
    """FAILURE title with business status/level/message; optional HTTP status."""
    attach_api_result("business failure", ctx.last_result)
    body = ctx.last_result.get("body")
    report = AssertionReport("business failure")
    code = ctx.last_result.get("status_code")
    report.check(
        "not a server fault",
        isinstance(code, int) and int(code) < HTTP_SERVER_ERROR,
    )
    if http is not None:
        report.equals("HTTP status", actual=code, expected=http)
    report.equals("result.title", actual=result_title(body), expected=_FAILURE)
    report.equals("result.status", actual=result_status(body), expected=_FAILURE_STATUS)
    report.equals("result.level", actual=result_level(body), expected=_FAILURE_LEVEL)
    report.equals("result.message", actual=result_message(body), expected=_FAILURE_MESSAGE)
    report.assert_all()


def assert_invalid_parameter(ctx: PromissoryNoteContext) -> None:
    """422 + INVALID_PARAMETER + business status."""
    attach_api_result("invalid parameter", ctx.last_result)
    body = ctx.last_result.get("body")
    report = AssertionReport("invalid parameter")
    report.equals(
        "HTTP status", actual=ctx.last_result.get("status_code"), expected=HTTP_UNPROCESSABLE
    )
    report.equals("result.title", actual=result_title(body), expected=_INVALID_PARAMETER)
    report.equals(
        "result.status",
        actual=result_status(body),
        expected=_INVALID_PARAMETER_STATUS,
    )
    report.assert_all()


def assert_saderat_routed(flow: PromissoryNoteFlow, ctx: PromissoryNoteContext) -> None:
    """Assert route assigned the Saderat provider."""
    assert_route_provider(flow, ctx, provider=PROVIDER_SADERAT, label="Saderat route")


def assert_kuknos_routed(flow: PromissoryNoteFlow, ctx: PromissoryNoteContext) -> None:
    """Assert route assigned the Kuknos provider."""
    assert_route_provider(flow, ctx, provider=PROVIDER_KUKNOS, label="Kuknos route")


def assert_route_renew(ctx: PromissoryNoteContext, *, offered: bool) -> None:
    """Route body ``hasRenew`` matches expectation."""
    attach_api_result("route renew", ctx.route_result)
    report = AssertionReport("route renew")
    body = ctx.route_result.get("body")
    report.check("route body typed", isinstance(body, RouteBody))
    if isinstance(body, RouteBody):
        report.equals("hasRenew", actual=body.has_renew, expected=offered)
    report.assert_all()


def assert_start_invalid_note_status(ctx: PromissoryNoteContext) -> None:
    """422 ``PROMISSORY_NOTE_INVALID_STATUS`` — note is not renewable."""
    attach_api_result("invalid note status", ctx.last_result)
    body = ctx.last_result.get("body")
    report = AssertionReport("invalid note status")
    report.equals(
        "HTTP status",
        actual=ctx.last_result.get("status_code"),
        expected=HTTP_UNPROCESSABLE,
    )
    report.equals("result.title", actual=result_title(body), expected=_INVALID_NOTE_STATUS)
    report.equals(
        "result.status",
        actual=result_status(body),
        expected=_INVALID_NOTE_STATUS_CODE,
    )
    report.assert_all()


def assert_note_not_renewed(flow: PromissoryNoteFlow, ctx: PromissoryNoteContext) -> None:
    """Mongo is unchanged from the renew baseline (status and generateDate)."""
    report = AssertionReport("note not renewed")
    try:
        doc = flow.get_note(ctx.tracking_code or "")
    except RuntimeError as exc:
        report.error("mongo note", exc)
        report.assert_all()
        return
    retry_renew = int(doc.get("retryRenewCount") or 0)
    generate_date = note_generate_date(doc)
    attach_json(
        "renew flags",
        {
            "status": doc.get("status"),
            "generateDate": doc.get("generateDate"),
            "retryRenewCount": doc.get("retryRenewCount"),
            "retriedForRenew": doc.get("retriedForRenew"),
            "renewRejected": doc.get("renewRejected"),
        },
    )
    expected_status = ctx.status_before if ctx.status_before is not None else -999
    report.equals("mongo status", actual=int(doc.get("status", -999)), expected=expected_status)
    report.equals("retryRenewCount", actual=retry_renew, expected=ctx.retry_renew_before)
    report.equals("generateDate", actual=generate_date, expected=ctx.generate_date_before)
    report.assert_all()


def assert_route_provider(
    flow: PromissoryNoteFlow,
    ctx: PromissoryNoteContext,
    *,
    provider: int,
    label: str,
) -> None:
    """Route SUCCESS, provider enum, and Mongo PROVIDER_SELECTED."""
    attach_api_result("route", ctx.route_result)
    report = AssertionReport(label)
    _check_success_envelope(report, ctx.route_result, http_label="route HTTP")
    body = ctx.route_result.get("body")
    report.check("route body typed", isinstance(body, RouteBody))
    if isinstance(body, RouteBody):
        report.equals("route provider", actual=body.provider, expected=provider)
    _check_mongo_routed(report, flow, ctx.tracking_code or "")
    report.assert_all()


def _check_mongo_routed(
    report: AssertionReport, flow: PromissoryNoteFlow, tracking_code: str
) -> dict[str, Any] | None:
    try:
        doc = flow.get_note(tracking_code)
    except RuntimeError as exc:
        report.error("mongo note", exc)
        return None
    report.equals(
        "mongo status",
        actual=int(doc.get("status", -999)),
        expected=STATUS_ROUTED,
    )
    return doc


def assert_inquiry_status(ctx: PromissoryNoteContext) -> None:
    """Inquiry HTTP 200 and first note status matches expected."""
    attach_api_result("inquiry", ctx.last_result)
    report = AssertionReport("inquiry status")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=HTTP_OK)
    body = ctx.last_result.get("body")
    report.check("typed InquiryBody", isinstance(body, InquiryBody))
    expected = ctx.expected_inquiry_status
    report.truthy("expected status set", expected is not None)
    if isinstance(body, InquiryBody) and body.promissory_notes:
        report.equals(
            "note status",
            actual=body.promissory_notes[0].status,
            expected=expected,
        )
    else:
        report.check("has promissoryNotes", False)
    report.assert_all()


def assert_injected_route_ignored(flow: PromissoryNoteFlow, ctx: PromissoryNoteContext) -> None:
    """Route succeeds; injected client fields do not stick in Mongo."""
    attach_api_result("route injected", ctx.last_result)
    report = AssertionReport("route ignores injection")
    _check_success_envelope(report, ctx.last_result, http_label="HTTP")
    doc = _check_mongo_routed(report, flow, ctx.tracking_code or "")
    if doc is None:
        report.assert_all()
        return
    for key in (
        "treasuryId",
        "businessId",
        "initiator",
        "version",
        "sealedPromissoryNoteFileId",
        "signedPromissoryNoteFileId",
        "sourcePromissoryNoteFileId",
    ):
        report.check(
            f"{key} not injected",
            doc.get(key) != INJECTED_FIELDS.get(key),
        )
    report.assert_all()


def assert_injected_init_ignored(flow: PromissoryNoteFlow, ctx: PromissoryNoteContext) -> None:
    """Init succeeds; injected client fields do not stick in Mongo."""
    attach_api_result("init injected", ctx.init_result)
    report = AssertionReport("init ignores injection")
    _check_success_envelope(report, ctx.init_result, http_label="init HTTP")
    try:
        doc = flow.get_note(ctx.tracking_code or "")
    except RuntimeError as exc:
        report.error("mongo note", exc)
        report.assert_all()
        return
    report.check(
        "status not injected",
        int(doc.get("status", -999)) != int(INJECTED_FIELDS["status"]),
    )
    for key in (
        "treasuryId",
        "businessId",
        "initiator",
        "version",
        "sealedPromissoryNoteFileId",
        "signedPromissoryNoteFileId",
        "sourcePromissoryNoteFileId",
    ):
        report.check(f"{key} not injected", doc.get(key) != INJECTED_FIELDS.get(key))
    report.assert_all()


def assert_rejected_bad_request(ctx: PromissoryNoteContext) -> None:
    """Business FAILURE with HTTP bad request."""
    assert_business_failure(ctx, http=HTTP_BAD_REQUEST)


def assert_rejected_unprocessable(ctx: PromissoryNoteContext) -> None:
    """Business FAILURE with HTTP unprocessable."""
    assert_business_failure(ctx, http=HTTP_UNPROCESSABLE)


def _is_handled_status(code: object) -> bool:
    return isinstance(code, int) and HTTP_OK <= int(code) < HTTP_SERVER_ERROR


def _has_result_title(body: Any) -> bool:
    title = result_title(body)
    return isinstance(title, str) and bool(title.strip())


def _concurrent_summary(ctx: PromissoryNoteContext) -> dict[str, Any]:
    """Attach the batch counts + latency summary and return it for checking."""
    summary = ctx.concurrent_out.get("summary") or {}
    attach_json("concurrent summary", summary)
    return summary


def _check_no_batch_faults(report: AssertionReport, summary: dict[str, Any]) -> None:
    report.equals("server faults", actual=summary.get("server_faults"), expected=0)
    report.equals("transport faults", actual=summary.get("transport_errors"), expected=0)


def assert_concurrent_business_results(ctx: PromissoryNoteContext) -> None:
    """Every concurrent call is handled and carries a business ``result.title``."""
    summary = _concurrent_summary(ctx)
    results = ctx.concurrent_out.get("results") or []
    report = AssertionReport("concurrent business results")
    _check_no_batch_faults(report, summary)
    report.truthy("has results", bool(results))
    _check_concurrent_business_envelopes(report, results)
    report.assert_all()


def assert_concurrent_not_found(ctx: PromissoryNoteContext) -> None:
    """Every concurrent call is PROMISSORY_NOTE_NOT_FOUND."""
    summary = _concurrent_summary(ctx)
    results = ctx.concurrent_out.get("results") or []
    report = AssertionReport("concurrent not found")
    _check_no_batch_faults(report, summary)
    report.truthy("has results", bool(results))
    _check_concurrent_not_found_envelopes(report, results)
    report.assert_all()


def _check_concurrent_business_envelopes(report: AssertionReport, results: list[Any]) -> None:
    for index, item in enumerate(results):
        envelope = item if isinstance(item, dict) else {}
        report.check(
            f"[{index}] handled status",
            _is_handled_status(envelope.get("status_code")),
        )
        report.check(
            f"[{index}] result.title present",
            _has_result_title(envelope.get("body")),
        )


def _check_concurrent_not_found_envelopes(report: AssertionReport, results: list[Any]) -> None:
    for index, item in enumerate(results):
        envelope = item if isinstance(item, dict) else {}
        body = envelope.get("body")
        report.equals(
            f"[{index}] HTTP",
            actual=envelope.get("status_code"),
            expected=HTTP_UNPROCESSABLE,
        )
        report.equals(
            f"[{index}] result.title",
            actual=result_title(body),
            expected=_NOT_FOUND,
        )
        report.equals(
            f"[{index}] result.status",
            actual=result_status(body),
            expected=_NOT_FOUND_STATUS,
        )


def assert_concurrent_healthy(ctx: PromissoryNoteContext) -> None:
    """Concurrent batch: every request succeeded."""
    summary = _concurrent_summary(ctx)
    total = summary.get("total")
    report = AssertionReport("concurrent healthy")
    _check_no_batch_faults(report, summary)
    report.equals("succeeded", actual=summary.get("succeeded"), expected=total)
    report.assert_all()


def assert_concurrent_at_least_one_success(ctx: PromissoryNoteContext) -> None:
    """At least one concurrent response succeeded (UAT cancel often accepts all)."""
    summary = _concurrent_summary(ctx)
    succeeded = summary.get("succeeded")
    report = AssertionReport("at least one concurrent success")
    report.check(
        "at least one success",
        isinstance(succeeded, int) and succeeded >= 1,
    )
    report.assert_all()


def assert_exactly_one_note(flow: PromissoryNoteFlow, ctx: PromissoryNoteContext) -> None:
    """Exactly one Mongo note for tracking code."""
    report = AssertionReport("exactly one note")
    report.equals(
        "count",
        actual=flow.count_notes(ctx.tracking_code or ""),
        expected=1,
    )
    report.assert_all()


def assert_note_canceled(flow: PromissoryNoteFlow, ctx: PromissoryNoteContext) -> None:
    """Mongo status CANCELED."""
    doc = flow.get_note(ctx.tracking_code or "")
    report = AssertionReport("note canceled")
    report.equals("status", actual=int(doc.get("status", -999)), expected=STATUS_CANCELED)
    report.assert_all()


def assert_settings_detail(ctx: PromissoryNoteContext) -> None:
    """Admin settings GET has recipient routing configuration."""
    attach_api_result("settings get", ctx.last_result)
    report = AssertionReport("settings detail")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=HTTP_OK)
    body = ctx.last_result.get("body")
    report.check("ProviderSettingsBody", isinstance(body, ProviderSettingsBody))
    if isinstance(body, ProviderSettingsBody):
        detail = body.setting_detail or {}
        recipients = detail.get("recipientDtos")
        report.check("recipientDtos list", isinstance(recipients, list) and len(recipients) > 0)
        report.check(
            "activeAutoWeighting bool",
            isinstance(detail.get("activeAutoWeighting"), bool),
        )
    report.assert_all()


def assert_settings_search_recipients(ctx: PromissoryNoteContext) -> None:
    """Settings search returns SUCCESS and a non-empty recipient list."""
    attach_api_result("settings search", ctx.last_result)
    report = AssertionReport("settings search")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=HTTP_OK)
    body = ctx.last_result.get("body")
    report.check("SettingsSearchBody", isinstance(body, SettingsSearchBody))
    if isinstance(body, SettingsSearchBody):
        if body.result is not None:
            report.equals("result.title", actual=body.result.title, expected=_SUCCESS)
            report.equals("result.status", actual=body.result.status, expected=_SUCCESS_STATUS)
        recipients = body.recipient_list or []
        report.check("recipientList non-empty", len(recipients) > 0)
        first = recipients[0] if recipients else None
        report.check(
            "first recipient id",
            first is not None and isinstance(first.recipient, int),
        )
    report.assert_all()


def assert_success_rate_list(ctx: PromissoryNoteContext) -> None:
    """Success-rate statistic returns typed provider rows."""
    attach_api_result("success rate", ctx.last_result)
    report = AssertionReport("success rate list")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=HTTP_OK)
    body = ctx.last_result.get("body")
    report.check(
        "list[SuccessRateStatItem]",
        isinstance(body, list)
        and len(body) > 0
        and all(isinstance(row, SuccessRateStatItem) for row in body),
    )
    if isinstance(body, list) and body and isinstance(body[0], SuccessRateStatItem):
        report.truthy("providerName", body[0].provider_name is not None)
        report.truthy("successRate", body[0].success_rate is not None)
    report.assert_all()


def assert_success_rate_paginated(ctx: PromissoryNoteContext) -> None:
    """Paginated success-rate search has pages and rate rows."""
    attach_api_result("success rate search", ctx.last_result)
    report = AssertionReport("success rate paginated")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=HTTP_OK)
    body = ctx.last_result.get("body")
    report.check("SuccessRateSearchBody", isinstance(body, SuccessRateSearchBody))
    if isinstance(body, SuccessRateSearchBody):
        if body.result is not None:
            report.equals("result.title", actual=body.result.title, expected=_SUCCESS)
            report.equals("result.status", actual=body.result.status, expected=_SUCCESS_STATUS)
        report.check(
            "totalElements",
            isinstance(body.total_elements, int) and body.total_elements >= 0,
        )
        report.check(
            "totalPages",
            isinstance(body.total_pages, int) and body.total_pages >= 1,
        )
        rates = body.rates or []
        report.check("rates non-empty", len(rates) > 0)
        first = rates[0] if rates else None
        report.check(
            "first rate providerName",
            first is not None and first.provider_name is not None,
        )
    report.assert_all()
