"""Poll native liveness status until verify (or fail).

Headers: ``User-Id``.
Query: signatureType.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.liveness.models import parse_liveness_status_body
from tests.api.kyc.paths import MS_KYC_LIVENESS_PATH, kyc_user_headers


def get_liveness_status(
    client: ApiClient,
    user_id: str,
    *,
    signature_type: int,
) -> dict[str, Any]:
    """Fetch native liveness status."""
    path = client.ms_path(
        f"/kyc/liveness/status?signatureType={signature_type}",
        MS_KYC_LIVENESS_PATH,
    )
    result = client.get(path, headers=kyc_user_headers(user_id))
    return {
        "status_code": result["status_code"],
        "body": parse_liveness_status_body(result.get("body")),
    }
