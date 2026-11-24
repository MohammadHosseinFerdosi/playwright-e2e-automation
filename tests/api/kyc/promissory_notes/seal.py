"""POST promissory-notes/seal."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import SealRequest, parse_result_or_raw


def post_promissory_notes_seal(
    client: ApiClient,
    tracking_code: str,
    sign_tracking_code: str,
    check_expiration: bool = True,
) -> dict[str, Any]:
    """Seal a signed promissory note.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/promissory-notes/seal``.
    Required body: ``trackingCode``, ``promissoryNoteSignTrackingCode``,
    ``checkExpiration``.
    """
    path = client.ms_path("/promissory-notes/seal", MS_PROMISSORY_NOTE_PATH)
    request = SealRequest.model_validate(
        {
            "trackingCode": tracking_code,
            "promissoryNoteSignTrackingCode": sign_tracking_code,
            "checkExpiration": check_expiration,
        }
    )
    result = client.post(path, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_result_or_raw(result.get("body")),
    }
