"""Port of src/apis/wallet-provider/transactions/post-transactions-payout.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH
from tests.services.tracking import random_tracking_code


def post_transactions_payout(
    client: ApiClient,
    amount: int,
    source_business_id: str,
    source_business_wallet_name: str,
    destination_user_id: str,
    destination_user_wallet_name: str | None = None,
    cashoutable_amount: int | None = None,
    sale_tracking_code: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Port of POST Transactions Payout — business wallet → user wallet."""
    path = client.ms_path("/transactions/payout", MS_WALLET_PROVIDER_PATH)

    body: dict[str, Any] = {
        "amount": amount,
        "trackingCode": random_tracking_code(25),
        "sourceBusinessId": source_business_id,
        "sourceWalletName": source_business_wallet_name,
        "destinationUserId": destination_user_id,
        "currency": "IRR",
    }
    if cashoutable_amount is not None:
        body["cashoutableAmount"] = cashoutable_amount
    if sale_tracking_code is not None:
        body["saleTrackingCode"] = sale_tracking_code
    if destination_user_wallet_name is not None:
        body["destinationWalletName"] = destination_user_wallet_name
    if description is not None:
        body["description"] = description

    return client.post(path, json=body)
