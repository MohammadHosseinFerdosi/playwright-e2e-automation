"""GET /bills/config — Platform bill-mng."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.bill_mng.bills.result import BillResult, parse_result_body
from tests.api.bill_mng.headers import bill_request_headers
from tests.api.client import ApiClient
from tests.api.ms_paths import MS_BILL_MNG_PATH


class BillConfigItem(BaseModel):
    """One bill type entry from GET /bills/config."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: int
    title: str | None = None
    active: bool = False
    pay_methods: list[int] = Field(default_factory=list, alias="payMethods")
    inquiry_methods: list[int] = Field(default_factory=list, alias="inquiryMethods")


class BillConfigBody(BaseModel):
    """Success body for GET /bills/config."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: BillResult
    configs: list[BillConfigItem] = Field(default_factory=list)


def get_bills_config(
    client: ApiClient,
    user_id: str,
    *,
    is_mobile_bill: bool | None = None,
) -> dict[str, Any]:
    """Call bill configuration. Returns ``{status_code, body}``."""
    path = client.ms_path("/bills/config", MS_BILL_MNG_PATH)
    params: dict[str, Any] = {}
    if is_mobile_bill is not None:
        params["isMobileBill"] = is_mobile_bill

    result = client.get(
        path,
        headers=bill_request_headers(user_id),
        params=params or None,
    )
    body = result.get("body")
    if (
        result["status_code"] == 200
        and isinstance(body, dict)
        and isinstance(body.get("configs"), list)
    ):
        return {
            "status_code": result["status_code"],
            "body": BillConfigBody.model_validate(body),
        }
    parsed = parse_result_body(body)
    if parsed is not None:
        return {"status_code": result["status_code"], "body": parsed}
    return result
