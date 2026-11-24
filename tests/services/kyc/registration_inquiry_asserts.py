"""Assertion helpers for registration-inquiry BDD steps."""

from __future__ import annotations

from typing import Any

from tests.api.kyc.models import result_title
from tests.api.kyc.registration.models import RegistrationInquiryBody
from tests.services.assert_report import AssertionReport
from tests.services.kyc.registration_inquiry import (
    RegistrationInquiryContext,
    RegistrationInquiryFlow,
    RegistrationJournal,
)
from tests.services.kyc.registration_inquiry_secrets import RegistrationPerson

_SUCCESS = "SUCCESS"
_NOT_FOUND = "KYC_IDENTITY_NOT_FOUND"
_INVALID_PARAMETER = "INVALID_PARAMETER"
_HAFEZSAMAN = "HAFEZSAMAN"
_FULL = "FULL"
_ARABIC_YE = "ي"
_PERSIAN_YE = "ی"
_ARABIC_KE = "ك"
_PERSIAN_KE = "ک"
_GENDER = {0: "FEMALE", 1: "MALE"}
_DEATH = {0: "ALIVE", 1: "DEAD"}


def _fa(text: str | None) -> str | None:
    """Normalize Arabic Yeh/Kaf so provider spelling matches secrets."""
    if text is None:
        return None
    return text.replace(_ARABIC_YE, _PERSIAN_YE).replace(_ARABIC_KE, _PERSIAN_KE)


