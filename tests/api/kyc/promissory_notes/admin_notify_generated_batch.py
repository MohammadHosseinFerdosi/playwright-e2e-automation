"""POST admin/promissory-notes/notify-generated-batch."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import (
    TrackingCodesRequest,
    parse_result_or_raw,
)


def post_admin_promissory_notes_notify_generated_batch(
    client: ApiClient,
    tracking_codes: list[str],
) -> dict[str, Any]:
    """Ask the provider to generate a batch of notes.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/admin/promissory-notes/notify/generated/batch``.
    Required body: ``trackingCodes``.
    """
    path = client.ms_path(
        "/admin/promissory-notes/notify/generated/batch",
        MS_PROMISSORY_NOTE_PATH,
    )
    request = TrackingCodesRequest.model_validate(
        {"trackingCodes": tracking_codes}
    )
    result = client.post(path, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_result_or_raw(result.get("body")),
    }
