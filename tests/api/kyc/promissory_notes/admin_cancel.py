"""POST admin/promissory-notes/cancel."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import (
    TrackingCodeRequest,
    parse_result_or_raw,
)


def post_admin_promissory_notes_cancel(
    client: ApiClient,
    tracking_code: str,
) -> dict[str, Any]:
    """Administrator cancel of a promissory note.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/admin/promissory-notes/cancel``.
    Required body: ``trackingCode``.
    """
    path = client.ms_path("/admin/promissory-notes/cancel", MS_PROMISSORY_NOTE_PATH)
    request = TrackingCodeRequest.model_validate({"trackingCode": tracking_code})
    result = client.post(path, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_result_or_raw(result.get("body")),
    }
