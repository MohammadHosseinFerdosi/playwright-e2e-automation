"""Port of src/apis/wallet-provider/transactions/post-transactions-collect.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH
from tests.services.tracking import random_tracking_code


def post_transactions_collect(
    client: ApiClient,
    source_user_id: str,
    source_user_wallet_name: str,
    destination_business_id: str,
    destination_business_wallet_name: str,
    currency: str = "IRR",
    tracking_code: str | None = None,
) -> dict[str, Any]:
    """Port of POST Transactions Collect — sweep a user wallet to a business wallet.

    Robot note: source user wallet should be expired for this call to succeed.
    """
    path = client.ms_path("/transactions/collect", MS_WALLET_PROVIDER_PATH)
    body = {
        "sourceUserId": source_user_id,
        "sourceWalletName": source_user_wallet_name,
        "destinationBusinessId": destination_business_id,
        "destinationWalletName": destination_business_wallet_name,
        "trackingCode": tracking_code or random_tracking_code(25),
        "currency": currency,
    }
    return client.post(path, json=body)
