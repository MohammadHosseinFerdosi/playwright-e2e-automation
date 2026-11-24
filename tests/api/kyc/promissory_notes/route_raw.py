"""POST promissory-notes/route with a raw body/headers."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import parse_route_body


def post_promissory_notes_route_raw(
    client: ApiClient,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Route with a caller-built body (negatives and mass-assignment).

    Path: ``{MS_PROMISSORY_NOTE_PATH}/promissory-notes/route``.
    Typical header: ``Requester-App-Name``. Typical body: ``trackingCode``,
    ``recipientCode``. This client sends a caller-built body so negatives can
    omit the header or inject extra fields.
    """
    path = client.ms_path("/promissory-notes/route", MS_PROMISSORY_NOTE_PATH)
    result = client.post(path, headers=headers or {}, json=body)
    return {
        "status_code": result["status_code"],
        "body": parse_route_body(result.get("body")),
    }
