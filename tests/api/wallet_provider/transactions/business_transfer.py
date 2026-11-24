"""Port of src/apis/wallet-provider/transactions/post-transactions-business-transfer.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH
from tests.services.tracking import random_tracking_code


def post_transactions_business_transfer(
    client: ApiClient,
    source_business_id: str,
    source_wallet_name: str,
    destination_business_id: str,
    destination_wallet_name: str,
    amount: int,
    currency: str = "IRR",
    tracking_code: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Port of POST Transactions Business-Transfer — business wallet → business wallet."""
    path = client.ms_path("/transactions/business-transfer", MS_WALLET_PROVIDER_PATH)
    body: dict[str, Any] = {
        "trackingCode": tracking_code or random_tracking_code(18),
        "sourceBusinessId": source_business_id,
        "sourceWalletName": source_wallet_name,
        "destinationBusinessId": destination_business_id,
        "destinationWalletName": destination_wallet_name,
        "amount": amount,
        "currency": currency,
        "description": description or "",
    }
    return client.post(path, json=body)
