"""Port of src/apis/wallet-provider/transactions/get-transactions-spend.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


def get_transactions_spend(
    client: ApiClient,
    tracking_code: str,
) -> dict[str, Any]:
    """Port of GET Transactions Spend — inquire by tracking code."""
    path = client.ms_path(
        f"/transactions/spend/{tracking_code}",
        MS_WALLET_PROVIDER_PATH,
    )
    return client.get(path)
