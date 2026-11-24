"""Port of src/apis/wallet-provider/transactions/post-transactions-spend-verify.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


def post_transactions_spend_verify(
    client: ApiClient,
    tracking_code: str,
    confirmation_code: str,
) -> dict[str, Any]:
    """Port of POST Transactions Spend Verify."""
    path = client.ms_path("/transactions/spend/verify", MS_WALLET_PROVIDER_PATH)
    return client.post(
        path,
        json={
            "trackingCode": tracking_code,
            "confirmationCode": confirmation_code,
        },
    )
