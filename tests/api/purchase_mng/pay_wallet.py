"""Port of src/apis/purchase-mng/post-purchases-pay-wallet.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_PURCHASE_PATH


def post_purchases_pay_wallet(
    client: ApiClient,
    destination_type: str,
    ticket: str,
    platform_version: str = "",
    x_forwarded_for: str = "",
) -> dict[str, Any]:
    """Port of POST Purchase Pay Wallet."""
    path = client.ms_path("/purchases/pay/wallet", MS_PURCHASE_PATH)
    headers: dict[str, str] = {}
    if platform_version:
        headers["Platform-Version"] = platform_version
    if x_forwarded_for:
        headers["X-Forwarded-For"] = x_forwarded_for
    return client.post(
        path,
        headers=headers,
        json={"type": destination_type, "ticket": ticket},
    )
