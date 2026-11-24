"""GET admin promissory-notes settings/provider."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import parse_settings_body


def get_admin_promissory_notes_settings_provider(
    client: ApiClient,
) -> dict[str, Any]:
    """Read current provider routing settings.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/admin/promissory-notes/settings/provider``.
    Response includes ``settingDetail.recipientDtos`` and
    ``settingDetail.activeAutoWeighting``.
    """
    path = client.ms_path(
        "/admin/promissory-notes/settings/provider", MS_PROMISSORY_NOTE_PATH
    )
    result = client.get(path)
    return {
        "status_code": result["status_code"],
        "body": parse_settings_body(result.get("body")),
    }
