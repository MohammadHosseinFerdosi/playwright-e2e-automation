"""Revoke the user's active digital signature for a given type.

Headers: ``User-Id``, ``Requester-App-Name``.
Body: type (signature type).
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.models import parse_result_body
from tests.api.kyc.paths import MS_DIGITAL_SIGNATURE_PATH, kyc_requester_headers


def post_digital_signatures_revoke(
    client: ApiClient,
    user_id: str,
    requester_app_name: str,
    *,
    signature_type: int,
) -> dict[str, Any]:
    """Revoke an active digital signature."""
    path = client.ms_path("/digital-signatures/revoke", MS_DIGITAL_SIGNATURE_PATH)
    result = client.post(
        path,
        headers=kyc_requester_headers(user_id, requester_app_name),
        json={"type": signature_type},
    )
    body = result.get("body")
    parsed = parse_result_body(body)
    return {
        "status_code": result["status_code"],
        "body": parsed if parsed is not None else body,
    }
