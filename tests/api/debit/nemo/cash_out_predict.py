"""POST /wallets/cash-out/predict.

Estimates the cash-out fee for a destination card before register.
Essential request fields: amount, targetPan (value, type, expireDate).
Response: HTTP status plus body with result.title and fee.
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.debit.nemo.models import CashOutPredictRequest, parse_predict_body
from tests.api.ms_paths import MS_NEMO_PATH
from tests.config.constants import PLATFORM_VERSION_2023


def post_cash_out_predict(
    client: ApiClient,
    request: CashOutPredictRequest,
    *,
    user_id: str,
    forwarded_for: str,
    platform_version: str = PLATFORM_VERSION_2023,
) -> dict[str, Any]:
    """Predict cash-out fee for a card pan."""
    path = client.ms_path("/wallets/cash-out/predict", MS_NEMO_PATH)
    headers = {
        "User-Id": user_id,
        "X-Forwarded-For": forwarded_for,
        "Platform-Version": platform_version,
        "Content-Type": "application/json",
    }
    result = client.post(path, headers=headers, json=request.to_payload())
    return {
        "status_code": result.get("status_code"),
        "body": parse_predict_body(result.get("body")),
    }
