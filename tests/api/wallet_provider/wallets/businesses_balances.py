"""Port of src/apis/wallet-provider/wallets/get-wallets-businesses-balances.resource."""

from typing import Any

from tests.api.client import ApiClient, ApiSide
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


def get_wallets_businesses_balances(
    client: ApiClient,
    business_id: str,
) -> dict[str, Any]:
    """Port of GET Wallets Businesses Balances — all wallets for one business."""
    path = "/wallets/businesses/balances"
    headers: dict[str, str] = {}
    if client.side is ApiSide.MICROSERVICE:
        path = client.ms_path(path, MS_WALLET_PROVIDER_PATH)
        headers["User-Id"] = business_id
    return client.get(path, headers=headers)
