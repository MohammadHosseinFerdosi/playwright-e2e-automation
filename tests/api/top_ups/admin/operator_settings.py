"""GET/PUT ``/admin/top-ups/settings/operator/{product}`` — Platform dashboard."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient


class TopUpProduct(str, Enum):
    """Path segment after ``/admin/top-ups/settings/operator/``."""

    INTERNET = "internet"
    SIM_CARD = "sim-card"  # dashboard tile «شارژ» / topup


class OperatorId(int, Enum):
    """Mobile operator ids as used by the dashboard admin API."""

    MCI = 1
    MTN = 2
    RIGHTEL = 3
    SHATEL = 4


class ProviderDistribution(BaseModel):
    """One provider row inside an operator config (weight + enabled flag)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    provider: int
    weight: float = Field(alias="providerWeight")
    enabled: bool


class OperatorConfig(BaseModel):
    """Provider distributions for a single operator."""

    model_config = ConfigDict(extra="ignore")

    operator: int
    distributions: list[ProviderDistribution] = Field(default_factory=list)


class OperatorSettingsBody(BaseModel):
    """GET response uses ``configs``; PUT body uses ``distributions`` (same list shape)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    result: dict[str, Any]
    configs: list[OperatorConfig] = Field(default_factory=list)

    def config_for(self, operator: OperatorId | int) -> OperatorConfig:
        """Return the config for ``operator`` (raises ``LookupError`` if absent)."""
        op = int(operator)
        for item in self.configs:
            if item.operator == op:
                return item
        raise LookupError(f"No operator config for operator={op}")


def _headers(user_id: str, *, bearer: str | None = None) -> dict[str, str]:
    headers = {
        "User-Id": user_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    return headers


def _path(product: TopUpProduct | str) -> str:
    segment = product.value if isinstance(product, TopUpProduct) else str(product)
    return f"/admin/top-ups/settings/operator/{segment}"


def get_operator_settings(
    client: ApiClient,
    user_id: str,
    product: TopUpProduct | str,
    *,
    access_token: str | None = None,
) -> dict[str, Any]:
    """GET operator settings. Returns ``{status_code, body}``."""
    result = client.get(
        _path(product),
        headers=_headers(user_id, bearer=access_token),
    )
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "configs" in body:
        return {
            "status_code": result["status_code"],
            "body": OperatorSettingsBody.model_validate(body),
        }
    return result


def put_operator_settings(
    client: ApiClient,
    user_id: str,
    product: TopUpProduct | str,
    configs: Sequence[OperatorConfig | dict[str, Any]],
    *,
    access_token: str | None = None,
) -> dict[str, Any]:
    """PUT full operator settings. UI sends ``{distributions: [...]}`` (GET's configs)."""
    payload_list: list[dict[str, Any]] = []
    for item in configs:
        if isinstance(item, OperatorConfig):
            payload_list.append(
                {
                    "operator": item.operator,
                    "distributions": [
                        {
                            "provider": d.provider,
                            "providerWeight": d.weight,
                            "enabled": d.enabled,
                        }
                        for d in item.distributions
                    ],
                }
            )
        else:
            payload_list.append(item)

    result = client.put(
        _path(product),
        headers=_headers(user_id, bearer=access_token),
        json={"distributions": payload_list},
    )
    return result
