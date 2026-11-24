"""Port of ``src/apis/uaa/get-admin-users-permissions.resource``."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient, ApiSide
from tests.api.ms_paths import MS_UAA_PATH


def get_admin_users_permissions(
    client: ApiClient,
    username: str,
    zone: str | None = None,
) -> dict[str, Any]:
    """GET /admin/users/permissions — dashboard permission list for UI inject."""
    if client.side is ApiSide.MICROSERVICE:
        path = client.ms_path("/admin/users/permissions", MS_UAA_PATH)
        headers: dict[str, str] = {"User-Id": username}
    else:
        path = "/admin/users/permissions"
        headers = {}
    if zone:
        headers["Zone"] = zone
    return client.get(path, headers=headers)
