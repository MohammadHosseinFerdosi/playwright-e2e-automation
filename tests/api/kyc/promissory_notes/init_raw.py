"""POST promissory-notes/init with a raw body/headers."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import parse_result_or_raw


def post_promissory_notes_init_raw(
    client: ApiClient,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Init with a caller-built body (missing-field and injection cases).

    Path: ``{MS_PROMISSORY_NOTE_PATH}/promissory-notes/init``.
    Typical header: ``Requester-App-Name``. Typical body: ``trackingCode``,
    ``owner``, ``iban``, ``amount``, ``dueType``, ``dueOffsetInYears``,
    ``recipientId``, ``recipientCode``, ``description``. This client sends a
    caller-built body so negatives can omit a required field.
    """
    path = client.ms_path("/promissory-notes/init", MS_PROMISSORY_NOTE_PATH)
    result = client.post(path, headers=headers or {}, json=body)
    return {
        "status_code": result["status_code"],
        "body": parse_result_or_raw(result.get("body")),
    }
