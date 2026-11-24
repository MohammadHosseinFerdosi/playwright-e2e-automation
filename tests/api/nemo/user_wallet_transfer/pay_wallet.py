"""Port of src/apis/nemo/user-wallet-transfer/post-wallets-transfer-pay-wallet.resource."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_NEMO_PATH


class TransferPayWalletBody(BaseModel):
    """Success body for POST /wallets/transfer/pay/wallet."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_code: str = Field(alias="trackingCode")


def post_wallets_transfer_pay_wallet(
    client: ApiClient,
    ticket: str,
    user_ip: str,
    transfer_type: str,
    agent: str,
) -> dict[str, Any]:
    """Port of POST Wallets Transfer Pay Wallet — complete transfer by ticket."""
    path = client.ms_path("/wallets/transfer/pay/wallet", MS_NEMO_PATH)
    headers = {"Agent": agent}
    body = {
        "ticket": ticket,
        "userIP": user_ip,
        "type": transfer_type,
    }
    result = client.post(path, headers=headers, json=body)
    response_body = result.get("body")
    if (
        result["status_code"] == 200
        and isinstance(response_body, dict)
        and "trackingCode" in response_body
    ):
        return {
            "status_code": result["status_code"],
            "body": TransferPayWalletBody.model_validate(response_body),
        }
    return result
