"""POST /admin/kyc/settings/shahkar/provider — pin or restore Shahkar weights."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_KYC_PATH
from tests.api.kyc.shahkar.models import (
    ShahkarProviderSettingsRequest,
    parse_shahkar_settings_body,
)


def post_admin_kyc_settings_shahkar_provider(
    client: ApiClient,
    request: ShahkarProviderSettingsRequest,
) -> dict[str, Any]:
    """Create or update Shahkar provider weight settings."""
    path = client.ms_path("/admin/kyc/settings/shahkar/provider", MS_KYC_PATH)
    result = client.post(path, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_shahkar_settings_body(result.get("body")),
    }
