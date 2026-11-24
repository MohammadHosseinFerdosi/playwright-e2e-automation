"""Step definitions for tests/bdd/features/payment/refund_inquiry.feature."""

from typing import Any

from pytest_bdd import parsers, scenarios, then, when

from tests.api.client import ApiClient, ApiSide
from tests.api.payment.refund_inquiry import (
    RefundInquiryBody,
    get_purchases_refunds_inquiry_id,
)
from tests.config.settings import Settings
from tests.services.assert_report import AssertionReport, assert_isinstance, assert_status_ok
from tests.services.refund_inquiry_asserts import assert_refund_destination_type

scenarios("../features/payment/refund_inquiry.feature")


@when(
    parsers.re(
        r"^the refund inquiry (?P<inquiry_id>[A-Za-z0-9-]+) is looked up by "
        r"(?P<id_type>providerId|trackingCode)$"
    ),
    target_fixture="inquiry_result",
)
def _(settings: Settings, access_token: str, inquiry_id: str, id_type: str) -> dict[str, Any]:
    # Robot hardcodes ?type=0; id_type is asserted on the response, not the query.
    del id_type
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return get_purchases_refunds_inquiry_id(client, inquiry_id, settings.platform_username)


@then("the refund inquiry request succeeds")
def _(inquiry_result: dict[str, Any]) -> None:
    assert_status_ok("Refund inquiry request", inquiry_result)
    body = inquiry_result["body"]
    assert_isinstance("Refund inquiry response body", body, RefundInquiryBody)
    AssertionReport("Refund inquiry succeeded").equals(
        "result.status", actual=body.result.status, expected=0
    ).equals("status", actual=body.status, expected=0).equals(
        "result_code", actual=body.result_code, expected=0
    ).assert_all()


@then(
    parsers.re(
        r"^the returned (?P<id_type>providerId|trackingCode) matches "
        r"(?P<inquiry_id>[A-Za-z0-9-]+)$"
    )
)
def _(inquiry_result: dict[str, Any], id_type: str, inquiry_id: str) -> None:
    body = inquiry_result["body"]
    assert_isinstance("Refund inquiry response body", body, RefundInquiryBody)
    payload = body.model_dump(by_alias=True)
    AssertionReport(f"Returned {id_type} matches request").equals(
        id_type, actual=payload.get(id_type), expected=inquiry_id
    ).assert_all()


@then(parsers.re(r"^the refund destination type is (?P<destination>wallet|iban)$"))
def _(inquiry_result: dict[str, Any], destination: str) -> None:
    assert_refund_destination_type(inquiry_result, destination)


@then("the refund inquiry request is rejected as invalid")
def _(inquiry_result: dict[str, Any]) -> None:
    assert_status_ok("Refund inquiry rejected as invalid", inquiry_result, expected=422)
    body = inquiry_result["body"]
    assert_isinstance("Refund inquiry response body", body, RefundInquiryBody)
    AssertionReport("Refund inquiry rejected as invalid").equals(
        "result.status", actual=body.result.status, expected=1121
    ).assert_all()
