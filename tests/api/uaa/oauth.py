"""Port of src/apis/uaa/oauth/oauth-token.resource."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient, ApiSide
from tests.api.ms_paths import MS_UAA_PATH


class OAuthTokenBody(BaseModel):
    """Success body for password-grant oauth/token."""

    model_config = ConfigDict(extra="ignore")

    access_token: str
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    scope: str | None = None
    jti: str | None = Field(default=None)


def post_oauth_token(
    client: ApiClient,
    username: str,
    password: str,
    device_id: str,
    client_id: str | None = None,
    zone: str | None = None,
) -> dict[str, Any]:
    """Port of POST Oauth Token from src/apis/uaa/oauth/oauth-token.resource.

    `client` must already carry the Basic Auth client credential as its
    `auth_header` — this endpoint authenticates the *client*, not the user,
    via the session's Authorization header (matching the Robot keyword's
    `${basic_auth_param}` passed straight into `Create A Session`).

    Sends form-encoded data (grant_type=password), not JSON — matches the
    Robot keyword's `data=${body}` on `POST On Session`.
    """
    if client.side is ApiSide.DASHBOARD:
        path = "admin/oauth/token"
    else:
        path = client.ms_path("oauth/token", MS_UAA_PATH)

    headers = {"Zone": zone} if zone else {}

    data = {
        "username": username,
        "password": password,
        "device_id": device_id,
        "grant_type": "password",
    }
    if client_id:
        data["client_id"] = client_id

    result = client.post(path, headers=headers, data=data)
    body = result.get("body")
    if result["status_code"] == 200 and isinstance(body, dict) and "access_token" in body:
        result = {
            "status_code": result["status_code"],
            "body": OAuthTokenBody.model_validate(body),
        }
    return result
