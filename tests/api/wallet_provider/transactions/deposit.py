"""Port of src/apis/wallet-provider/transactions/post-transactions-deposit.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH
from tests.services.tracking import random_tracking_code


def post_transactions_deposit(
    client: ApiClient,
    user_id: str,
    wallet_name: str,
    amount: int,
    currency: str = "IRR",
    tracking_code: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Port of Post Deposit Wallet — deposit from a wallet to the platform wallet."""
    path = client.ms_path("/transactions/deposit", MS_WALLET_PROVIDER_PATH)
    body: dict[str, Any] = {
        "trackingCode": tracking_code or random_tracking_code(25),
        "userId": user_id,
        "walletName": wallet_name,
        "amount": amount,
        "currency": currency,
        "description": description or "",
    }
    return client.post(path, json=body)
