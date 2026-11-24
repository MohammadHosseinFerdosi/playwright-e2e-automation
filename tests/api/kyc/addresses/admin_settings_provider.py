"""GET/POST /admin/kyc/settings/address/provider — pin or restore address weights."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.addresses.models import (
    AddressProviderSettingsRequest,
    parse_address_settings_body,
)
from tests.api.kyc.paths import MS_KYC_PATH


def get_admin_kyc_settings_address_provider(client: ApiClient) -> dict[str, Any]:
    """Fetch the live address provider settings snapshot."""
    path = client.ms_path("/admin/kyc/settings/address/provider", MS_KYC_PATH)
    result = client.get(path)
    return {
        "status_code": result["status_code"],
        "body": parse_address_settings_body(result.get("body")),
    }


def post_admin_kyc_settings_address_provider(
    client: ApiClient,
    request: AddressProviderSettingsRequest,
) -> dict[str, Any]:
    """Create or update address provider weight settings."""
    path = client.ms_path("/admin/kyc/settings/address/provider", MS_KYC_PATH)
    result = client.post(path, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_address_settings_body(result.get("body")),
    }
