"""Assertion helpers for postal-code BDD steps."""

from __future__ import annotations

from typing import Any

from tests.api.kyc.addresses.models import (
    AddressSettingDetail,
    PostalAddress,
    PostalCodeInquiryBody,
)
from tests.api.kyc.models import result_title
from tests.services.assert_report import AssertionReport
from tests.services.kyc.postal_code import PostalCodeContext, PostalCodeFlow, PostalJournal

_SUCCESS = "SUCCESS"
_NOT_FOUND = "KYC_IDENTITY_NOT_FOUND"
_INVALID_PARAMETER = "INVALID_PARAMETER"
_JIBIT = "JIBIT"


def assert_inquiry_succeeded(ctx: PostalCodeContext) -> None:
    """Assert HTTP 200, SUCCESS, and the expected provider address."""
    if ctx.provider is None:
        raise RuntimeError("postal-code provider was not selected")
    expected = ctx.secrets.jibit_address
    body = ctx.last_inquiry.get("body")
    report = AssertionReport("postal-code inquiry success")
    report.equals("HTTP status", actual=ctx.last_inquiry.get("status_code"), expected=200)
    report.equals("result.title", actual=result_title(body), expected=_SUCCESS)
    _compare_address(report, _inquiry_address(body), expected)
    report.assert_all()


def assert_inquiry_not_found(ctx: PostalCodeContext) -> None:
    """Assert the unknown postal code was not found."""
    report = AssertionReport("postal-code inquiry not found")
    report.equals("HTTP status", actual=ctx.last_inquiry.get("status_code"), expected=422)
    report.equals(
        "result.title",
        actual=result_title(ctx.last_inquiry.get("body")),
        expected=_NOT_FOUND,
    )
    report.assert_all()


def assert_inquiry_rejected(ctx: PostalCodeContext) -> None:
    """Assert the malformed postal code was rejected and no journal was written."""
    report = AssertionReport("postal-code inquiry rejected")
    report.equals("HTTP status", actual=ctx.last_inquiry.get("status_code"), expected=422)
    report.equals(
        "result.title",
        actual=result_title(ctx.last_inquiry.get("body")),
        expected=_INVALID_PARAMETER,
    )
    report.equals("journal written", actual=ctx.live_journal, expected=None)
    report.assert_all()


def assert_live_success_journal(ctx: PostalCodeContext) -> None:
    """Assert the latest journal is a live success for the pinned provider."""
    if ctx.provider is None:
        raise RuntimeError("postal-code provider was not selected")
    journal = ctx.live_journal
    expected = ctx.secrets.jibit_address
    report = AssertionReport("postal-code live success journal")
    report.truthy("journal present", journal is not None)
    if journal is not None:
        report.equals("postalCode", actual=str(journal.postal_code), expected=str(ctx.secrets.postal_code))
        report.equals("status", actual=journal.status, expected=_SUCCESS)
        report.equals(
            "provider",
            actual=journal.provider,
            expected=_JIBIT,
        )
        report.equals("resultStatus", actual=journal.result_status, expected=_SUCCESS)
        report.equals("fetchedFromCache", actual=journal.fetched_from_cache, expected=False)
        _compare_audit(report, journal, expected)
    report.assert_all()


def assert_live_not_found_journal(ctx: PostalCodeContext) -> None:
    """Assert the latest journal is a live not-found failure."""
    if ctx.provider is None:
        raise RuntimeError("postal-code provider was not selected")
    journal = ctx.live_journal
    report = AssertionReport("postal-code live not-found journal")
    report.truthy("journal present", journal is not None)
    if journal is not None:
        report.equals(
            "postalCode",
            actual=str(journal.postal_code),
            expected=str(ctx.secrets.unknown_postal_code),
        )
        report.equals("status", actual=journal.status, expected="FAILURE")
        report.equals(
            "provider",
            actual=journal.provider,
            expected=_JIBIT,
        )
        report.equals("resultStatus", actual=journal.result_status, expected=_NOT_FOUND)
        report.equals("fetchedFromCache", actual=journal.fetched_from_cache, expected=False)
    report.assert_all()


