"""POST /test/ach/trigger-transfer-report and /test/ach/trigger-resume-suspend."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.debit.bank_transfer.models import parse_scheduler_body
from tests.api.debit.paths import MS_BANK_TRANSFER_PATH, bank_transfer_user_headers


def post_trigger_transfer_report(
    client: ApiClient,
    *,
    user_id: str,
    forwarded_for: str,
    platform_version: str,
) -> dict[str, Any]:
    """Trigger ACH transfer-report scheduler job."""
    path = client.ms_path("/test/ach/trigger-transfer-report", MS_BANK_TRANSFER_PATH)
    result = client.post(
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
        "body": parse_scheduler_body(result.get("body")),
    }


def post_trigger_resume_suspend(
    client: ApiClient,
    *,
    user_id: str,
    forwarded_for: str,
    platform_version: str,
) -> dict[str, Any]:
    """Trigger ACH resume/suspend scheduler job."""
    path = client.ms_path("/test/ach/trigger-resume-suspend", MS_BANK_TRANSFER_PATH)
    result = client.post(
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
        "body": parse_scheduler_body(result.get("body")),
    }
