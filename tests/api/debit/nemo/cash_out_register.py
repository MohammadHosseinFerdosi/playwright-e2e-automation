"""POST /wallets/cash-out/register.

Creates an IBAN cash-out on the Nemo wallet.
Essential request fields: amount, iban, birthDate.
Response: HTTP status plus body with result.title, trackingCode, ticket, status.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.debit.nemo.models import CashOutRegisterRequest, parse_register_body
from tests.api.ms_paths import MS_NEMO_PATH
from tests.config.constants import PLATFORM_VERSION_2023


def post_cash_out_register(
    client: ApiClient,
    request: CashOutRegisterRequest,
    *,
    user_id: str,
    forwarded_for: str,
    platform_version: str = PLATFORM_VERSION_2023,
) -> dict[str, Any]:
    """Register an IBAN wallet cash-out."""
    path = client.ms_path("/wallets/cash-out/register", MS_NEMO_PATH)
    headers = {
        "User-Id": user_id,
        "X-Forwarded-For": forwarded_for,
        "Platform-Version": platform_version,
        "Content-Type": "application/json",
    }
    result = client.post(path, headers=headers, json=request.to_payload())
    return {
        "status_code": result.get("status_code"),
        "body": parse_register_body(result.get("body")),
    }
