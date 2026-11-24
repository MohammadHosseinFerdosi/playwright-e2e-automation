"""Debit bank-transfer path helpers."""

from __future__ import annotations

from tests.api.ms_paths import MS_BANK_TRANSFER_PATH

__all__ = [
    "MS_BANK_TRANSFER_PATH",
    "bank_transfer_user_headers",
]


def bank_transfer_user_headers(
    user_id: str,
    *,
    forwarded_for: str,
    platform_version: str,
    content_type: str | None = "application/json",
) -> dict[str, str]:
    """Headers for bank-transfer MS calls (User-Id + Platform-Version)."""
    headers = {
        "User-Id": user_id,
        "X-Forwarded-For": forwarded_for,
        "Platform-Version": platform_version,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers
