"""Assertion helpers + destination-type constants for purchase refund inquiry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tests.api.payment.refund_inquiry import RefundInquiryBody
from tests.services.assert_report import AssertionReport, assert_isinstance

DESTINATION_TYPE_BY_NAME: dict[str, int] = {
    "wallet": 2,
    "iban": 1,
}

REFUND_LOOKUP_STEP = (
    r"^the refund inquiry (?P<inquiry_id>[A-Za-z0-9-]+) is looked up by "
    r"(?P<id_type>providerId|trackingCode)$"
)
REFUND_RETURNED_ID_STEP = (
    r"^the returned (?P<id_type>providerId|trackingCode) matches "
    r"(?P<inquiry_id>[A-Za-z0-9-]+)$"
)
REFUND_DESTINATION_TYPE_STEP = r"^the refund destination type is (?P<destination>wallet|iban)$"


def known_refund_destinations() -> list[str]:
    """Registered destination names, for the regex unit test."""
    return sorted(DESTINATION_TYPE_BY_NAME)


def _require_iban_destination(report: AssertionReport, body: RefundInquiryBody) -> None:
    report.truthy("destination present", body.destination)


_DESTINATION_EXTRAS: dict[str, Callable[[AssertionReport, RefundInquiryBody], None]] = {
    "iban": _require_iban_destination,
}


def assert_refund_destination_type(inquiry_result: dict[str, Any], destination: str) -> None:
    """Assert ``destinationType`` (and IBAN destination present when applicable)."""
    body = inquiry_result["body"]
    assert_isinstance("Refund inquiry response body", body, RefundInquiryBody)
    expected = DESTINATION_TYPE_BY_NAME[destination]
    report = AssertionReport(f"Refund destination type is {destination}").equals(
        "destination_type",
        actual=body.destination_type,
        expected=expected,
    )
    extra = _DESTINATION_EXTRAS.get(destination)
    if extra is not None:
        extra(report, body)
    report.assert_all()
