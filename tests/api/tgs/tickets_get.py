"""Port of src/apis/tgs/get-tickets.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_TGS_PATH


def get_tickets(
    client: ApiClient,
    ticket: str,
    platform_version: str,
) -> dict[str, Any]:
    """Port of Get Tickets — payment methods for a ticket."""
    path = client.ms_path(f"/tickets/{ticket}", MS_TGS_PATH)
    return client.get(path, headers={"Platform-Version": platform_version})
