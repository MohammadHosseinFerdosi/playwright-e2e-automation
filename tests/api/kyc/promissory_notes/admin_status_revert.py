"""POST admin/promissory-notes/status/revert."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import (
    TrackingCodeRequest,
    parse_result_or_raw,
)


def post_admin_promissory_notes_status_revert(
    client: ApiClient,
    tracking_code: str,
) -> dict[str, Any]:
    """Revert note status as an administrator.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/admin/promissory-notes/status/revert``.
    Required body: ``trackingCode``.
    """
    path = client.ms_path(
        "/admin/promissory-notes/status/revert", MS_PROMISSORY_NOTE_PATH
    )
    request = TrackingCodeRequest.model_validate({"trackingCode": tracking_code})
    result = client.post(path, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_result_or_raw(result.get("body")),
    }
