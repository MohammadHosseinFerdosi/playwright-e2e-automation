"""Port of src/apis/wallet-provider/wallets/get-wallets-users-balance.resource."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient, ApiSide
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


class WalletBalanceBody(BaseModel):
    """Success body for GET /wallets/users/balance."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    balance: int
    cashoutable_balance: int | None = Field(default=None, alias="cashoutableBalance")
    non_cashoutable_balance: int | None = Field(
        default=None, alias="nonCashoutableBalance"
    )


def get_wallets_users_balance(
    client: ApiClient,
    user_id: str,
    wallet_name: str,
) -> dict[str, Any]:
    """Port of GET Wallets Users Balance — per-wallet balance for one user."""
    path = "/wallets/users/balance"
    headers: dict[str, str] = {}

    if client.side is ApiSide.MICROSERVICE:
        path = client.ms_path(path, MS_WALLET_PROVIDER_PATH)
        headers["User-Id"] = user_id

    result = client.get(path, headers=headers, params={"walletName": wallet_name})
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "balance" in body:
        result = {
            "status_code": result["status_code"],
            "body": WalletBalanceBody.model_validate(body),
        }
    return result
