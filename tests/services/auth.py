"""Login orchestration — port of src/services/backend/auth-service.resource.

Plain functions, not a class: unlike ApiClient/DB clients/factories, a login
helper holds no connection or state of its own between calls — it just
orchestrates one oauth/OTP flow and hands back tokens for the caller to build
an authenticated ApiClient with.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from tests.api.client import ApiClient
from tests.api.uaa.oauth import OAuthTokenBody, post_oauth_token
from tests.api.uaa.users_login import post_users_login
from tests.api.uaa.users_send_sms import post_users_send_sms
from tests.api.user_mng.users_activate import post_users_activate
from tests.services.api_assert import ensure_ok
from tests.services.db.mysql_client import MySQLClient
from tests.services.db.redis_client import RedisClient


def login_business(client: ApiClient, username: str, password: str) -> str:
    """Port of Login For Business. Returns the access_token on success.

    `client` must be constructed with `auth_header=settings.business_basic_auth`
    (the Basic Auth client credential) — matching the Robot keyword's
    `${BUSINESS_BASIC_AUTH}` argument passed into `Create A Session`.
    """
    device_id = uuid.uuid4().hex[:15]
    result = ensure_ok(
        post_oauth_token(client, username, password, device_id),
        context=f"Business login for username={username!r}",
    )
    body = result["body"]
    if isinstance(body, OAuthTokenBody):
        return body.access_token
    if isinstance(body, dict) and "access_token" in body:
        return body["access_token"]
    raise RuntimeError(f"Business login 200 but missing access_token: {body}")


def login_to_dashboard(
    client: ApiClient,
    username: str,
    password: str,
    *,
    zone: str = "dashboard",
) -> dict[str, str]:
    """Port of Login To Dashboard. Returns access/refresh/user/device ids.

    ``client`` must be ``ApiSide.DASHBOARD`` with ``dashboard_basic_auth``.
    """
    device_id = uuid.uuid4().hex[:15]
    result = ensure_ok(
        post_oauth_token(client, username, password, device_id, zone=zone),
        context=f"Dashboard login for username={username!r}",
    )
    body = result["body"]
    if isinstance(body, OAuthTokenBody):
        access_token = body.access_token
        refresh_token = body.refresh_token or ""
    elif isinstance(body, dict) and "access_token" in body:
        access_token = body["access_token"]
        refresh_token = body.get("refresh_token") or ""
    else:
        raise RuntimeError(f"Dashboard login 200 but missing access_token: {body}")
    return {
        "user_id": username,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "device_id": device_id,
    }


def send_otp_sms_and_resolve_user(
    client: ApiClient,
    mysql_client: MySQLClient,
    cell_number: str,
) -> tuple[str, dict[str, Any], str]:
    """Send the OTP SMS exactly once and resolve the userId that owns it.

    Split out of ``login_to_app`` so a caller that needs to retry the
    OTP-read/activate steps (e.g. while the OTP is still propagating to Redis)
    can do so WITHOUT re-sending SMS on every attempt — re-sending on each
    retry is what trips Platform's ``USER_SEND_SMS_MAX_EXCEEDED`` throttle
    after a handful of retries, and it also masks the real failure behind
    that rate-limit error. See ``UserFactory._login_to_app_with_retry``.

    Returns ``(user_id, device_info, device_id)`` — pass these unchanged into
    ``complete_login_with_otp`` for as many retries as needed.
    """
    device_id = str(uuid.uuid4())
    device_info: dict[str, Any] = {
        "deviceId": device_id,
        "deviceModel": "WEB_BROWSER",
        "deviceAPI": "WEB_BROWSER",
        "osName": "WEB",
    }

    send_sms_response = post_users_send_sms(client, cell_number, device_info)
    user_id = _resolve_user_id_after_send_sms(
        send_sms_response, mysql_client, cell_number
    )
    return user_id, device_info, device_id


def complete_login_with_otp(
    client: ApiClient,
    redis_client: RedisClient,
    user_id: str,
    device_info: dict[str, Any],
    device_id: str,
    pin_code: str = "",
    otp_overwrite: str | None = None,
) -> dict[str, str]:
    """Read the already-sent OTP from Redis, activate, optionally PIN-login.

    Safe to call repeatedly for the same ``user_id``/``device_info`` — it
    never sends a new SMS, so a caller can retry this alone while waiting for
    the OTP to land in Redis.
    """
    otp = _resolve_otp(
        redis_client,
        user_id,
        device_info,
        otp_overwrite=otp_overwrite,
    )

    activate_result = ensure_ok(
        post_users_activate(client, user_id, otp),
        context=f"Activate user_id={user_id}",
    )

    body = activate_result["body"] or {}
    if body.get("hasPassword") is True:
        login_result = ensure_ok(
            post_users_login(client, user_id, pin_code, device_info),
            context=f"PIN login for user_id={user_id}",
        )
        login_body = login_result["body"] or {}
        access_token = login_body["accessToken"]
        refresh_token = login_body["refreshToken"]
    else:
        access_token = body["accessToken"]
        refresh_token = body["refreshToken"]

    # Match Robot: Set Access Token To Suite uses the original device_id variable,
    # not the possibly-updated deviceInfo.deviceId from the OTP payload.
    return {
        "user_id": user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "device_id": device_id,
    }


def login_to_app(
    client: ApiClient,
    redis_client: RedisClient,
    mysql_client: MySQLClient,
    cell_number: str,
    pin_code: str = "",
    otp_overwrite: str | None = None,
) -> dict[str, str]:
    """Port of Login To App — one-shot: send-sms -> resolve userId -> read OTP from Redis -> activate -> optional PIN login.

    Reads the OTP from Redis (``auth_otp_<userId>``) then activates; when
    ``hasPassword`` is true, also completes a PIN login. `client` must be
    ``ApiSide.APP`` with ``auth_header=settings.app_basic_auth``.

    For a *retried* login (e.g. ``UserFactory``'s "wait until succeeds" flow),
    do NOT loop this whole function — call ``send_otp_sms_and_resolve_user``
    once, then retry only ``complete_login_with_otp``. See that function's
    docstring for why: looping this one re-sends SMS on every attempt and
    will trip Platform's send-sms rate limit.

    Returns the same shape Robot stores in ``${AUTHENTICATED_USER_PARAMETERS}``::

        {
            "user_id": ...,
            "access_token": ...,
            "refresh_token": ...,
            "device_id": ...,
        }
    """
    user_id, device_info, device_id = send_otp_sms_and_resolve_user(
        client, mysql_client, cell_number
    )
    return complete_login_with_otp(
        client,
        redis_client,
        user_id,
        device_info,
        device_id,
        pin_code=pin_code,
        otp_overwrite=otp_overwrite,
    )


def _resolve_user_id_after_send_sms(
    send_sms_response: dict[str, Any],
    mysql_client: MySQLClient,
    cell_number: str,
) -> str:
    if send_sms_response["status_code"] == 200:
        return send_sms_response["body"]["userId"]

    body = send_sms_response.get("body") or {}
    result = body.get("result") or {}
    if result.get("title") == "UAA_OTP_ALREADY_SENT":
        db_result = mysql_client.fetch_all(
            "uaa_db",
            "SELECT * FROM uaa_db.users WHERE cell_number=%s AND zone_id=%s",
            (cell_number, "app"),
        )
        if db_result["status_code"] != 0:
            raise RuntimeError(
                f"mysql result should be successful but found: {db_result['body']}"
            )
        rows = db_result["body"]
        if not rows:
            raise RuntimeError("UAA_OTP_ALREADY_SENT but user row not found in uaa_db")
        return rows[0]["user_id"]

    raise RuntimeError(
        f"Send sms OTP failed with status_code={send_sms_response['status_code']}: {body}"
    )


def _resolve_otp(
    redis_client: RedisClient,
    user_id: str,
    device_info: dict[str, Any],
    otp_overwrite: str | None = None,
) -> str:
    if otp_overwrite is not None and otp_overwrite != "":
        return otp_overwrite

    key = f"auth_otp_{user_id}"
    get_otp_result = redis_client.get_key(key)
    if get_otp_result["status_code"] != 0:
        raise RuntimeError(
            f"Get OTP failed with status_code={get_otp_result['status_code']}: "
            f"{get_otp_result['body']}"
        )

    raw_value = get_otp_result["body"].get("value")
    if raw_value is None:
        raise RuntimeError(f"Get OTP failed: key {key!r} is empty")

    if isinstance(raw_value, bytes):
        otp_json = json.loads(raw_value.decode("utf-8"))
    else:
        otp_json = json.loads(raw_value)

    otp_list = _collect_otp_values(otp_json)
    if not otp_list:
        raise RuntimeError(f"Get OTP failed: no otpCodes values in key {key!r}")

    device = otp_json.get("device") or {}
    device_id_in_otp = device.get("deviceId")
    if device_id_in_otp:
        # Match Robot: when OTP already exists, device id must match the OTP payload.
        device_info["deviceId"] = device_id_in_otp

    return otp_list[-1]


def _collect_otp_values(otp_json: dict[str, Any]) -> list[str]:
    """Port of JSONPath ``$.otpCodes[*].[*].value`` used in Login To App."""
    values: list[str] = []
    for group in otp_json.get("otpCodes") or []:
        if isinstance(group, list):
            for item in group:
                if isinstance(item, dict) and "value" in item:
                    values.append(str(item["value"]))
        elif isinstance(group, dict) and "value" in group:
            values.append(str(group["value"]))
    return values
