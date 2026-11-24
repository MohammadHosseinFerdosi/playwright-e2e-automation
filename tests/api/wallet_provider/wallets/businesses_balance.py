"""Port of src/apis/wallet-provider/wallets/get-wallets-businesses-balance.resource."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_WALLET_PROVIDER_PATH


class BusinessWalletBalanceBody(BaseModel):
    """Success body for GET /wallets/businesses/balance."""

    model_config = ConfigDict(extra="ignore")

    balance: int = 0
    currency: str = "IRR"
    wallet_name: str | None = Field(default=None, alias="walletName")


def get_wallets_businesses_balance(
    client: ApiClient,
    business_id: str,
    wallet_name: str,
) -> dict[str, Any]:
    """Port of GET Wallets Businesses Balance.

    On microservice side, Robot sends ``User-Id`` = business id.
    """
    path = client.ms_path("/wallets/businesses/balance", MS_WALLET_PROVIDER_PATH)
    result = client.get(
        path,
        headers={"User-Id": business_id},
        params={"walletName": wallet_name},
    )
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "balance" in body:
        return {
            "status_code": result["status_code"],
            "body": BusinessWalletBalanceBody.model_validate(body),
        }
    return result
