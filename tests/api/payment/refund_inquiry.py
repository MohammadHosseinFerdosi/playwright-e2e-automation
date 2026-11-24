"""Port of src/apis/purchase-mng/refund/get-purchases-refunds-inquiry-id.resource."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.client import ApiClient, ApiSide
from tests.api.ms_paths import MS_PURCHASE_PATH


class RefundInquiryResult(BaseModel):
    """Nested ``result`` object on a refund inquiry response."""

    model_config = ConfigDict(extra="ignore")

    status: int


class RefundInquiryBody(BaseModel):
    """Success / structured failure body for refund inquiry."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    result: RefundInquiryResult
    status: int
    result_code: int = Field(alias="resultCode")
    destination_type: int | None = Field(default=None, alias="destinationType")
    destination: str | None = None


def get_purchases_refunds_inquiry_id(
    client: ApiClient,
    inquiry_id: str,
    user_id: str = "",
) -> dict[str, Any]:
    """Port of GET Purchases Refunds Inquiry Id.

    NOTE: for the microservice side, `user_id` must be filled — it's always
    sent as the `User-Id` header (other sides derive the caller from the
    access token itself, but the microservice route needs it explicit).
    """
    if client.side is ApiSide.MICROSERVICE:
        path = client.ms_path(f"/purchases/refunds/{inquiry_id}", MS_PURCHASE_PATH)
    else:
        path = f"refunds/{inquiry_id}?type=0"

    result = client.get(path, headers={"User-Id": user_id})
    body = result.get("body")
    if isinstance(body, dict) and "result" in body and "resultCode" in body:
        try:
            result = {
                "status_code": result["status_code"],
                "body": RefundInquiryBody.model_validate(body),
            }
        except ValidationError:
            # Keep raw body when shape does not match (unexpected errors).
            pass
    return result
