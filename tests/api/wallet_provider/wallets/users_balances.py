"""Port of src/apis/wallet-provider/wallets/get-wallets-users-balances.resource."""

from typing import Any

from tests.api.client import ApiClient, ApiSide
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


def get_wallets_users_balances(
    client: ApiClient,
    user_id: str,
) -> dict[str, Any]:
    """Port of GET Wallets Users Balances — all wallets for one user."""
    path = "/wallets/users/balances"
    headers: dict[str, str] = {}
    if client.side is ApiSide.MICROSERVICE:
        path = client.ms_path(path, MS_WALLET_PROVIDER_PATH)
        headers["User-Id"] = user_id
    return client.get(path, headers=headers)
