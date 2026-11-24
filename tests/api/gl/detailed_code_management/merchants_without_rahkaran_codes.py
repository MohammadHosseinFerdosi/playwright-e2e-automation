"""Port of post-without-rahkaran-codes.resource, post-suspend-merchant.resource.

Also post-get-suspended-list.resource (src/apis/gl/detailed-code-mangement/).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_GL_PATH

_SEARCH_WITHOUT_PATH = "/api/gl/admin/profile-mapping-rahkaran-codes/without-rahkaran-codes"
_SUSPEND_PATH = "/api/gl/admin/profile-mappings/suspend-merchant"
_SUSPENDED_LIST_PATH = "/api/gl/admin/profile-mappings/get-suspended-list"


class MerchantWithoutRahkaranCode(BaseModel):
    """One merchant record from the "without/suspended Rahkaran code" searches."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    business_name: str | None = Field(default=None, alias="businessName")
    national_code: str | None = Field(default=None, alias="nationalCode")
    rahkaran_code: str | None = Field(default=None, alias="rahkaranCode")


class MerchantsWithoutRahkaranCodesPage(BaseModel):
    """One page of the "without-rahkaran-codes" / "suspended list" response.

    Note the JSON key is ``profileMappings`` here, unlike the "with codes"
    endpoint which uses ``merchants`` — kept as separate models on purpose
    (see ``.cursor/rules/migration-quality.mdc``: don't force-unify two
    genuinely different response shapes just to share one class).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    merchants: list[MerchantWithoutRahkaranCode] = Field(
        default_factory=list, alias="profileMappings"
    )
    total_pages: int = Field(default=1, alias="totalPages")


def search_merchants_without_rahkaran_codes(
    client: ApiClient,
    *,
    page: int = 0,
    size: int = 250,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """POST search merchants without a Rahkaran code — one page."""
    return _post_search(client, _SEARCH_WITHOUT_PATH, page=page, size=size, payload=payload)


def search_suspended_merchants(
    client: ApiClient,
    *,
    page: int = 0,
    size: int = 250,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """POST search suspended merchants — one page."""
    return _post_search(client, _SUSPENDED_LIST_PATH, page=page, size=size, payload=payload)


def suspend_merchant(client: ApiClient, *, business_id: int, is_suspended: bool) -> dict[str, Any]:
    """POST suspend (``is_suspended=True``) or restore (``False``) a merchant by GL id."""
    path = client.ms_path(_SUSPEND_PATH, MS_GL_PATH)
    headers = {"accept": "application/json", "content-type": "application/json"}
    payload = {"id": business_id, "isSuspended": is_suspended}
    return client.post(path, json=payload, headers=headers)


def _post_search(
    client: ApiClient,
    endpoint: str,
    *,
    page: int,
    size: int,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    path = client.ms_path(endpoint, MS_GL_PATH)
    headers = {"accept": "application/json", "content-type": "application/json"}
    params = {"page": page, "size": size}
    result = client.post(path, params=params, json=payload or {}, headers=headers)
    return {
        "status_code": result["status_code"],
        "body": _parse_without_rahkaran_page(result.get("body")),
    }


def _parse_without_rahkaran_page(body: Any) -> Any:
    """Parse a 200 search body; return the raw value when it is not that shape."""
    if not isinstance(body, dict) or "profileMappings" not in body:
        return body
    try:
        return MerchantsWithoutRahkaranCodesPage.model_validate(body)
    except ValidationError:
        return body
