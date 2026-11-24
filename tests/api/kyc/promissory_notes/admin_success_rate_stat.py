"""GET admin promissory-notes success-rate/stat."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import parse_success_rate_stat_body


def get_admin_promissory_notes_success_rate_stat(
    client: ApiClient,
) -> dict[str, Any]:
    """Read per-provider success-rate statistics.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/admin/promissory-notes/statistic/success-rate``.
    No body. Response is a list of provider rows.
    """
    path = client.ms_path(
        "/admin/promissory-notes/statistic/success-rate",
        MS_PROMISSORY_NOTE_PATH,
    )
    result = client.get(path)
    return {
        "status_code": result["status_code"],
        "body": parse_success_rate_stat_body(result.get("body")),
    }
