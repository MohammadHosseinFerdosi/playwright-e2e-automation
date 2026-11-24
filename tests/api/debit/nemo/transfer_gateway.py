"""POST Nemo transfer route-prediction and fee on the app gateway.

Route-prediction asks which cash-out rail the app will use.
Essential request fields: amount, agenda, targetIban.
Fee asks the app cash-out fee. Essential request field: amount.
Headers: Authorization (Bearer), User-Id, Platform-Version.
Response: HTTP status plus body (result.title / clientCode on prediction).
"""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.debit.nemo.models import (
    TransferFeeRequest,
    TransferRoutePredictionRequest,
    parse_gateway_body,
)
from tests.config.constants import PLATFORM_VERSION_2023


def _app_headers(
    *,
    access_token: CHANGE_ME
    user_id: str,
    forwarded_for: str,
    platform_version: str,
) -> dict[str, str]:
    """Bearer and User-Id headers for Nemo app-gateway calls."""
    return {
        "Authorization": f"Bearer {access_token}",
        "User-Id": user_id,
        "X-Forwarded-For": forwarded_for,
        "Platform-Version": platform_version,
        "Content-Type": "application/json",
    }


def post_transfer_route_prediction(
    client: ApiClient,
    request: TransferRoutePredictionRequest,
    *,
    access_token: CHANGE_ME
    user_id: str,
    forwarded_for: str,
    platform_version: str = PLATFORM_VERSION_2023,
) -> dict[str, Any]:
    """Predict the cash-out gateway for an IBAN amount."""
    result = client.post(
        "/nemo/transfer/route-prediction",
        headers=_app_headers(
            access_token=CHANGE_ME
            user_id=user_id,
            forwarded_for=forwarded_for,
            platform_version=platform_version,
        ),
        json=request.to_payload(),
    )
    return {
        "status_code": result.get("status_code"),
        "body": parse_gateway_body(result.get("body")),
    }


def post_transfer_fee(
    client: ApiClient,
    request: TransferFeeRequest,
    *,
    access_token: CHANGE_ME
    user_id: str,
    forwarded_for: str,
    platform_version: str = PLATFORM_VERSION_2023,
) -> dict[str, Any]:
    """Predict the app cash-out fee for an amount."""
    result = client.post(
        "/nemo/transfer/fee",
        headers=_app_headers(
            access_token=CHANGE_ME
            user_id=user_id,
            forwarded_for=forwarded_for,
            platform_version=platform_version,
        ),
        json=request.to_payload(),
    )
    return {
        "status_code": result.get("status_code"),
        "body": parse_gateway_body(result.get("body")),
    }
