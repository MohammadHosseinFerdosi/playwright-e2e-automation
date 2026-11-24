"""Port of src/apis/nemo/admin/post-admin-wallets-businesses-config-search.resource."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_NEMO_PATH


class BusinessWalletConfigItem(BaseModel):
    """One wallet entry from Nemo businesses config search."""

    model_config = ConfigDict(extra="ignore")

    wallet_name: str = Field(alias="walletName")


class BusinessWalletsConfigSearchBody(BaseModel):
    """Success body for POST /admin/wallets/businesses/config/search."""

    model_config = ConfigDict(extra="ignore")

    wallets: list[BusinessWalletConfigItem] = Field(default_factory=list)


def post_admin_wallets_businesses_config_search(
    client: ApiClient,
    restrictions: list[dict[str, Any]],
    orders: list[Any] | None = None,
    page: int = 0,
    size: int = 50,
    user_id: str = "test-staff-user",
) -> dict[str, Any]:
    """Port of POST Admin Wallets businesses config Search (Nemo)."""
    path = client.ms_path(
        "/admin/wallets/businesses/config/search",
        MS_NEMO_PATH,
    )
    result = client.post(
        path,
        headers={"User-Id": user_id},
        params={"page": page, "size": size},
        json={
            "restrictions": restrictions,
            "orders": orders or [],
        },
    )
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "wallets" in body:
        return {
            "status_code": result["status_code"],
            "body": BusinessWalletsConfigSearchBody.model_validate(body),
        }
    return result
