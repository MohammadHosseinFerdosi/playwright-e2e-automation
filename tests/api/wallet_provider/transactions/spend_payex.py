"""Port of src/apis/wallet-provider/transactions/post-transactions-spend-payex.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH
from tests.services.tracking import random_tracking_code


def post_transactions_spend_payex(
    client: ApiClient,
    source_list: list[dict[str, Any]],
    destinations_list: list[dict[str, Any]],
    currency: str,
    description: str | None = None,
) -> dict[str, Any]:
    """Port of POST Transactions Spend Payex."""
    path = client.ms_path("/transactions/spend/payex", MS_WALLET_PROVIDER_PATH)

    body: dict[str, Any] = {
        "sources": source_list,
        "destinations": destinations_list,
        "trackingCode": random_tracking_code(30, alphabet="abcdefghijklmnopqrstuvwxyz"),
        "currency": currency,
        "description": description
        if description is not None
        else "Spend payex for api automation test.",
    }
    return client.post(path, json=body)
