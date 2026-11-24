"""Port of src/apis/uaa/post-admin-businesses.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_UAA_PATH


def post_admin_businesses(
    client: ApiClient,
    name: str,
    username: str,
    password: str,
    roles: list[str],
    zone: str | None = None,
) -> dict[str, Any]:
    """Port of POST Admin Businesses.

    Returns the locked ``{status_code, body}`` envelope only — callers parse
    ``body`` for ``business_id`` (see ``BusinessFactory``).
    """
    path = client.ms_path("/admin/businesses", MS_UAA_PATH)

    headers = {"Agent": "CONSOLE"}
    if zone:
        headers["Zone"] = zone

    return client.post(
        path,
        headers=headers,
        json={
            "name": name,
            "username": username,
            "password": password,
            "roles": roles,
            "active": True,
        },
    )


def business_id_from_create_body(body: Any) -> str:
    """Extract business id from a successful POST /admin/businesses body."""
    if not isinstance(body, dict):
        raise ValueError(f"Expected dict body for business create, got: {body!r}")
    try:
        return body["userDetail"]["userId"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            f"Could not read business id from create body: {body!r}"
        ) from exc
