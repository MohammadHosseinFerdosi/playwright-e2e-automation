"""Check that a password matches the user's active digital signature.

Headers: ``User-Id``, ``Requester-App-Name``.
Body: password.
No signature → ``DIGITAL_SIGNATURE_NOT_FOUND``; wrong password →
``DIGITAL_SIGNATURE_PASSWORD_MISMATCH``.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.models import parse_result_body
from tests.api.kyc.paths import MS_DIGITAL_SIGNATURE_PATH, kyc_requester_headers


def post_digital_signatures_validate_password(
    client: ApiClient,
    user_id: str,
    requester_app_name: str,
    *,
    password: CHANGE_ME
) -> dict[str, Any]:
    """Validate a digital-signature password."""
    path = client.ms_path(
        "/digital-signatures/validate-password", MS_DIGITAL_SIGNATURE_PATH
    )
    result = client.post(
        path,
        headers=kyc_requester_headers(user_id, requester_app_name),
        json={"password": password},
    )
    body = result.get("body")
    parsed = parse_result_body(body)
    return {
        "status_code": result["status_code"],
        "body": parsed if parsed is not None else body,
    }
