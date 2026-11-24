"""Port of src/apis/purchase-mng/refund/post-purchase-refund.resource."""

from typing import Any

from tests.api.client import ApiClient, ApiSide
from tests.api.ms_paths import MS_PURCHASE_PATH


def post_purchases_refund(
    client: ApiClient,
    *,
    amount: int | None = None,
    business_id: str | None = None,
    user_id: str | None = None,
    sale_tracking_code: str | None = None,
    provider_id: str | None = None,
    pan: str | None = None,
    iban: str | None = None,
    description: str | None = None,
    customer_name: str | None = None,
    cell_number: str | None = None,
    sale_order_id: str | None = None,
    restrictions: Any = None,
    refund_type: str | None = None,
) -> dict[str, Any]:
    """Port of Post Purchase Refund.

    Microservice path is ``MS_PURCHASE_PATH`` + ``/purchases/refunds``.
    Other sides use ``/refunds``.
    """
    if client.side is ApiSide.MICROSERVICE:
        path = client.ms_path("/purchases/refunds", MS_PURCHASE_PATH)
    else:
        path = "/refunds"

    headers: dict[str, str] = {}
    if client.side is ApiSide.MICROSERVICE and business_id:
        headers["User-Id"] = business_id

    body: dict[str, Any] = {
        "amount": amount,
        "userId": user_id,
        "providerId": provider_id,
        "saleTrackingCode": sale_tracking_code,
        "pan": pan,
        "iban": iban,
        "description": description,
        "customerName": customer_name,
        "cellNumber": cell_number,
        "additional_info": {
            "saleOrderId": sale_order_id,
            "restrictions": restrictions,
        },
    }
    params = {"type": refund_type} if refund_type is not None else None
    return client.post(path, headers=headers, params=params, json=body)
