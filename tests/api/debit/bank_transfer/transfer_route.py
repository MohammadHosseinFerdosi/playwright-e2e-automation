"""POST bank-transfer/transfer/route.

Creates a routed transfer row for the given tracking code and target IBAN.
Essential request fields: trackingCode, businessId, targetIban, amount,
ownerName, description, preferredType, agenda.
Response: HTTP status plus body with result.title, clientCode, bankCode, type, fee.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.debit.bank_transfer.models import (
    TransferRouteRequest,
    parse_transfer_body,
)
from tests.api.debit.paths import MS_BANK_TRANSFER_PATH, bank_transfer_user_headers


def post_bank_transfer_route(
    client: ApiClient,
    request: TransferRouteRequest,
    *,
    user_id: str,
    forwarded_for: str,
    platform_version: str,
) -> dict[str, Any]:
    """Route a bank transfer (no execute)."""
    path = client.ms_path("/bank-transfer/transfer/route", MS_BANK_TRANSFER_PATH)
    result = client.post(
        path,
        headers=bank_transfer_user_headers(
            user_id,
            forwarded_for=forwarded_for,
            platform_version=platform_version,
        ),
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_transfer_body(result.get("body")),
    }
