"""POST promissory-notes/refund."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH, promissory_requester_headers
from tests.api.kyc.promissory_notes.models import (
    TrackingCodeRequest,
    parse_result_or_raw,
)


def post_promissory_notes_refund(
    client: ApiClient,
    requester_app_name: str,
    tracking_code: str,
) -> dict[str, Any]:
    """Refund stamp-duty payment for a tracking code.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/promissory-notes/refund``.
    Required header: ``Requester-App-Name``.
    Required body: ``trackingCode``.
    """
    path = client.ms_path("/promissory-notes/refund", MS_PROMISSORY_NOTE_PATH)
    request = TrackingCodeRequest.model_validate({"trackingCode": tracking_code})
    result = client.post(
        path,
        headers=promissory_requester_headers(requester_app_name),
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_result_or_raw(result.get("body")),
    }
