"""POST promissory-notes/init."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH, promissory_requester_headers
from tests.api.kyc.promissory_notes.models import InitRequest, parse_result_or_raw


def post_promissory_notes_init(
    client: ApiClient,
    requester_app_name: str,
    request: InitRequest,
) -> dict[str, Any]:
    """Create the note after route. Provider generate is asynchronous.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/promissory-notes/init``.
    Required header: ``Requester-App-Name``.
    Required body: ``trackingCode``, ``owner``, ``iban``, ``amount``,
    ``dueType``, ``dueOffsetInYears``, ``recipientId``, ``recipientCode``,
    ``description``.
    """
    path = client.ms_path("/promissory-notes/init", MS_PROMISSORY_NOTE_PATH)
    result = client.post(
        path,
        headers=promissory_requester_headers(requester_app_name),
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_result_or_raw(result.get("body")),
    }
