"""GET /wallets/cash-out/detail/{trackingCode}.

Reads a registered cash-out by tracking code.
Essential path field: trackingCode.
Response: HTTP status plus body with result.title, trackingCode, status, amount.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.debit.nemo.models import parse_register_body
from tests.api.ms_paths import MS_NEMO_PATH
from tests.config.constants import PLATFORM_VERSION_2023


def get_cash_out_detail(
    client: ApiClient,
    tracking_code: str,
    *,
    user_id: str,
    forwarded_for: str,
    platform_version: str = PLATFORM_VERSION_2023,
) -> dict[str, Any]:
    """Fetch cash-out detail by tracking code."""
    path = client.ms_path(
        f"/wallets/cash-out/detail/{tracking_code}", MS_NEMO_PATH
    )
    headers = {
        "User-Id": user_id,
        "X-Forwarded-For": forwarded_for,
        "Platform-Version": platform_version,
    }
    result = client.get(path, headers=headers)
    return {
        "status_code": result.get("status_code"),
        "body": parse_register_body(result.get("body")),
    }
