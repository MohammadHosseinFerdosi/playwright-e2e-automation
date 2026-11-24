"""Port of src/apis/wallet-provider/transactions/post-transactions-receive.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH
from tests.services.tracking import random_tracking_code


def post_transactions_receive(
    client: ApiClient,
    source_user_id: str,
    source_wallet_name: str,
    destination_business_id: str,
    destination_wallet_name: str,
    amount: int,
    cashoutable_amount: int,
    currency: str = "IRR",
    tracking_code: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Port of Post Receive Wallet — user wallet → business wallet."""
    path = client.ms_path("/transactions/receive", MS_WALLET_PROVIDER_PATH)
    body: dict[str, Any] = {
        "trackingCode": tracking_code or random_tracking_code(25),
        "sourceUserId": source_user_id,
        "sourceWalletName": source_wallet_name,
        "destinationBusinessId": destination_business_id,
        "destinationWalletName": destination_wallet_name,
        "amount": amount,
        "cashoutableAmount": cashoutable_amount,
        "currency": currency,
        "description": description or "",
    }
    return client.post(path, json=body)
