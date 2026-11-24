"""GET bank-transfer/transfer/{trackingCode}.

Inquiry for a routed (or settled) transfer.
Essential path param: trackingCode.
Response: HTTP status plus body with clientCode, bankCode, status, journals.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.debit.bank_transfer.models import parse_transfer_body
from tests.api.debit.paths import MS_BANK_TRANSFER_PATH, bank_transfer_user_headers


def get_bank_transfer_inquiry(
    client: ApiClient,
    tracking_code: str,
    *,
    user_id: str,
    forwarded_for: str,
    platform_version: str,
) -> dict[str, Any]:
    """Inquiry a bank transfer by tracking code."""
    path = client.ms_path(
        f"/bank-transfer/transfer/{tracking_code}", MS_BANK_TRANSFER_PATH
    )
    result = client.get(
        path,
        headers=bank_transfer_user_headers(
            user_id,
            forwarded_for=forwarded_for,
            platform_version=platform_version,
            content_type=None,
        ),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_transfer_body(result.get("body")),
    }
