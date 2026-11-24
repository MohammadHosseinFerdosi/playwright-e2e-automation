"""POST promissory-notes/inquiry."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import InquiryRequest, parse_inquiry_body


def post_promissory_notes_inquiry(
    client: ApiClient,
    tracking_code: str,
) -> dict[str, Any]:
    """Look up notes by tracking code.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/promissory-notes/inquiry``.
    Required body: ``trackingCodes`` (list of one or more codes).
    """
    path = client.ms_path("/promissory-notes/inquiry", MS_PROMISSORY_NOTE_PATH)
    request = InquiryRequest.model_validate({"trackingCodes": [tracking_code]})
    result = client.post(path, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_inquiry_body(result.get("body")),
    }
