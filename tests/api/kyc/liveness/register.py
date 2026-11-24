"""Register a native liveness session for digital signature.

Headers: ``User-Id``, ``Requester-App-Name``.
Body: type, name, englishName, nationalCard, birthDate, postalCode,
nationalCardExpirationDate, fatherName, address, city, province, gender,
customVideoText.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.liveness.models import (
    RegisterLivenessRequest,
    parse_liveness_action_body,
)
from tests.api.kyc.paths import MS_KYC_LIVENESS_PATH, kyc_requester_headers


def post_liveness_native_register(
    client: ApiClient,
    user_id: str,
    requester_app_name: str,
    request: RegisterLivenessRequest,
) -> dict[str, Any]:
    """Register a native liveness session."""
    path = client.ms_path("/kyc/liveness/native/register", MS_KYC_LIVENESS_PATH)
    result = client.post(
        path,
        headers=kyc_requester_headers(user_id, requester_app_name),
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_liveness_action_body(result.get("body")),
    }
