"""Port of src/apis/wallet-provider/transactions/post-transactions-user-transfer.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH
from tests.services.tracking import random_tracking_code


def post_transactions_user_transfer(
    client: ApiClient,
    source_user_id: str,
    source_wallet_name: str,
    destination_user_id: str,
    destination_wallet_name: str,
    amount: int,
    cashoutable_amount: int,
    currency: str = "IRR",
    tracking_code: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Port of POST Transactions user-Transfer — user wallet → user wallet.

    Path is ``/transactions/transfer`` (wallet-provider), distinct from Nemo
    user-wallet-transfer under ``/wallets/transfer``.
    """
    path = client.ms_path("/transactions/transfer", MS_WALLET_PROVIDER_PATH)
    body: dict[str, Any] = {
        "trackingCode": tracking_code or random_tracking_code(25),
        "sourceUserId": source_user_id,
        "sourceWalletName": source_wallet_name,
        "destinationUserId": destination_user_id,
        "destinationWalletName": destination_wallet_name,
        "amount": amount,
        "cashoutableAmount": cashoutable_amount,
        "currency": currency,
    }
    if description:
        body["description"] = description
    return client.post(path, json=body)
