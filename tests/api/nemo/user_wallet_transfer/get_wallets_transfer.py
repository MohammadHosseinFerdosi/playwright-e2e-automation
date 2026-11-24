"""Port of src/apis/nemo/user-wallet-transfer/get-wallets-transfer.resource."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_NEMO_PATH


class WalletsTransferInfoBody(BaseModel):
    """Success body for GET /wallets/transfer (remaining cashoutable cap)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    remaining_cap: int = Field(alias="remainingCap")
    wallet_balance: int = Field(alias="walletBalance")


def get_wallets_transfer(
    client: ApiClient,
    user_id: str,
    agent: str,
) -> dict[str, Any]:
    """Port of GET Wallets Transfer — wallet transfer info for a user."""
    path = client.ms_path("/wallets/transfer", MS_NEMO_PATH)
    headers = {
        "Agent": agent,
        "User-id": user_id,
    }
    result = client.get(path, headers=headers)
    body = result.get("body")
    if (
        result["status_code"] == 200
        and isinstance(body, dict)
        and "remainingCap" in body
        and "walletBalance" in body
    ):
        return {
            "status_code": result["status_code"],
            "body": WalletsTransferInfoBody.model_validate(body),
        }
    return result
