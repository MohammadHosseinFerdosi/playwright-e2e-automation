"""Port of src/apis/gl/detailed-code-mangement/post-with-rahkaran-codes.resource."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_GL_PATH

_SEARCH_PATH = "/api/gl/admin/profile-mapping-rahkaran-codes/with-rahkaran-codes"


class MerchantWithRahkaranCode(BaseModel):
    """One merchant record from the GL Rahkaran-code mapping search."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    business_name: str | None = Field(default=None, alias="businessName")
    national_code: str | None = Field(default=None, alias="nationalCode")
    rahkaran_code: str | None = Field(default=None, alias="rahkaranCode")
    # Live UAT returns this as a raw JSON int, not a zero-padded string — keep
    # both shapes valid instead of forcing a lossy str coercion.
    account_number: int | str | None = Field(default=None, alias="accountNumber")


class MerchantsWithRahkaranCodesPage(BaseModel):
    """One page of the ``with-rahkaran-codes`` search response."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    merchants: list[MerchantWithRahkaranCode] = Field(default_factory=list)
    total_pages: int = Field(default=1, alias="totalPages")


def search_merchants_with_rahkaran_codes(
    client: ApiClient,
    *,
    page: int = 0,
    size: int = 250,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """POST search merchants with Rahkaran code — one page.

    Args:
        client: Microservice-side ``ApiClient`` (no auth header on this side).
        page: Zero-based page index.
        size: Page size.
        payload: Optional ``{restrictions, orders}`` filter body; an empty body
            lists every merchant.

    Returns:
        ``{status_code, body}``. ``body`` is a ``MerchantsWithRahkaranCodesPage``
        when the response is a 200 shaped like the search result; otherwise the
        raw body is returned unchanged.
    """
    path = client.ms_path(_SEARCH_PATH, MS_GL_PATH)
    headers = {"accept": "application/json", "content-type": "application/json"}
    params = {"page": page, "size": size}
    result = client.post(path, params=params, json=payload or {}, headers=headers)
    return {
        "status_code": result["status_code"],
        "body": _parse_with_rahkaran_page(result.get("body")),
    }


def _parse_with_rahkaran_page(body: Any) -> Any:
    """Parse a 200 search body; return the raw value when it is not that shape."""
    if not isinstance(body, dict) or "merchants" not in body:
        return body
    try:
        return MerchantsWithRahkaranCodesPage.model_validate(body)
    except ValidationError:
        return body
