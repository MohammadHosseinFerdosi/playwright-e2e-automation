"""POST promissory-notes/sign-request/init."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import (
    TrackingCodeRequest,
    parse_result_or_raw,
)


def post_promissory_notes_sign_request_init(
    client: ApiClient,
    tracking_code: str,
) -> dict[str, Any]:
    """Start a signature request for a note.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/promissory-notes/sign-request/init``.
    Required body: ``trackingCode``. Ticket is not sent by this client.
    """
    path = client.ms_path(
        "/promissory-notes/sign-request/init", MS_PROMISSORY_NOTE_PATH
    )
    request = TrackingCodeRequest.model_validate({"trackingCode": tracking_code})
    result = client.post(path, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_result_or_raw(result.get("body")),
    }
