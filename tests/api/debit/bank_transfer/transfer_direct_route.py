"""POST /bank-transfer/transfer/direct-route — TREASURY ACH payout."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.debit.bank_transfer.models import (
    TransferDirectRouteRequest,
    parse_transfer_body,
)
from tests.api.debit.paths import MS_BANK_TRANSFER_PATH, bank_transfer_user_headers


def post_bank_transfer_direct_route(
    client: ApiClient,
    request: TransferDirectRouteRequest,
    *,
    user_id: str,
    forwarded_for: str,
    platform_version: str,
) -> dict[str, Any]:
    """Submit a treasury direct-route (source + target IBAN)."""
    path = client.ms_path(
        "/bank-transfer/transfer/direct-route", MS_BANK_TRANSFER_PATH
    )
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
