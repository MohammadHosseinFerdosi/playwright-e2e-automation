"""Remove the user's current native liveness session.

Headers: ``User-Id``.
Body: signatureType.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.liveness.models import parse_liveness_action_body
from tests.api.kyc.paths import MS_KYC_LIVENESS_PATH, kyc_user_headers


def post_liveness_native_remove(
    client: ApiClient,
    user_id: str,
    *,
    signature_type: int,
) -> dict[str, Any]:
    """Remove the current native liveness session."""
    path = client.ms_path("/kyc/liveness/native/remove", MS_KYC_LIVENESS_PATH)
    result = client.post(
        path,
        headers=kyc_user_headers(user_id),
        json={"signatureType": signature_type},
    )
    return {
        "status_code": result["status_code"],
        "body": parse_liveness_action_body(result.get("body")),
    }
