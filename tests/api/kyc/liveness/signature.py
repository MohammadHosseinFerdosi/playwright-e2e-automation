"""Upload the handwritten signature image for an open liveness session.

Headers: ``User-Id``, ``Requester-App-Name``.
Body: signatureType, signatureFileName, signatureFileContent (base64).
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.liveness.models import parse_liveness_action_body
from tests.api.kyc.paths import MS_KYC_LIVENESS_PATH, kyc_requester_headers


def post_liveness_native_signature(
    client: ApiClient,
    user_id: str,
    requester_app_name: str,
    *,
    signature_type: int,
    signature_file_name: str,
    signature_file_content: str,
) -> dict[str, Any]:
    """Upload signature media for liveness."""
    path = client.ms_path("/kyc/liveness/native/signature", MS_KYC_LIVENESS_PATH)
    result = client.post(
        path,
        headers=kyc_requester_headers(user_id, requester_app_name),
        json={
            "signatureType": signature_type,
            "signatureFileName": signature_file_name,
            "signatureFileContent": signature_file_content,
        },
    )
    return {
        "status_code": result["status_code"],
        "body": parse_liveness_action_body(result.get("body")),
    }
