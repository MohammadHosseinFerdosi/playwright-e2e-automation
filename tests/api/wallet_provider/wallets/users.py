"""Port of src/apis/wallet-provider/wallets/post-wallets-users.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


def post_wallets_users(
    client: ApiClient,
    user_id: str,
    wallet_name: str,
    expiration_date: int | None = None,
) -> dict[str, Any]:
    """Port of POST Wallets Users — create a wallet for a user."""
    path = client.ms_path("/wallets/users", MS_WALLET_PROVIDER_PATH)

    body: dict[str, Any] = {
        "walletName": wallet_name,
        "userId": user_id,
    }
    if expiration_date is not None:
        body["expirationDate"] = expiration_date

    return client.post(path, json=body)
