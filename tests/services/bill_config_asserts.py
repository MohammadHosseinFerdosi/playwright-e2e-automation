"""Assertion helpers for Platform bills config + business-rejection envelopes."""

from __future__ import annotations

from typing import Any

from tests.api.bill_mng.bills.config import BillConfigBody
from tests.api.bill_mng.bills.result import BillResultBody, result_title_from_body
from tests.services.assert_report import AssertionReport, attach_api_result


def assert_bill_configuration_succeeds(bill_config_result: dict[str, Any]) -> None:
    """HTTP 200 + SUCCESS BillConfigBody."""
    report = AssertionReport("Bill configuration request succeeds")
    status = bill_config_result["status_code"]
    body = bill_config_result["body"]
    report.equals("HTTP status", actual=status, expected=200)
    report.check("body is BillConfigBody", isinstance(body, BillConfigBody))
    if not isinstance(body, BillConfigBody):
        report.assert_all()
        return
    report.equals("result.title", actual=body.result.title, expected="SUCCESS")
    report.attach_json("BillConfigBody", body).assert_all()


def assert_bill_configuration_lists_active_types(
    bill_config_result: dict[str, Any],
) -> None:
    """Config list is non-empty with at least one active type and int type codes."""
    body = bill_config_result["body"]
    report = AssertionReport("Bill configuration lists active bill types")
    report.check("body is BillConfigBody", isinstance(body, BillConfigBody))
    if not isinstance(body, BillConfigBody):
        report.assert_all()
        return
    report.truthy("at least one bill config entry", body.configs)
    active = [c for c in body.configs if c.active]
    report.truthy("at least one active bill type", active)
    for item in body.configs:
        report.check(
            f"config type is int (type={item.type!r})",
            isinstance(item.type, int),
            detail=repr(item),
        )
    report.attach_json("BillConfigBody", body).assert_all()


def assert_bill_business_rejection(result: dict[str, Any], expected_title: str) -> None:
    """HTTP 422 with the expected ``result.title`` business error."""
    attach_api_result("Bill business rejection", result)
    report = AssertionReport("Bill business rejection")
    status = result["status_code"]
    body = result.get("body")
    report.equals("HTTP status", actual=status, expected=422)
    envelope_ok = (
        isinstance(body, BillResultBody)
        or (isinstance(body, dict) and "result" in body)
        or (getattr(body, "result", None) is not None)
    )
    report.check("result envelope present", envelope_ok)
    actual = result_title_from_body(body)
    report.equals("result.title", actual=actual, expected=expected_title)
    report.attach_json("response body", body).assert_all()
