"""POST /bills/inquiry — Platform bill-mng."""

from __future__ import annotations

from typing import Any

from tests.api.bill_mng.bills.inquiry_models import BillInquiryBody
from tests.api.bill_mng.bills.result import parse_result_body
from tests.api.bill_mng.headers import bill_request_headers
from tests.api.client import ApiClient
from tests.api.ms_paths import MS_BILL_MNG_PATH


def _parse_inquiry_body(body: Any) -> Any:
    if isinstance(body, dict) and isinstance(body.get("result"), dict):
        if "billInfos" in body or body.get("result", {}).get("title") == "SUCCESS":
            try:
                return BillInquiryBody.model_validate(body)
            except Exception:
                pass
        parsed = parse_result_body(body)
        if parsed is not None:
            return parsed
    return body


def post_bills_inquiry(
    client: ApiClient,
    user_id: str,
    *,
    bill_id: str | None = None,
    pay_id: str | None = None,
    pay_method: int | None = None,
    bill_type: int | None = None,
    inquiry_id: str | None = None,
) -> dict[str, Any]:
    """Call bill inquiry (default billId+payId, or custom payMethod=3 body).

    Returns ``{status_code, body}``. Success with bill list → ``BillInquiryBody``;
    business errors → ``BillResultBody`` when possible.
    """
    payload: dict[str, Any] = {}
    if pay_method is not None:
        payload["payMethod"] = pay_method
    if bill_type is not None:
        payload["type"] = bill_type
    if inquiry_id is not None:
        payload["inquiryId"] = inquiry_id
    if bill_id is not None:
        payload["billId"] = bill_id
    if pay_id is not None:
        payload["payId"] = pay_id

    path = client.ms_path("/bills/inquiry", MS_BILL_MNG_PATH)
    result = client.post(
        path,
        headers=bill_request_headers(user_id),
        json=payload,
    )
    return {
        "status_code": result["status_code"],
        "body": _parse_inquiry_body(result.get("body")),
    }


def get_bills_inquiry_by_cell(
    client: ApiClient,
    user_id: str,
    cell_number: str,
    *,
    operator: int = 1,
) -> dict[str, Any]:
    """GET /bills/inquiry/{cellNumber}?operator= — MCI=1, MTN=2, RIGHTEL=3."""
    path = client.ms_path(f"/bills/inquiry/{cell_number}", MS_BILL_MNG_PATH)
    result = client.get(
        path,
        headers=bill_request_headers(user_id),
        params={"operator": operator},
    )
    return {
        "status_code": result["status_code"],
        "body": _parse_inquiry_body(result.get("body")),
    }
