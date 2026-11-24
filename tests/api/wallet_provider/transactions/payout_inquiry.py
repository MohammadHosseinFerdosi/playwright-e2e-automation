"""Port of src/apis/wallet-provider/transactions/get-transactions-payout.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


def get_transactions_payout(
    client: ApiClient,
    tracking_code: str,
) -> dict[str, Any]:
    """Port of GET Transactions Payout — inquire by tracking code."""
    path = client.ms_path(
        f"/transactions/payout/{tracking_code}",
        MS_WALLET_PROVIDER_PATH,
    )
    return client.get(path)
