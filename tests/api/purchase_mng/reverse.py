"""Port of src/apis/purchase-mng/post-purchases-reverse.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_PURCHASE_PATH


def post_purchases_reverse(
    client: ApiClient,
    tracking_code: str,
    provider_id: str,
    user_id: str = "",
) -> dict[str, Any]:
    """Port of POST Purchases Reverse."""
    path = client.ms_path("/purchases/reverse", MS_PURCHASE_PATH)
    return client.post(
        path,
        headers={"User-Id": user_id},
        json={
            "providerId": provider_id,
            "purchaseTrackingCode": tracking_code,
        },
    )
