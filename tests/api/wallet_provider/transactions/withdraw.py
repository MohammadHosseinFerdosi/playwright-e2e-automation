"""Port of src/apis/wallet-provider/transactions/post-transactions-withdraw.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH
from tests.services.tracking import random_tracking_code


def post_transactions_withdraw(
    client: ApiClient,
    user_id: str,
    wallet_name: str,
    amount: int,
    fee: int,
    fee_payer_business_id: str,
    fee_payer_wallet_name: str,
    currency: str = "IRR",
    tracking_code: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Port of POST Transactions Withdraw."""
    path = client.ms_path("/transactions/withdraw", MS_WALLET_PROVIDER_PATH)
    body: dict[str, Any] = {
        "trackingCode": tracking_code or random_tracking_code(25),
        "userId": user_id,
        "walletName": wallet_name,
        "amount": amount,
        "fee": fee,
        "feePayerBusinessId": fee_payer_business_id,
        "feePayerWalletName": fee_payer_wallet_name,
        "currency": currency,
        "description": description or "",
    }
    return client.post(path, json=body)
