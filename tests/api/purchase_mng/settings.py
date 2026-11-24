"""Port of src/apis/purchase-mng/setting/post-purchase-setting.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_PURCHASE_PATH


def post_admin_purchases_settings(
    client: ApiClient,
    business_id: str,
    active_gateways: list[Any],
) -> dict[str, Any]:
    """Port of Post admin Purchase setting."""
    path = client.ms_path(
        f"/admin/purchases/settings/{business_id}",
        MS_PURCHASE_PATH,
    )
    return client.post(path, json={"activeGateways": active_gateways})
