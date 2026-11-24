"""Port of src/apis/purchase-mng/post-purchases-verify.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_PURCHASE_PATH


def post_purchases_verify(
    client: ApiClient,
    tracking_code: str,
    user_id: str = "",
) -> dict[str, Any]:
    """Port of POST Purchases Verify."""
    path = client.ms_path(f"/purchases/verify/{tracking_code}", MS_PURCHASE_PATH)
    return client.post(path, headers={"User-Id": user_id})