def _token(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def assert_person_returned(ctx: RegistrationInquiryContext) -> None:
    """Assert HTTP 200 and the selected person's identity fields."""
    person = ctx.person
    if person is None:
        raise RuntimeError("registration inquiry person was not set")
    _assert_identity_http(ctx, person)


def assert_inquiry_rejected(ctx: RegistrationInquiryContext, title: str) -> None:
    """Assert the inquiry business error title and the matching journal side-effect."""
    report = AssertionReport("registration inquiry rejected")
    report.equals("HTTP status", actual=ctx.last_inquiry.get("status_code"), expected=422)
    report.equals(
        "result.title",
        actual=result_title(ctx.last_inquiry.get("body")),
        expected=title,
    )
    if title == _INVALID_PARAMETER:
        report.equals("journal written", actual=ctx.live_journal, expected=None)
    report.assert_all()
    if title == _NOT_FOUND:
        _assert_not_found_journal(ctx, title)


def assert_success_journal(ctx: RegistrationInquiryContext) -> None:
    """Assert the latest journal is a live success for the selected person."""
    _assert_success_journal(ctx, ctx.live_journal, cached=False)


def assert_cache_miss_then_hit(ctx: RegistrationInquiryContext) -> None:
    """Assert the first journal was live and the latest was served from cache."""
    first = ctx.first_journal
    cached = ctx.cached_journal
    report = AssertionReport("registration cache miss then hit")
    report.truthy("first journal present", first is not None)
    report.equals("first fetchedFromCache", actual=_cached(first), expected=False)
    report.truthy("cached journal present", cached is not None)
    report.equals("latest fetchedFromCache", actual=_cached(cached), expected=True)
    report.check(
        "cached journal is a new document",
        first is not None and cached is not None and first.id != cached.id,
        detail="first and latest journal _id must differ",
    )
    report.assert_all()
    _assert_success_journal(ctx, cached, cached=True)


def assert_settings_rejected(
    ctx: RegistrationInquiryContext, title: str, flow: RegistrationInquiryFlow
) -> None:
    """Assert the admin weight POST was rejected and live weights did not change."""
    report = AssertionReport("registration provider settings rejected")
    report.equals("HTTP status", actual=ctx.last_settings.get("status_code"), expected=422)
    report.equals(
        "result.title",
        actual=result_title(ctx.last_settings.get("body")),
        expected=title,
    )
    report.equals(
        "live provider weights unchanged",
        actual=flow.registration_weight_fingerprint(flow.live_registration_settings()),
        expected=flow.registration_weight_fingerprint(
            flow.captured_registration_settings()
        ),
    )
    report.assert_all()


def _assert_identity_http(
    ctx: RegistrationInquiryContext,
    person: RegistrationPerson,
) -> None:
    body = ctx.last_inquiry.get("body")
    parsed = _inquiry_body(body)
    report = AssertionReport("registration inquiry identity")
    report.equals("HTTP status", actual=ctx.last_inquiry.get("status_code"), expected=200)
    report.equals("result.title", actual=result_title(body), expected=_SUCCESS)
    report.truthy("identity body present", parsed is not None)
    if parsed is None:
        report.assert_all()
        return
    report.equals("firstName", actual=_fa(parsed.first_name), expected=_fa(person.first_name))
    report.equals("lastName", actual=_fa(parsed.last_name), expected=_fa(person.last_name))
    report.equals("fatherName", actual=_fa(parsed.father_name), expected=_fa(person.father_name))
    report.equals("nationalCode", actual=_token(parsed.national_code), expected=_token(person.national_code))
    report.equals("birthDate", actual=_token(parsed.birth_date), expected=_token(person.persian_birth_date))
    report.equals("shenasnameSeri", actual=_token(parsed.shenasname_seri), expected=_token(person.shenasname_seri))
    report.equals(
        "shenasnameSerial",
        actual=_token(parsed.shenasname_serial),
        expected=_token(person.shenasname_serial),
    )
    report.equals("shenasnameNo", actual=_token(parsed.shenasname_no), expected=_token(person.shenasname_no))
    report.equals("deathStatus", actual=parsed.death_status, expected=person.death_status)
    report.equals("gender", actual=parsed.gender, expected=person.gender)
    info = parsed.birth_certificate_info
    expected_info = person.birth_certificate_info
    report.truthy("birthCertificateInfo present", info is not None and expected_info is not None)
    if info is not None and expected_info is not None:
        report.equals(
            "birthCertificateSerial",
            actual=_token(info.birth_certificate_serial),
            expected=_token(expected_info.birth_certificate_serial),
        )
        report.equals(
            "birthCertificateNumber",
            actual=_token(info.birth_certificate_number),
            expected=_token(expected_info.birth_certificate_number),
        )
        report.equals(
            "birthCertificateSeries",
            actual=_token(info.birth_certificate_series),
            expected=_token(expected_info.birth_certificate_series),
        )
    report.equals("birthPlace", actual=_fa(parsed.birth_place), expected=_fa(person.birth_place))
    report.assert_all()


def _assert_not_found_journal(ctx: RegistrationInquiryContext, title: str) -> None:
    """Assert the latest journal is a live identity-not-found failure."""
    person = ctx.person
    kind = ctx.inquiry_kind
    provider = ctx.provider
    if person is None or kind is None or provider is None:
        raise RuntimeError("registration inquiry context is incomplete")
    journal = ctx.live_journal
    report = AssertionReport("registration not-found journal")
    report.truthy("journal present", journal is not None)
    if journal is None:
        report.assert_all()
        return
    report.equals(
        "nationalCode",
        actual=_token(journal.national_code),
        expected=_token(person.national_code),
    )
    report.equals("status", actual=journal.status, expected="FAILURE")
    report.equals("provider", actual=journal.provider, expected=_HAFEZSAMAN)
    report.equals("type", actual=journal.type, expected=_FULL)
    report.equals("resultStatus", actual=journal.result_status, expected=title)
    report.equals("fetchedFromCache", actual=journal.fetched_from_cache, expected=False)
    report.assert_all()


def _assert_success_journal(
    ctx: RegistrationInquiryContext,
    journal: RegistrationJournal | None,
    *,
    cached: bool,
) -> None:
    person = ctx.person
    kind = ctx.inquiry_kind
    provider = ctx.provider
    if person is None or kind is None or provider is None:
        raise RuntimeError("registration inquiry context is incomplete")
    report = AssertionReport("registration journal")
    report.truthy("journal present", journal is not None)
    if journal is None:
        report.assert_all()
        return
    report.equals("nationalCode", actual=_token(journal.national_code), expected=_token(person.national_code))
    report.equals("status", actual=journal.status, expected=_SUCCESS)
    report.equals("provider", actual=journal.provider, expected=_HAFEZSAMAN)
    report.equals("type", actual=journal.type, expected=_FULL)
    report.equals("glRelay", actual=journal.gl_relay, expected=True)
    report.equals("strongValidation", actual=journal.strong_validation, expected=not cached)
    report.equals("resultStatus", actual=journal.result_status, expected=_SUCCESS)
    report.equals("fetchedFromCache", actual=journal.fetched_from_cache, expected=cached)
    audit = journal.audit
    report.equals("audit.nationalCode", actual=_token(audit.get("nationalCode")), expected=_token(person.national_code))
    report.equals("audit.birthDate", actual=_token(audit.get("birthDate")), expected=_token(person.persian_birth_date))
    report.equals("audit.firstName", actual=_fa(_as_str(audit.get("firstName"))), expected=_fa(person.first_name))
    report.equals("audit.lastName", actual=_fa(_as_str(audit.get("lastName"))), expected=_fa(person.last_name))
    report.equals("audit.fatherName", actual=_fa(_as_str(audit.get("fatherName"))), expected=_fa(person.father_name))
    report.equals("audit.deathStatus", actual=audit.get("deathStatus"), expected=_DEATH.get(person.death_status or 0))
    report.equals("audit.gender", actual=audit.get("gender"), expected=_GENDER.get(person.gender or 0))
    info = person.birth_certificate_info
    if info is not None:
        report.equals(
            "audit.birthCertificateNumber",
            actual=_token(audit.get("birthCertificateNumber")),
            expected=_token(info.birth_certificate_number),
        )
        report.equals(
            "audit.birthCertificateSeries",
            actual=_token(audit.get("birthCertificateSeries")),
            expected=_token(info.birth_certificate_series),
        )
        report.equals(
            "audit.birthCertificateSerial",
            actual=_token(audit.get("birthCertificateSerial")),
            expected=_token(info.birth_certificate_serial),
        )
    report.equals(
        "audit.birthPlace",
        actual=_fa(_as_str(audit.get("birthPlace"))),
        expected=_fa(person.birth_place),
    )
    report.assert_all()


def _inquiry_body(body: Any) -> RegistrationInquiryBody | None:
    if isinstance(body, RegistrationInquiryBody):
        return body
    if isinstance(body, dict) and "firstName" in body:
        return RegistrationInquiryBody.model_validate(body)
    return None


def _cached(journal: RegistrationJournal | None) -> bool | None:
    return None if journal is None else journal.fetched_from_cache


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
