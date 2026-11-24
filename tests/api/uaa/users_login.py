"""Port of src/apis/uaa/users/users-login.resource."""

from typing import Any

from tests.api.client import ApiClient


def post_users_login(
    client: ApiClient,
    user_id: str,
    password: CHANGE_ME
    device_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Port of POST Users Login.

    Robot hardcodes the APP session for this call (microservice side is not
    implemented there). `client` should be ``ApiSide.APP`` with
    ``APP_BASIC_AUTH``.
    """
    body: dict[str, Any] = {
        "username": user_id,
        "password": password,
    }
    if device_info:
        body["device"] = device_info

    return client.post("/users/login", json=body)
