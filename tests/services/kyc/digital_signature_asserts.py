"""Assertion helpers for native digital-signature BDD steps."""

from __future__ import annotations

from typing import Any, TypeVar, cast

from tests.api.kyc.digital_signatures.models import (
    GenerateSignatureBody,
    InitiateBasicBody,
)
from tests.api.kyc.models import KycResultBody
from tests.services.assert_report import (
    AssertionReport,
    assert_isinstance,
    assert_status_ok,
    assert_truthy,
    attach_api_result,
)
from tests.services.kyc.digital_signature import (
    DSP_INITIATED,
    DSP_PENDING,
    DSP_REVOKED,
    DigitalSignatureContext,
    DigitalSignatureFlow,
)

_SUCCESS_TITLE = "SUCCESS"
_INCOMPLETE_LIVENESS = "DIGITAL_SIGNATURE_INCOMPLETE_LIVENESS"
_BAD_REQUEST = "BAD_REQUEST"
_NOT_FOUND = "DIGITAL_SIGNATURE_NOT_FOUND"
_PASSWORD_MISMATCH = "DIGITAL_SIGNATURE_PASSWORD_MISMATCH"

_T = TypeVar("_T")


def require_value(label: str, value: _T | None) -> _T:
    """Require a non-empty value via AssertionReport."""
    assert_truthy(label, value)
    return cast(_T, value)


def result_title(body: Any) -> str | None:
    """Extract ``result.title`` from a typed or raw KYC body."""
    typed = (KycResultBody, GenerateSignatureBody, InitiateBasicBody)
    if isinstance(body, typed):
        result = getattr(body, "result", None)
        return result.title if result is not None else None
    if not isinstance(body, dict):
        return None
    result = body.get("result")
    if not isinstance(result, dict):
        return None
    title = result.get("title")
    return title if isinstance(title, str) else None


def store_ok_initiate(ctx: DigitalSignatureContext, result: dict[str, Any]) -> None:
    """Assert initiate success (setup) and store provider tracking on ``ctx``."""
    assert_status_ok("initiate/basic (setup)", result)
    body = result["body"]
    assert_isinstance("initiate body", body, InitiateBasicBody)
    typed = cast(InitiateBasicBody, body)
    ctx.provider_tracking_code = typed.tracking_code
    ctx.last_result = result


def store_ok_generate(ctx: DigitalSignatureContext, result: dict[str, Any]) -> None:
    """Assert generate success (setup) and store signature tracking on ``ctx``."""
    assert_status_ok("generate (setup)", result)
    body = result["body"]
    assert_isinstance("generate body", body, GenerateSignatureBody)
    typed = cast(GenerateSignatureBody, body)
    ctx.signature_tracking_code = require_value(
        "generate trackingCode", typed.tracking_code
    )
    ctx.last_result = result


def store_initiate_result(ctx: DigitalSignatureContext, result: dict[str, Any]) -> None:
    """Store initiate response; capture provider tracking when typed success."""
    ctx.last_result = result
    body = result.get("body")
    if isinstance(body, InitiateBasicBody):
        ctx.provider_tracking_code = body.tracking_code


def store_generate_result(ctx: DigitalSignatureContext, result: dict[str, Any]) -> None:
    """Store generate response; capture signature tracking when present."""
    ctx.last_result = result
    body = result.get("body")
    if isinstance(body, GenerateSignatureBody) and body.tracking_code:
        ctx.signature_tracking_code = body.tracking_code


def assert_initiate_success(ctx: DigitalSignatureContext) -> None:
    """Assert initiate/basic returned 200 + SUCCESS + trackingCode."""
    attach_api_result("initiate/basic", ctx.last_result)
    report = AssertionReport("initiate/basic success")
    status = ctx.last_result.get("status_code")
    body = ctx.last_result.get("body")
    report.equals("HTTP status", actual=status, expected=200)
    report.check("body is InitiateBasicBody", isinstance(body, InitiateBasicBody))
    if isinstance(body, InitiateBasicBody):
        report.truthy("trackingCode present", body.tracking_code)
        report.equals(
            "result.title",
            actual=body.result.title if body.result is not None else None,
            expected=_SUCCESS_TITLE,
        )
        ctx.provider_tracking_code = body.tracking_code
    report.assert_all()


def assert_generate_success(ctx: DigitalSignatureContext) -> None:
    """Assert generate returned 200 + SUCCESS + trackingCode + imageId."""
    attach_api_result("generate", ctx.last_result)
    report = AssertionReport("generate success")
    status = ctx.last_result.get("status_code")
    body = ctx.last_result.get("body")
    report.equals("HTTP status", actual=status, expected=200)
    report.check("body is GenerateSignatureBody", isinstance(body, GenerateSignatureBody))
    if isinstance(body, GenerateSignatureBody):
        report.equals(
            "result.title",
            actual=body.result.title,
            expected=_SUCCESS_TITLE,
        )
        report.truthy("trackingCode present", body.tracking_code)
        report.check(
            "imageId non-empty",
            isinstance(body.image_id, str) and bool(body.image_id.strip()),
        )
        if body.tracking_code:
            ctx.signature_tracking_code = body.tracking_code
    report.assert_all()


