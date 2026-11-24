"""Port of src/apis/wallet-provider/wallets/post-disable-wallets-users.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


def post_disable_wallets_users(
    client: ApiClient,
    user_id: str,
    wallet_name: str,
) -> dict[str, Any]:
    """Port of Post Disable User Wallet."""
    path = client.ms_path("/wallets/users/disable", MS_WALLET_PROVIDER_PATH)
    return client.post(
        path,
        json={"userId": user_id, "walletName": wallet_name},
    )
