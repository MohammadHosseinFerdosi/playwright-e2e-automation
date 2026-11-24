"""Assertion helpers for Shahkar BDD steps."""

from __future__ import annotations

from typing import Any

from tests.api.kyc.models import KycResultBody
from tests.api.kyc.shahkar.models import CellNumberInquiryBody
from tests.services.assert_report import AssertionReport
from tests.services.kyc.shahkar import ShahkarContext, ShahkarJournal

_SUCCESS_TITLE = "SUCCESS"
_INVALID_PARAMETER = "INVALID_PARAMETER"


def _result_title(body: Any) -> str | None:
    if isinstance(body, (KycResultBody, CellNumberInquiryBody)):
        result = body.result
        return result.title if result is not None else None
    if not isinstance(body, dict):
        return None
    result = body.get("result")
    if isinstance(result, dict):
        title = result.get("title")
        return title if isinstance(title, str) else None
    return None


def _inquiry_verified(body: Any) -> bool | None:
    if isinstance(body, CellNumberInquiryBody):
        return body.verified
    if isinstance(body, dict):
        flag = body.get("verified")
        return flag if isinstance(flag, bool) else None
    return None


def assert_inquiry_verified(ctx: ShahkarContext) -> None:
    """Assert HTTP 200, SUCCESS, and ``verified`` true."""
    _assert_inquiry_flag(ctx, expected=True)


def assert_inquiry_unverified(ctx: ShahkarContext) -> None:
    """Assert HTTP 200, SUCCESS, and ``verified`` false."""
    _assert_inquiry_flag(ctx, expected=False)


def _assert_inquiry_flag(ctx: ShahkarContext, *, expected: bool) -> None:
    result = ctx.last_inquiry
    report = AssertionReport("Shahkar inquiry outcome")
    report.equals("HTTP status", actual=result.get("status_code"), expected=200)
    report.equals(
        "result.title",
        actual=_result_title(result.get("body")),
        expected=_SUCCESS_TITLE,
    )
    report.equals(
        "verified",
        actual=_inquiry_verified(result.get("body")),
        expected=expected,
    )
    report.assert_all()


def assert_inquiry_rejected(ctx: ShahkarContext) -> None:
    """Assert the inquiry was rejected as an invalid parameter."""
    result = ctx.last_inquiry
    report = AssertionReport("Shahkar inquiry rejected")
    report.equals("HTTP status", actual=result.get("status_code"), expected=422)
    report.equals(
        "result.title",
        actual=_result_title(result.get("body")),
        expected=_INVALID_PARAMETER,
    )
    report.assert_all()


def assert_cache_miss_then_hit(ctx: ShahkarContext) -> None:
    """Assert the first journal was live and the latest was served from cache."""
    first = ctx.first_journal
    cached = ctx.cached_journal
    report = AssertionReport("Shahkar cache miss then hit")
    report.truthy("first journal present", first is not None)
    report.equals(
        "first fetchedFromCache",
        actual=_journal_cached(first),
        expected=False,
    )
    report.truthy("cached journal present", cached is not None)
    report.equals(
        "latest fetchedFromCache",
        actual=_journal_cached(cached),
        expected=True,
    )
    report.check(
        "cached journal is a new document",
        first is not None and cached is not None and first.id != cached.id,
        detail="first and latest journal _id must differ",
    )
    report.assert_all()


def _journal_cached(journal: ShahkarJournal | None) -> bool | None:
    return None if journal is None else journal.fetched_from_cache
