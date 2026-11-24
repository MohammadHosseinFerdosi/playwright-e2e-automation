"""Port of src/apis/wallet-provider/wallets/get-wallets-users-total-balance.resource."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient, ApiSide
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


class TotalBalanceBody(BaseModel):
    """Success body for GET /wallets/users/total-balance."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    balance: int
    cashoutable_balance: int = Field(alias="cashoutableBalance")
    non_cashoutable_balance: int = Field(alias="nonCashoutableBalance")
    time_bound_balance: int = Field(alias="timeBoundBalance")


def get_wallets_users_total_balance(
    client: ApiClient,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Port of GET Wallets Users Total Balance.

    APP side: authenticated customer (Bearer on the client); no user id.
    MICROSERVICE side: requires ``user_id`` as the ``User-Id`` header.

    On HTTP 200 with a balance payload, ``body`` is a ``TotalBalanceBody``.
    Failure / non-balance bodies stay as raw dicts.
    """
    path = "/wallets/users/total-balance"
    headers: dict[str, str] = {}

    if client.side is ApiSide.MICROSERVICE:
        if not user_id:
            raise ValueError("For microservice side call, user id should not be empty.")
        headers["User-Id"] = user_id

    path = client.ms_path(path, MS_WALLET_PROVIDER_PATH)
    result = client.get(path, headers=headers)
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "balance" in body:
        result = {
            "status_code": result["status_code"],
            "body": TotalBalanceBody.model_validate(body),
        }
    return result
