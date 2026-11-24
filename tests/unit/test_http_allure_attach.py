"""Unit tests for Allure HTTP attach and credential redaction (no UAT)."""

import pytest

from tests.services import assert_report as ar
from tests.services.assert_report import (
    _PASSWORD_MASK_FILL,
    _PASSWORD_MIN_PLAIN_LEN,
    _PASSWORD_PREFIX_LEN,
    _PASSWORD_SUFFIX_LEN,
    _REDACTED,
    _mask_password_value,
    mask_secrets,
)


def _long_password() -> str:
    return (
        "A" * _PASSWORD_PREFIX_LEN
        + "HIDDEN"
        + "1" * _PASSWORD_SUFFIX_LEN
    )


def test_mask_password_value_uses_shared_affix_constants() -> None:
    plain = _long_password()
    expected = (
        f"{plain[:_PASSWORD_PREFIX_LEN]}{_PASSWORD_MASK_FILL}"
        f"{plain[-_PASSWORD_SUFFIX_LEN:]}"
    )
    assert _mask_password_value(plain) == expected


def test_mask_password_value_hides_values_shorter_than_minimum() -> None:
    short = "x" * (_PASSWORD_MIN_PLAIN_LEN - 1)
    assert _mask_password_value(short) == _REDACTED


def test_mask_secrets_partially_masks_password_values() -> None:
    plain = _long_password()
    short = "x" * (_PASSWORD_MIN_PLAIN_LEN - 1)
    payload = {
        "password": plain,
        "userPassword": plain,
        "current_password": short,
        "grant_type": "password",
    }
    masked = mask_secrets(payload)
    assert masked["password"] == _mask_password_value(plain)
    assert masked["userPassword"] == _mask_password_value(plain)
    assert masked["current_password"] == _mask_password_value(short)
    assert masked["grant_type"] == "password"


def test_mask_secrets_redacts_authorization_and_access_token() -> None:
    payload = {
        "Authorization": "Bearer header.payload.sig",
        "accessToken": "secret-token",
        "cookie": "session=secret",
        "result": {"title": "SUCCESS"},
    }
    masked = mask_secrets(payload)
    assert masked["Authorization"] == _REDACTED
    assert masked["accessToken"] == _REDACTED
    assert masked["cookie"] == _REDACTED
    assert masked["result"]["title"] == "SUCCESS"


def test_mask_secrets_redacts_bearer_in_free_text() -> None:
    text = "Authorization: Bearer abc.def.ghi"
    assert mask_secrets(text) == f"Authorization: Bearer {_REDACTED}"


def test_attach_http_exchange_includes_request_and_response_bodies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, object]] = []

    def _fake_attach_json(name: str, obj: object) -> None:
        captured.append((name, obj))

    monkeypatch.setattr(ar, "attach_json", _fake_attach_json)
    request_body = {"provider": "example", "enabled": True}
    response_body = {"items": [{"id": 1, "status": "ok"}]}
    ar.attach_http_exchange(
        method="POST",
        url="https://example.test/admin/settings",
        request_headers={"cookie": "secret"},
        request_body=request_body,
        status_code=200,
        response_headers={"content-type": "application/json"},
        response_body=response_body,
    )
    assert [name for name, _ in captured] == [
        "Request POST /admin/settings",
        "Response POST /admin/settings -> 200",
    ]
    request_payload = captured[0][1]
    response_payload = captured[1][1]
    assert isinstance(request_payload, dict)
    assert isinstance(response_payload, dict)
    assert request_payload["body"] == request_body
    assert response_payload["body"] == response_body
    assert response_payload["status_code"] == 200
