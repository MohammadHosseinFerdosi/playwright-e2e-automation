"""POST /bills/init — Platform bill-mng payment ticket."""

from __future__ import annotations

from typing import Any

from tests.api.bill_mng.bills.result import parse_result_body
from tests.api.bill_mng.headers import bill_request_headers
from tests.api.client import ApiClient
from tests.api.ms_paths import MS_BILL_MNG_PATH

DEFAULT_CALLBACK_URL = "https://example.com/web/test"


def post_bills_init(
    client: ApiClient,
    user_id: str,
    *,
    bill_id: str,
    pay_id: str,
    callback_url: str = DEFAULT_CALLBACK_URL,
    redirect_url: str | None = None,
) -> dict[str, Any]:
    """Create a bill payment ticket. Returns ``{status_code, body}``."""
    payload: dict[str, Any] = {
        "billId": bill_id,
        "payId": pay_id,
        "callbackUrl": callback_url,
    }
    if redirect_url is not None:
        payload["redirectUrl"] = redirect_url

    path = client.ms_path("/bills/init", MS_BILL_MNG_PATH)
    result = client.post(
        path,
        headers=bill_request_headers(user_id),
        json=payload,
    )
    parsed = parse_result_body(result.get("body"))
    if parsed is not None:
        return {"status_code": result["status_code"], "body": parsed}
    return result
