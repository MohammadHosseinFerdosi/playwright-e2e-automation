"""POST /admin/kyc/settings/shahkar/provider/search — current Shahkar weights."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_KYC_PATH
from tests.api.kyc.shahkar.models import parse_shahkar_settings_body


def post_admin_kyc_settings_shahkar_provider_search(client: ApiClient) -> dict[str, Any]:
    """Fetch the live Shahkar provider settings snapshot."""
    path = client.ms_path("/admin/kyc/settings/shahkar/provider/search", MS_KYC_PATH)
    result = client.post(path)
    return {
        "status_code": result["status_code"],
        "body": parse_shahkar_settings_body(result.get("body")),
    }
