"""Start basic digital-signature initiation after native liveness.

Headers: ``User-Id``, ``Requester-App-Name``.
Body: birthDate, name, englishName, nationalCard, postalCode, type,
livenessType, gender, password — omit password → ``BAD_REQUEST``.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.digital_signatures.models import (
    InitiateBasicRequest,
    parse_initiate_body,
)
from tests.api.kyc.paths import MS_DIGITAL_SIGNATURE_PATH, kyc_requester_headers


def post_digital_signatures_initiate_basic(
    client: ApiClient,
    user_id: str,
    requester_app_name: str,
    request: InitiateBasicRequest,
) -> dict[str, Any]:
    """Initiate a basic digital signature."""
    path = client.ms_path(
        "/digital-signatures/initiate/basic", MS_DIGITAL_SIGNATURE_PATH
    )
    result = client.post(
        path,
        headers=kyc_requester_headers(user_id, requester_app_name),
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_initiate_body(result.get("body")),
    }
