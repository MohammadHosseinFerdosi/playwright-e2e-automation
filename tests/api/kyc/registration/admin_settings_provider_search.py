"""POST .../registration/inquiry/provider/search — current registration weights."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_KYC_PATH
from tests.api.kyc.registration.models import parse_registration_settings_body


def post_admin_kyc_settings_registration_provider_search(
    client: ApiClient,
) -> dict[str, Any]:
    """Fetch the live registration provider settings snapshot."""
    path = client.ms_path(
        "/admin/kyc/settings/identity/registration/inquiry/provider/search",
        MS_KYC_PATH,
    )
    result = client.post(path)
    return {
        "status_code": result["status_code"],
        "body": parse_registration_settings_body(result.get("body")),
    }
