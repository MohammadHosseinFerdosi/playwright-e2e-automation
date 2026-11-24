"""POST admin provider success-rate search."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import (
    ProviderSuccessRateSearchRequest,
    parse_success_rate_search_body,
)


def post_admin_promissory_notes_provider_success_rate_search(
    client: ApiClient,
    page: int = 0,
    size: int = 10,
    restrictions: list[Any] | None = None,
    orders: list[Any] | None = None,
) -> dict[str, Any]:
    """Search paginated provider success-rate history.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/kyc/admin/promissory-notes/provider/success-rate/search``.
    This UAT route is under ``/kyc/admin``; the other admin promissory
    endpoints are not. Without that segment UAT returns 404.
    Required query: ``page``, ``size``. Body: ``restrictions``, ``orders``
    (lists; empty allowed).
    """
    path = client.ms_path(
        "/kyc/admin/promissory-notes/provider/success-rate/search",
        MS_PROMISSORY_NOTE_PATH,
    )
    request = ProviderSuccessRateSearchRequest.model_validate(
        {
            "restrictions": restrictions if restrictions is not None else [],
            "orders": orders if orders is not None else [],
        }
    )
    result = client.post(
        path,
        params={"page": page, "size": size},
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_success_rate_search_body(result.get("body")),
    }
