"""GET/PUT ``/admin/bills/configs`` — Platform bill-mng admin inquiry weights."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.bill_mng.bill_types import BillType, UtilityBillType, utility_bill_type_for
from tests.api.bill_mng.bills.result import BillResult, parse_result_body
from tests.api.client import ApiClient
from tests.api.ms_paths import MS_BILL_MNG_PATH


class InquiryDistribution(BaseModel):
    """One provider row of a bill-type inquiry distribution (weight per provider)."""

    model_config = ConfigDict(extra="ignore")

    provider: int
    weight: float


class AdminBillConfigItem(BaseModel):
    """One per-type entry from GET ``/admin/bills/configs``."""

    model_config = ConfigDict(extra="ignore")

    type: int
    inquiry_distributions: list[InquiryDistribution] = Field(
        default_factory=list, alias="inquiryDistributions"
    )


class AdminBillConfigsBody(BaseModel):
    """GET ``/admin/bills/configs`` response — per-type configs + totals."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: BillResult
    configs: list[AdminBillConfigItem] = Field(default_factory=list)
    total_inquiry_distributions: list[InquiryDistribution] = Field(
        default_factory=list, alias="totalInquiryDistributions"
    )

    def config_for(self, bill_type: BillType) -> AdminBillConfigItem:
        """Return the config for ``bill_type`` (raises ``LookupError`` if absent)."""
        api_type = int(bill_type)
        for item in self.configs:
            if item.type == api_type:
                return item
        raise LookupError(f"No admin bill config for type={api_type}")


def _admin_headers(user_id: str) -> dict[str, str]:
    return {
        "User-Id": user_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_admin_bills_configs(client: ApiClient, user_id: str) -> dict[str, Any]:
    """GET /admin/bills/configs. Returns ``{status_code, body}``."""
    path = client.ms_path("/admin/bills/configs", MS_BILL_MNG_PATH)
    result = client.get(path, headers=_admin_headers(user_id))
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "configs" in body:
        return {
            "status_code": result["status_code"],
            "body": AdminBillConfigsBody.model_validate(body),
        }
    parsed = parse_result_body(body)
    if parsed is not None:
        return {"status_code": result["status_code"], "body": parsed}
    return result


def put_admin_bills_config(
    client: ApiClient,
    user_id: str,
    utility_type: UtilityBillType | str,
    *,
    inquiry_distributions: Sequence[InquiryDistribution | dict[str, Any]],
    active: bool | None = None,
    disable_message: str | None = None,
) -> dict[str, Any]:
    """PUT /admin/bills/configs/{utilityType}. Returns ``{status_code, body}``."""
    code = utility_type.value if isinstance(utility_type, UtilityBillType) else str(utility_type)
    path = client.ms_path(f"/admin/bills/configs/{code}", MS_BILL_MNG_PATH)
    payload: dict[str, Any] = {
        "inquiryDistributions": [
            d.model_dump() if isinstance(d, InquiryDistribution) else d
            for d in inquiry_distributions
        ]
    }
    if active is not None:
        payload["active"] = active
    if disable_message is not None:
        payload["disableMessage"] = disable_message

    result = client.put(path, headers=_admin_headers(user_id), json=payload)
    body = result.get("body")
    parsed = parse_result_body(body)
    if parsed is not None:
        return {"status_code": result["status_code"], "body": parsed}
    return result


def put_admin_bills_config_for_api_type(
    client: ApiClient,
    user_id: str,
    bill_type: BillType,
    *,
    inquiry_distributions: Sequence[InquiryDistribution | dict[str, Any]],
) -> dict[str, Any]:
    """PUT using API ``BillType`` mapped to ``UtilityBillType`` path code."""
    return put_admin_bills_config(
        client,
        user_id,
        utility_bill_type_for(bill_type),
        inquiry_distributions=inquiry_distributions,
    )
