"""Port of src/apis/wallet-provider/admin/admin-wallets-businesses.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


def post_admin_wallets_businesses(
    client: ApiClient,
    business_id: str,
    wallet_name: str,
    currency: str = "IRR",
) -> dict[str, Any]:
    """Port of POST Admin Wallets Businesses — create a wallet on a business.

    Robot returned a bare ``True`` on success; this port keeps the framework
    ``{status_code, body}`` envelope so callers stay consistent.
    """
    path = client.ms_path("/admin/wallets/businesses", MS_WALLET_PROVIDER_PATH)
    return client.post(
        path,
        headers={"Agent": "CONSOLE"},
        json={
            "businessId": business_id,
            "walletName": wallet_name,
            "currency": currency,
        },
    )
