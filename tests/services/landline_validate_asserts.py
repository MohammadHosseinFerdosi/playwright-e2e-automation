"""Assertion helpers for Platform landline validate + TCI provider inquiries."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tests.api.bill_mng.bill_types import BILL_TYPE_TELEPHONE
from tests.api.bill_mng.bills.config import BillConfigBody
from tests.api.bill_mng.bills.inquiry_models import (
    TERM_TYPE_FINAL,
    TERM_TYPE_MID,
    BillInquiryBody,
)
from tests.api.bill_mng.bills.result import result_title_from_body
from tests.api.tci.models import TciProxyResponse
from tests.services.assert_report import AssertionReport, attach_api_result


def _result_message(body: Any) -> str:
    result_obj = getattr(body, "result", None)
    if result_obj is not None:
        message = getattr(result_obj, "message", None)
        if isinstance(message, str):
            return message
    if isinstance(body, dict):
        result = body.get("result")
        if isinstance(result, dict):
            message = result.get("message")
            if isinstance(message, str):
                return message
    return ""


def province_rejection_signal(body: Any) -> bool:
    """True when result title/message indicate a province not-allowed response."""
    title = (result_title_from_body(body) or "").lower()
    message = _result_message(body).lower()
    blob = f"{title} {message}"
    return "province" in blob or "not allowed" in blob


def assert_bill_config_includes_active_landline(bill_config_result: dict[str, Any]) -> None:
    """Check TELEPHONE (type 7) is present and active in bills config."""
    attach_api_result("Platform bills config", bill_config_result)
    report = AssertionReport("Bill config — TELEPHONE active")
    body = bill_config_result.get("body")
    report.check("body is BillConfigBody", isinstance(body, BillConfigBody))
    if not isinstance(body, BillConfigBody):
        report.assert_all()
        return
    telephone = [c for c in body.configs if c.type == BILL_TYPE_TELEPHONE]
    report.check(
        "TELEPHONE type=7 present",
        bool(telephone),
        detail=f"configs={len(body.configs)}",
    )
    report.check("TELEPHONE active", any(c.active for c in telephone))
    report.attach_json("BillConfigBody", body).assert_all()


def assert_landline_validate_succeeds(bill_inquiry_result: dict[str, Any]) -> None:
    """HTTP 200 + SUCCESS with non-empty billInfos."""
    attach_api_result("Platform landline validate", bill_inquiry_result)
    report = AssertionReport("Platform landline validate — SUCCESS")
    status = bill_inquiry_result["status_code"]
    body = bill_inquiry_result["body"]
    report.equals("HTTP status", actual=status, expected=200)
    report.check("body is BillInquiryBody", isinstance(body, BillInquiryBody))
    if not isinstance(body, BillInquiryBody):
        report.assert_all()
        return
    report.equals("result.title", actual=body.result.title, expected="SUCCESS")
    report.truthy("billInfos non-empty", body.bill_infos)
    report.attach_json("BillInquiryBody", body).assert_all()


def assert_landline_has_mid_and_final_terms(bill_inquiry_result: dict[str, Any]) -> None:
    """Both MID and FINAL termTypes present on a successful validate."""
    body = bill_inquiry_result["body"]
    report = AssertionReport("Platform landline validate — mid + final terms")
    report.check("body is BillInquiryBody", isinstance(body, BillInquiryBody))
    if not isinstance(body, BillInquiryBody):
        report.assert_all()
        return
    terms = body.term_types_present()
    report.check(
        "termTypes include MID (0) and FINAL (1)",
        TERM_TYPE_MID in terms and TERM_TYPE_FINAL in terms,
        detail=f"termTypes={sorted(terms)}",
    )
    report.attach_json("infos_by_term", body.infos_by_term()).assert_all()


def assert_every_landline_info_telephone_zero_fee(
    bill_inquiry_result: dict[str, Any],
) -> None:
    """Every billInfo is TELEPHONE with feeCharge 0."""
    body = bill_inquiry_result["body"]
    report = AssertionReport("Platform landline validate — billType / feeCharge")
    report.check("body is BillInquiryBody", isinstance(body, BillInquiryBody))
    if not isinstance(body, BillInquiryBody):
        report.assert_all()
        return
    report.truthy("billInfos non-empty", body.bill_infos)
    for idx, info in enumerate(body.bill_infos):
        report.equals(
            f"billInfos[{idx}].billType",
            actual=info.bill_type,
            expected=BILL_TYPE_TELEPHONE,
        )
        report.equals(
            f"billInfos[{idx}].feeCharge",
            actual=info.fee_charge,
            expected=0,
        )
    report.attach_json("BillInquiryBody", body).assert_all()


def assert_mid_final_share_bill_id_distinct_pay_ids(
    bill_inquiry_result: dict[str, Any],
) -> None:
    """MID/FINAL share billId and use distinct payIds."""
    body = bill_inquiry_result["body"]
    report = AssertionReport("Platform landline validate — billId / payId pairing")
    report.check("body is BillInquiryBody", isinstance(body, BillInquiryBody))
    if not isinstance(body, BillInquiryBody):
        report.assert_all()
        return
    by_term = body.infos_by_term()
    mid = by_term.get(TERM_TYPE_MID)
    final = by_term.get(TERM_TYPE_FINAL)
    report.check("MID term present", mid is not None)
    report.check("FINAL term present", final is not None)
    if mid is None or final is None:
        report.assert_all()
        return
    report.truthy("MID billId", mid.bill_id)
    report.truthy("FINAL billId", final.bill_id)
    report.equals(
        "shared billId across terms",
        actual=mid.bill_id,
        expected=final.bill_id,
    )
    report.truthy("MID payId", mid.pay_id)
    report.truthy("FINAL payId", final.pay_id)
    report.check(
        "distinct payId per term",
        mid.pay_id != final.pay_id,
        detail=f"mid={mid.pay_id!r} final={final.pay_id!r}",
    )
    report.attach_json("mid", mid).attach_json("final", final).assert_all()


def assert_landline_has_payable_mid(bill_inquiry_result: dict[str, Any]) -> None:
    """Payable MID term is present."""
    body = bill_inquiry_result["body"]
    report = AssertionReport("Platform landline validate — payable MID")
    report.check("body is BillInquiryBody", isinstance(body, BillInquiryBody))
    if not isinstance(body, BillInquiryBody):
        report.assert_all()
        return
    payable = body.payable_by_term()
    report.check(
        "payable MID (termType 0) present",
        TERM_TYPE_MID in payable,
        detail=f"payable_terms={sorted(payable)}",
    )
    report.attach_json("payable_by_term", payable).assert_all()


def assert_landline_has_no_payable_final(bill_inquiry_result: dict[str, Any]) -> None:
    """No payable FINAL term."""
    body = bill_inquiry_result["body"]
    report = AssertionReport("Platform landline validate — no payable FINAL")
    report.check("body is BillInquiryBody", isinstance(body, BillInquiryBody))
    if not isinstance(body, BillInquiryBody):
        report.assert_all()
        return
    payable = body.payable_by_term()
    report.check(
        "no payable FINAL (termType 1)",
        TERM_TYPE_FINAL not in payable,
        detail=f"payable_terms={sorted(payable)}",
    )
    report.attach_json("payable_by_term", payable).assert_all()


def assert_landline_validate_without_payable_bill(
    bill_inquiry_result: dict[str, Any],
) -> None:
    """No-debt path: SUCCESS with empty payable list, or mapped 422."""
    attach_api_result("Platform landline validate (no debt)", bill_inquiry_result)
    report = AssertionReport("Platform landline validate — no payable debt")
    status = bill_inquiry_result["status_code"]
    body = bill_inquiry_result["body"]
    title = result_title_from_body(body)
    if status == 200 and isinstance(body, BillInquiryBody):
        report.equals("HTTP status", actual=status, expected=200)
        report.equals("result.title", actual=body.result.title, expected="SUCCESS")
        payable = body.payable_infos()
        report.check(
            "no payable billInfos",
            not payable,
            detail=f"count={len(payable)}",
        )
        report.note(f"billInfos length={len(body.bill_infos)}")
        report.attach_json("BillInquiryBody", body).assert_all()
        return
    report.equals("HTTP status (business mapping)", actual=status, expected=422)
    report.truthy("result.title present", title)
    report.note(f"result.title={title!r}")
    report.attach_json("validate body", body).assert_all()


def assert_landline_validate_province_rejected(
    bill_inquiry_result: dict[str, Any],
) -> None:
    """Province-blocked validate returns 200/422 with a non-SUCCESS province signal."""
    attach_api_result("Platform landline validate (province)", bill_inquiry_result)
    report = AssertionReport("Platform landline validate — province not allowed")
    status = bill_inquiry_result["status_code"]
    body = bill_inquiry_result["body"]
    title = result_title_from_body(body) or ""
    province_signal = province_rejection_signal(body)
    report.check(
        "HTTP status in {200, 422}",
        status in (200, 422),
        detail=f"status={status}",
    )
    report.check(
        "province rejection signal or non-SUCCESS title",
        province_signal or title != "SUCCESS",
        detail=f"title={title!r} province_signal={province_signal}",
    )
    report.attach_json("validate body", body).assert_all()


def assert_tci_tel_status(tci_inquiry_result: dict[str, Any], tel_status: str | int) -> None:
    """TCI proxy returned the expected telStatus."""
    attach_api_result("TCI provider inquiry", tci_inquiry_result)
    report = AssertionReport("TCI inquiry — telStatus")
    body = tci_inquiry_result["body"]
    report.check("body is TciProxyResponse", isinstance(body, TciProxyResponse))
    if not isinstance(body, TciProxyResponse):
        report.assert_all()
        return
    report.equals(
        "responseStatusCode",
        actual=body.response_status_code,
        expected=200,
    )
    data = body.parse_inner().as_bill_data()
    report.equals("telStatus", actual=data.tel_status, expected=int(tel_status))
    report.note(f"serviceStatus={data.service_status!r} amount={data.amount!r}")
    report.attach_json("TciProxyResponse", body)
    report.attach_json("TciBillData", data).assert_all()


def assert_tci_authentication_failed(tci_inquiry_result: dict[str, Any]) -> None:
    """TCI proxy or inner status reports 401."""
    attach_api_result("TCI provider inquiry (bad creds)", tci_inquiry_result)
    report = AssertionReport("TCI inquiry — authentication failure")
    body = tci_inquiry_result["body"]
    report.check("body is TciProxyResponse", isinstance(body, TciProxyResponse))
    if not isinstance(body, TciProxyResponse):
        report.assert_all()
        return
    inner = body.parse_inner()
    inner_code = inner.status.code if inner.status is not None else None
    auth_failed = body.response_status_code == 401 or inner_code == 401
    report.check(
        "responseStatusCode or inner status is 401",
        auth_failed,
        detail=f"responseStatusCode={body.response_status_code!r} inner={inner_code!r}",
    )
    report.attach_json("TciProxyResponse", body).assert_all()


def assert_tci_province_not_allowed(tci_inquiry_result: dict[str, Any]) -> None:
    """TCI proxy reports province is not allowed."""
    attach_api_result("TCI provider inquiry (province)", tci_inquiry_result)
    report = AssertionReport("TCI inquiry — province not allowed")
    body = tci_inquiry_result["body"]
    report.check("body is TciProxyResponse", isinstance(body, TciProxyResponse))
    if not isinstance(body, TciProxyResponse):
        report.assert_all()
        return
    blocked = body.province_blocked()
    report.equals("responseStatusCode", actual=body.response_status_code, expected=422)
    report.check("province is not allowed (parsed message)", blocked)
    report.attach_json("TciProxyResponse", body).assert_all()


def assert_tci_leading_zero_edge(tci_inquiry_result: dict[str, Any]) -> None:
    """Leading-zero edge: province/422 or definitive telStatus in {1,2,3,4}."""
    attach_api_result("TCI provider inquiry (leading zero)", tci_inquiry_result)
    report = AssertionReport("TCI inquiry — leading zero edge")
    body = tci_inquiry_result["body"]
    report.check("body is TciProxyResponse", isinstance(body, TciProxyResponse))
    if not isinstance(body, TciProxyResponse):
        report.assert_all()
        return
    if body.province_blocked() or body.response_status_code == 422:
        report.note("province blocked / 422 — accepted for leading-zero edge")
        report.check("province path", True)
        report.attach_json("TciProxyResponse", body).assert_all()
        return
    report.equals("responseStatusCode", actual=body.response_status_code, expected=200)
    data = body.parse_inner().as_bill_data()
    report.check(
        "telStatus in {1,2,3,4}",
        data.tel_status in (1, 2, 3, 4),
        detail=f"telStatus={data.tel_status!r}",
    )
    report.attach_json("TciBillData", data).assert_all()


LANDLINE_VALIDATE_THEN_STEP = r"^the landline validate (?P<outcome>[A-Za-z0-9 -]+)$"
TCI_INQUIRY_OUTCOME_STEP = r"^the TCI inquiry (?P<outcome>(?!reports tel status )[A-Za-z0-9 -]+)$"

_LANDLINE_VALIDATE_THENS: dict[str, Callable[[dict[str, Any]], None]] = {
    "succeeds": assert_landline_validate_succeeds,
    "includes both mid and final terms": assert_landline_has_mid_and_final_terms,
    "includes a payable mid term": assert_landline_has_payable_mid,
    "does not include a payable final term": assert_landline_has_no_payable_final,
    "completes without a payable bill": assert_landline_validate_without_payable_bill,
    "is rejected for a disallowed province": assert_landline_validate_province_rejected,
}

_TCI_INQUIRY_OUTCOMES: dict[str, Callable[[dict[str, Any]], None]] = {
    "fails authentication": assert_tci_authentication_failed,
    "reports that the province is not allowed": assert_tci_province_not_allowed,
    "completes with a definitive tel status or province error": assert_tci_leading_zero_edge,
}


def known_landline_validate_outcomes() -> list[str]:
    """Registered landline-validate Then tails, for the regex unit test."""
    return sorted(_LANDLINE_VALIDATE_THENS)


def known_tci_inquiry_outcomes() -> list[str]:
    """Registered TCI Then tails, for the regex unit test."""
    return sorted(_TCI_INQUIRY_OUTCOMES)


def assert_landline_validate_outcome(bill_inquiry_result: dict[str, Any], outcome: str) -> None:
    """Dispatch one landline-validate Then from the captured Gherkin tail.

    Raises:
        KeyError: Unknown outcome — lists registered tails.
    """
    check = _LANDLINE_VALIDATE_THENS.get(outcome)
    if check is None:
        raise KeyError(
            f"No landline validate outcome for {outcome!r}; "
            f"known outcomes: {known_landline_validate_outcomes()}"
        )
    check(bill_inquiry_result)


def assert_tci_inquiry_outcome(tci_inquiry_result: dict[str, Any], outcome: str) -> None:
    """Dispatch one TCI Then from the captured Gherkin tail.

    Raises:
        KeyError: Unknown outcome — lists registered tails.
    """
    check = _TCI_INQUIRY_OUTCOMES.get(outcome)
    if check is None:
        raise KeyError(
            f"No TCI inquiry outcome for {outcome!r}; "
            f"known outcomes: {known_tci_inquiry_outcomes()}"
        )
    check(tci_inquiry_result)
