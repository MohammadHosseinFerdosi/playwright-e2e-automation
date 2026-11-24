"""Port of src/apis/wallet-provider/admin/admin-wallets-users.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


def get_admin_wallets_users(
    client: ApiClient,
    user_id: str,
    currency: str,
) -> dict[str, Any]:
    """Port of GET Admin Wallets Users.

    Robot returned ``response_status_code`` / ``response_body``; this port uses
    the framework-standard ``{status_code, body}`` shape.
    """
    path = client.ms_path(
        f"/admin/wallets/users/{user_id}/balances?currency={currency}",
        MS_WALLET_PROVIDER_PATH,
    )
    return client.get(path)
