"""Port of src/apis/purchase-mng/moke-pay/mock-ipg-result.resource."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_MOCK_PATH


class IpgMockCallbackBody(BaseModel):
    """Parsed fields from the mock IPG HTML/form callback response."""

    model_config = ConfigDict(extra="ignore")

    rrn: str
    sale_order_id: str = Field(alias="saleOrderId")
    raw: str = ""


def post_ipg_result(
    client: ApiClient,
    token: CHANGE_ME
    status: int,
) -> dict[str, Any]:
    """Port of POST IPG Result — simulate PSP callback into Platform mock.

    Robot returned ``(rrn, sale_order_id)``; this port keeps
    ``{status_code, body}`` and puts parsed fields on ``body``.
    """
    path = client.ms_path("/ipg/result", MS_MOCK_PATH)
    result = client.post(
        path,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"token": token, "status": status},
    )
    raw = ""
    body = result.get("body")
    if isinstance(body, dict) and "_raw" in body:
        raw = str(body["_raw"])
    elif isinstance(body, str):
        raw = body
    else:
        # form endpoints sometimes still parse as non-JSON; fall back via status
        raw = str(body) if body is not None else ""

    if result["status_code"] == 200 and raw:
        rrn_match = re.search(r'name="rrn" value="(.*?)"', raw)
        sale_match = re.search(r'name="SaleOrderId" value="(.*?)"', raw)
        if rrn_match and sale_match:
            return {
                "status_code": result["status_code"],
                "body": IpgMockCallbackBody(
                    rrn=rrn_match.group(1),
                    saleOrderId=sale_match.group(1),
                    raw=raw,
                ),
            }
    return result
