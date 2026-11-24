"""POST /bills/validate — Platform bill-mng (deprecated alias of /bills/inquiry).

UI landline inquiry calls this path; same handler as ``/bills/inquiry``.
"""

from __future__ import annotations

from typing import Any

from tests.api.bill_mng.bills.inquiry import _parse_inquiry_body
from tests.api.bill_mng.headers import bill_request_headers
from tests.api.client import ApiClient
from tests.api.ms_paths import MS_BILL_MNG_PATH


def post_bills_validate(
    client: ApiClient,
    user_id: str,
    *,
    bill_id: str | None = None,
    pay_id: str | None = None,
    pay_method: int | None = None,
    bill_type: int | None = None,
    inquiry_id: str | None = None,
) -> dict[str, Any]:
    """Call bill validate. Returns ``{status_code, body}``.

    Success with bill list → ``BillInquiryBody``; business errors → result envelope
    when possible.
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

    path = client.ms_path("/bills/validate", MS_BILL_MNG_PATH)
    result = client.post(
        path,
        headers=bill_request_headers(user_id),
        json=payload,
    )
    return {
        "status_code": result["status_code"],
        "body": _parse_inquiry_body(result.get("body")),
    }
