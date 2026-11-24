"""POST admin promissory-notes settings/search."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import parse_settings_search_body


def post_admin_promissory_notes_settings_search(
    client: ApiClient,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search promissory settings recipients.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/admin/promissory-notes/settings/search``.
    Body is optional; empty object returns the full recipient list.
    """
    path = client.ms_path(
        "/admin/promissory-notes/settings/search", MS_PROMISSORY_NOTE_PATH
    )
    result = client.post(path, json=body if body is not None else {})
    return {
        "status_code": result["status_code"],
        "body": parse_settings_search_body(result.get("body")),
    }