def assert_result_success(label: str, ctx: DigitalSignatureContext) -> None:
    """Assert HTTP 200 and ``result.title == SUCCESS``."""
    attach_api_result(label, ctx.last_result)
    report = AssertionReport(f"{label} success")
    report.equals(
        "HTTP status",
        actual=ctx.last_result.get("status_code"),
        expected=200,
    )
    report.equals(
        "result.title",
        actual=result_title(ctx.last_result.get("body")),
        expected=_SUCCESS_TITLE,
    )
    report.assert_all()


def assert_result_error(
    label: str,
    ctx: DigitalSignatureContext,
    *,
    status_code: int,
    title: str,
) -> None:
    """Assert HTTP error status and business ``result.title``."""
    attach_api_result(label, ctx.last_result)
    report = AssertionReport(label)
    report.equals(
        "HTTP status",
        actual=ctx.last_result.get("status_code"),
        expected=status_code,
    )
    report.equals(
        "result.title",
        actual=result_title(ctx.last_result.get("body")),
        expected=title,
    )
    report.assert_all()


def assert_generate_incomplete_liveness(ctx: DigitalSignatureContext) -> None:
    """Assert generate rejected for incomplete liveness."""
    assert_result_error(
        "generate (incomplete liveness)",
        ctx,
        status_code=422,
        title=_INCOMPLETE_LIVENESS,
    )


def assert_initiate_bad_request(ctx: DigitalSignatureContext) -> None:
    """Assert initiate without password returns BAD_REQUEST."""
    assert_result_error(
        "initiate/basic (no password)",
        ctx,
        status_code=422,
        title=_BAD_REQUEST,
    )


def assert_validate_not_found(ctx: DigitalSignatureContext) -> None:
    """Assert validate-password returns DIGITAL_SIGNATURE_NOT_FOUND."""
    assert_result_error(
        "validate-password (not found)",
        ctx,
        status_code=422,
        title=_NOT_FOUND,
    )


def assert_validate_password_mismatch(ctx: DigitalSignatureContext) -> None:
    """Assert validate-password returns DIGITAL_SIGNATURE_PASSWORD_MISMATCH."""
    assert_result_error(
        "validate-password (mismatch)",
        ctx,
        status_code=422,
        title=_PASSWORD_MISMATCH,
    )


def assert_dsp_pending(flow: DigitalSignatureFlow, ctx: DigitalSignatureContext) -> None:
    """Assert DSP mongo row is pending for the provider tracking code."""
    tracking = require_value("provider tracking code", ctx.provider_tracking_code)
    found = flow.wait_until_dsp_status(
        expected_status=DSP_PENDING,
        provider_tracking_code=tracking,
    )
    report = AssertionReport("provider signature pending")
    body = found.get("body") or {}
    report.equals("mongo status_code", actual=found.get("status_code"), expected=0)
    report.truthy("signature document present", body.get("status") is not None)
    report.equals("signature status", actual=body.get("status"), expected=DSP_PENDING)
    report.equals(
        "initiator",
        actual=body.get("initiator"),
        expected=ctx.secrets.requester_app_name,
    )
    report.assert_all()


def assert_dsp_initiated(
    flow: DigitalSignatureFlow, ctx: DigitalSignatureContext
) -> None:
    """Assert DSP mongo row is initiated for the signature tracking code."""
    tracking = require_value("signature tracking code", ctx.signature_tracking_code)
    found = flow.wait_until_dsp_status(
        expected_status=DSP_INITIATED,
        signature_tracking_code=tracking,
    )
    report = AssertionReport("provider signature initiated")
    body = found.get("body") or {}
    report.equals("mongo status_code", actual=found.get("status_code"), expected=0)
    report.equals(
        "owner.userId",
        actual=(body.get("owner") or {}).get("userId"),
        expected=ctx.secrets.user_id,
    )
    report.equals(
        "signature status",
        actual=body.get("status"),
        expected=DSP_INITIATED,
    )
    report.assert_all()


def assert_dsp_revoked(flow: DigitalSignatureFlow, ctx: DigitalSignatureContext) -> None:
    """Assert DSP mongo row is revoked for the signature tracking code."""
    tracking = require_value("signature tracking code", ctx.signature_tracking_code)
    found = flow.wait_until_dsp_status(
        expected_status=DSP_REVOKED,
        signature_tracking_code=tracking,
    )
    report = AssertionReport("provider signature revoked")
    body = found.get("body") or {}
    report.equals("mongo status_code", actual=found.get("status_code"), expected=0)
    report.equals(
        "owner.userId",
        actual=(body.get("owner") or {}).get("userId"),
        expected=ctx.secrets.user_id,
    )
    report.equals(
        "signature status",
        actual=body.get("status"),
        expected=DSP_REVOKED,
    )
    report.assert_all()
