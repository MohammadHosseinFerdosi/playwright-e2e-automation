"""Generate the digital-signature certificate from a pending initiation.

Headers: ``User-Id``, ``Requester-App-Name``.
Body: password, type, providerTrackingCode.
Incomplete liveness → ``DIGITAL_SIGNATURE_INCOMPLETE_LIVENESS``.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.digital_signatures.models import (
    GenerateSignatureRequest,
    parse_generate_body,
)
from tests.api.kyc.paths import MS_DIGITAL_SIGNATURE_PATH, kyc_requester_headers


def post_digital_signatures_generate(
    client: ApiClient,
    user_id: str,
    requester_app_name: str,
    *,
    password: CHANGE_ME
    signature_type: int,
    provider_tracking_code: str,
) -> dict[str, Any]:
    """Generate a digital-signature certificate."""
    path = client.ms_path("/digital-signatures/generate", MS_DIGITAL_SIGNATURE_PATH)
    request = GenerateSignatureRequest.model_validate(
        {
            "password": password,
            "type": signature_type,
            "providerTrackingCode": provider_tracking_code,
        }
    )
    result = client.post(
        path,
        headers=kyc_requester_headers(user_id, requester_app_name),
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_generate_body(result.get("body")),
    }
