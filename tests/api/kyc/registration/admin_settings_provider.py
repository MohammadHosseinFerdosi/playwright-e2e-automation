"""POST /admin/kyc/settings/identity/registration/inquiry/provider — pin/restore."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_KYC_PATH
from tests.api.kyc.registration.models import (
    RegistrationSettingsRequest,
    parse_registration_settings_body,
)


def post_admin_kyc_settings_registration_provider(
    client: ApiClient,
    request: RegistrationSettingsRequest,
) -> dict[str, Any]:
    """Create or update registration provider weight settings."""
    path = client.ms_path(
        "/admin/kyc/settings/identity/registration/inquiry/provider",
        MS_KYC_PATH,
    )
    result = client.post(path, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_registration_settings_body(result.get("body")),
    }
