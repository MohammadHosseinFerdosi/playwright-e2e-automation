"""Port of src/apis/wallet-provider/transactions/post-transactions-spend-pay.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH
from tests.services.tracking import random_tracking_code


def post_transactions_spend_pay(
    client: ApiClient,
    source_user_id: str,
    destinations_list: list[dict[str, Any]],
    currency: str,
    description: str | None = None,
) -> dict[str, Any]:
    """Port of POST Transactions Spend Pay — user → one or more businesses."""
    path = client.ms_path("/transactions/spend/pay", MS_WALLET_PROVIDER_PATH)
    body: dict[str, Any] = {
        "sourceUserId": source_user_id,
        "destinations": destinations_list,
        "trackingCode": random_tracking_code(30, alphabet="abcdefghijklmnopqrstuvwxyz"),
        "currency": currency,
        "description": description
        if description is not None
        else "Spend for api automation test.",
    }
    return client.post(path, json=body)
