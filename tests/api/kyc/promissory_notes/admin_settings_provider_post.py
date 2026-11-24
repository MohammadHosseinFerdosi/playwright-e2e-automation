"""POST admin promissory-notes settings/provider."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import (
    ProviderSettingsRequest,
    parse_result_or_raw,
)


def post_admin_promissory_notes_settings_provider(
    client: ApiClient,
    request: ProviderSettingsRequest,
) -> dict[str, Any]:
    """Update provider weights and auto-weighting for one recipient.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/admin/promissory-notes/settings/provider``.
    Required body: ``recipientDto.recipient``, ``recipientDto.providersDto``
    (``providerName``, ``weight``, ``active``, ``priority``),
    ``activeAutoWeighting``.
    """
    path = client.ms_path(
        "/admin/promissory-notes/settings/provider", MS_PROMISSORY_NOTE_PATH
    )
    result = client.post(path, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_result_or_raw(result.get("body")),
    }
