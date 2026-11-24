"""Upload the selfie video for an open liveness session.

Headers: ``User-Id``.
Body: signatureType, selfieVideoFileName, selfieVideoFileContent (base64).
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.liveness.models import parse_liveness_action_body
from tests.api.kyc.paths import MS_KYC_LIVENESS_PATH, kyc_user_headers


def post_liveness_native_selfie_video(
    client: ApiClient,
    user_id: str,
    *,
    signature_type: int,
    selfie_video_file_name: str,
    selfie_video_file_content: str,
) -> dict[str, Any]:
    """Upload selfie video for liveness."""
    path = client.ms_path("/kyc/liveness/native/selfie-video", MS_KYC_LIVENESS_PATH)
    result = client.post(
        path,
        headers=kyc_user_headers(user_id),
        json={
            "signatureType": signature_type,
            "selfieVideoFileName": selfie_video_file_name,
            "selfieVideoFileContent": selfie_video_file_content,
        },
    )
    return {
        "status_code": result["status_code"],
        "body": parse_liveness_action_body(result.get("body")),
    }
