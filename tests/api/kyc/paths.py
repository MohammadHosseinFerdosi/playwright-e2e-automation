"""KYC microservice path helpers."""

from __future__ import annotations

from tests.api.ms_paths import (
    MS_DIGITAL_SIGNATURE_PATH,
    MS_KYC_LIVENESS_PATH,
    MS_KYC_PATH,
    MS_PROMISSORY_NOTE_PATH,
)

__all__ = [
    "MS_DIGITAL_SIGNATURE_PATH",
    "MS_KYC_LIVENESS_PATH",
    "MS_KYC_PATH",
    "MS_PROMISSORY_NOTE_PATH",
    "kyc_user_headers",
    "kyc_requester_headers",
    "promissory_requester_headers",
    "requester_app_headers",
]


def kyc_user_headers(user_id: str) -> dict[str, str]:
    """Build User-Id headers for KYC calls."""
    return {"User-Id": user_id}


def requester_app_headers(requester_app_name: str) -> dict[str, str]:
    """Build Requester-App-Name header for KYC routes that do not send User-Id."""
    return {"Requester-App-Name": requester_app_name}


def kyc_requester_headers(user_id: str, requester_app_name: str) -> dict[str, str]:
    """Build User-Id + Requester-App-Name headers."""
    return {"User-Id": user_id, **requester_app_headers(requester_app_name)}


def promissory_requester_headers(requester_app_name: str) -> dict[str, str]:
    """Build Requester-App-Name header for promissory-note route/init/refund."""
    return requester_app_headers(requester_app_name)