def assert_cache_miss_then_hit(ctx: PostalCodeContext) -> None:
    """Assert the first journal was live and the latest was served from cache."""
    if ctx.provider is None:
        raise RuntimeError("postal-code provider was not selected")
    first = ctx.first_journal
    cached = ctx.cached_journal
    expected = ctx.secrets.jibit_address
    report = AssertionReport("postal-code cache miss then hit")
    report.truthy("first journal present", first is not None)
    report.equals("first fetchedFromCache", actual=_cached(first), expected=False)
    report.truthy("cached journal present", cached is not None)
    report.equals("latest fetchedFromCache", actual=_cached(cached), expected=True)
    report.check(
        "cached journal is a new document",
        first is not None and cached is not None and first.id != cached.id,
        detail="first and latest journal _id must differ",
    )
    if cached is not None:
        report.equals("cached postalCode", actual=str(cached.postal_code), expected=str(ctx.secrets.postal_code))
        report.equals("cached status", actual=cached.status, expected=_SUCCESS)
        report.equals(
            "cached provider",
            actual=cached.provider,
            expected=_JIBIT,
        )
        report.equals("cached resultStatus", actual=cached.result_status, expected=_SUCCESS)
        _compare_audit(report, cached, expected)
    report.assert_all()


def assert_settings_rejected(
    ctx: PostalCodeContext, title: str, flow: PostalCodeFlow
) -> None:
    """Assert the admin weight POST was rejected and live weights did not change."""
    report = AssertionReport("address provider settings rejected")
    report.equals("HTTP status", actual=ctx.last_settings.get("status_code"), expected=422)
    report.equals(
        "result.title",
        actual=result_title(ctx.last_settings.get("body")),
        expected=title,
    )
    report.equals(
        "live provider weights unchanged",
        actual=_address_weight_rows(flow.live_address_settings()),
        expected=_address_weight_rows(flow.captured_address_settings()),
    )
    report.assert_all()


def _address_weight_rows(detail: AddressSettingDetail) -> list[tuple[int, float]]:
    return sorted((row.provider_name, float(row.weight)) for row in detail.provider_settings)


def _inquiry_address(body: Any) -> PostalAddress | None:
    if isinstance(body, PostalCodeInquiryBody):
        return body.address
    if isinstance(body, dict) and isinstance(body.get("address"), dict):
        return PostalAddress.model_validate(body["address"])
    return None


def _compare_address(
    report: AssertionReport,
    actual: PostalAddress | None,
    expected: PostalAddress,
) -> None:
    report.truthy("address present", actual is not None)
    if actual is None:
        return
    expected_dump = expected.model_dump(by_alias=True, exclude_none=True)
    actual_dump = actual.model_dump(by_alias=True, exclude_none=True)
    for key, value in expected_dump.items():
        report.equals(f"address.{key}", actual=actual_dump.get(key), expected=value)


def _compare_audit(
    report: AssertionReport,
    journal: PostalJournal,
    expected: PostalAddress,
) -> None:
    audit = journal.audit
    report.equals("audit.postalCode", actual=audit.get("postalCode"), expected=journal.postal_code)
    report.equals("audit.province", actual=audit.get("province"), expected=expected.province)
    report.equals("audit.townShip", actual=audit.get("townShip"), expected=expected.town_ship)
    report.equals("audit.district", actual=audit.get("district"), expected=expected.district)
    report.equals(
        "audit.localityName",
        actual=audit.get("localityName"),
        expected=expected.locality_name,
    )
    report.equals(
        "audit.subLocality",
        actual=audit.get("subLocality"),
        expected=expected.sub_locality,
    )
    report.equals("audit.street", actual=audit.get("street"), expected=expected.street)
    report.equals("audit.street2", actual=audit.get("street2"), expected=expected.street2)
    report.equals("audit.floor", actual=audit.get("floor"), expected=expected.floor)
    report.equals("audit.houseNo", actual=audit.get("houseNo"), expected=expected.house_no)
    report.equals(
        "audit.houseNoStr",
        actual=_whole_number_str(audit.get("houseNoStr")),
        expected=_whole_number_str(expected.house_number),
    )


def _whole_number_str(value: int | str | float | None) -> str | None:
    if value is None or value == "":
        return None
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return str(value)
    if as_float.is_integer():
        return str(int(as_float))
    return str(as_float)


def _cached(journal: PostalJournal | None) -> bool | None:
    return None if journal is None else journal.fetched_from_cache
