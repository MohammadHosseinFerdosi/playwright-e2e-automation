"""GET /addresses/postal-code/{postalCode} — resolve an Iranian postal code."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.addresses.models import parse_postal_code_inquiry_body
from tests.api.kyc.paths import MS_KYC_PATH, kyc_requester_headers


def get_addresses_postal_code(
    client: ApiClient,
    requester_app_name: str,
    user_id: str,
    postal_code: str,
) -> dict[str, Any]:
    """Inquire the address for a postal code."""
    path = client.ms_path(f"/addresses/postal-code/{postal_code}", MS_KYC_PATH)
    result = client.get(
        path,
        headers=kyc_requester_headers(user_id, requester_app_name),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_postal_code_inquiry_body(result.get("body")),
    }
