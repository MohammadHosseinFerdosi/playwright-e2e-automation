"""App PIN login for Nemo gateway Bearer calls."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from tests.api.client import ApiClient
from tests.api.uaa.users_login import post_users_login
from tests.services.debit.nemo_secrets import NemoSecrets, require_nemo_pin


def login_nemo_app_pin(app_client: ApiClient, secrets: NemoSecrets) -> str:
    """Return access_token from APP /users/login with PIN."""
    pin = require_nemo_pin(secrets)
    device = {
        "deviceId": str(uuid.uuid4()),
        "deviceModel": "WEB_BROWSER",
        "deviceAPI": "WEB_BROWSER",
        "osName": "WEB",
    }
    result = post_users_login(
        app_client,
        secrets.user_id,
        pin,
        device_info=device,
    )
    if result.get("status_code") != 200:
        pytest.skip(
            f"Nemo app PIN login failed HTTP={result.get('status_code')} "
            "(check pin_code / user_id in secrets/uat_nemo.yaml)"
        )
    body: Any = result.get("body")
    if not isinstance(body, dict):
        pytest.skip("Nemo app PIN login returned non-object body")
    token = body.get("accessToken") or body.get("access_token")
    if not isinstance(token, str) or not token.strip():
        pytest.skip("Nemo app PIN login missing accessToken")
    return token.strip()
