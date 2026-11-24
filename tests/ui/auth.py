"""UI session helpers — port of Playwright front-auth / walkthrough / popup resources.

Default path for domain UI tests: API ``login_to_app`` → inject ``localStorage`` → reload.
Full UI OTP login lives on ``LoginPage`` for auth e2e only.
"""

from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from tests.api.client import ApiClient
from tests.api.uaa.admin_users_permissions import get_admin_users_permissions
from tests.config.settings import Settings
from tests.services.auth import login_to_app, login_to_dashboard
from tests.services.db.mysql_client import MySQLClient
from tests.services.db.redis_client import RedisClient
from tests.services.factories import User
from tests.ui.labels.app import AppLabels as L


def require_dashboard_credentials(settings: Settings) -> tuple[str, str]:
    """Return dashboard username/password or raise when env secrets are missing."""
    username = settings.dashboard_username
    password = CHANGE_ME
    if not username or not password:
        raise RuntimeError("DASHBOARD_USERNAME / DASHBOARD_PASSWORD required")
    return username, password


WALKTHROUGH_DONE = '{"step":"done"}'
WALKTHROUGH_KEYS = (
    "walk-through-dpx",
    "hub-walk-through",
    "profile-walk-through",
    "stores-walk-through",
    "transaction-walk-through",
)

LOGIN_POPUP_CLOSE = (
    "//div[contains(@class,'notice-container')]"
    "//button[contains(@class,'ngx-button') and "
    f"contains(normalize-space(.), '{L.CLOSE}')]"
)
LOGIN_POPUP_SPLASH = "#splash_bg"


def mark_walkthrough_done_in_storage(page: Page, *, skip_hub_onboarding: bool = False) -> None:
    """Port of ``Skip Walkthrough - Local Storage``."""
    for key in WALKTHROUGH_KEYS:
        page.evaluate(
            "(pair) => localStorage.setItem(pair[0], pair[1])",
            [key, WALKTHROUGH_DONE],
        )
    if skip_hub_onboarding:
        page.evaluate("() => localStorage.setItem('checkHubOnboarding', 'true')")


def skip_walkthrough_ui(page: Page, *, skip_hub_onboarding: bool = False) -> None:
    """Port of ``Skip Walkthrough - UI`` — clicks close when present."""
    close_btn = page.locator("css=ngx-button.close-btn button")
    try:
        close_btn.first.wait_for(state="visible", timeout=5_000)
        close_btn.first.click()
    except PlaywrightTimeoutError:
        return
    if skip_hub_onboarding:
        for text in (L.CONTINUE, L.CONTINUE, L.GOT_IT):
            btn = page.get_by_role("button", name=text)
            if btn.count():
                btn.first.click()


def dismiss_login_popup_if_present(page: Page, timeout_ms: int = 8_000) -> None:
    """Dismiss the post-login hub notice when it appears; no-op when absent.

    The notice is async after hub land — wait for close (do not early-return on
    ``count() == 0``), then wait for ``#splash_bg`` so hub tiles are clickable.
    """
    notice_close = page.locator(f"xpath={LOGIN_POPUP_CLOSE}")
    role_close = page.get_by_role("button", name=L.CLOSE)
    close = notice_close.or_(role_close).first
    try:
        close.wait_for(state="visible", timeout=timeout_ms)
        close.click(timeout=timeout_ms)
    except PlaywrightTimeoutError:
        pass

    splash = page.locator(LOGIN_POPUP_SPLASH)
    try:
        splash.first.wait_for(state="hidden", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return


def inject_app_session(
    page: Page,
    *,
    settings: Settings,
    access_token: CHANGE_ME
    refresh_token: CHANGE_ME
    user_id: str,
    device_id: str,
    cell_number: str,
    skip_walkthrough: bool = True,
    skip_hub_onboarding: bool = False,
) -> None:
    """Write ``__dp_storage`` / ``__dp_machine_id`` then reload (API login handler)."""
    origin = settings.app_base_url.rstrip("/")
    if not page.url.startswith(origin):
        page.goto(origin, wait_until="domcontentloaded")

    storage = {
        "auth": {
            "access": access_token,
            "refresh": refresh_token,
            "userId": user_id,
            "phoneNumber": cell_number,
        }
    }
    payload = {
        "storage_json": json.dumps(storage, ensure_ascii=False),
        "device_id": device_id,
        "skip_walkthrough": skip_walkthrough,
        "walkthrough_done": WALKTHROUGH_DONE,
        "walkthrough_keys": list(WALKTHROUGH_KEYS),
        "skip_hub_onboarding": skip_hub_onboarding,
    }
    page.evaluate(
        """(p) => {
            localStorage.clear();
            localStorage.setItem('__dp_storage', p.storage_json);
            localStorage.setItem('__dp_machine_id', p.device_id);
            if (p.skip_walkthrough) {
                for (const key of p.walkthrough_keys) {
                    localStorage.setItem(key, p.walkthrough_done);
                }
                if (p.skip_hub_onboarding) {
                    localStorage.setItem('checkHubOnboarding', 'true');
                }
            }
        }""",
        payload,
    )
    page.reload(wait_until="domcontentloaded")


def inject_dashboard_session(
    page: Page,
    *,
    settings: Settings,
    access_token: CHANGE_ME
    refresh_token: CHANGE_ME
    username: str,
    permissions: list[Any],
) -> None:
    """Port of ``API Login To DASHBOARD Handler`` storage inject."""
    origin = settings.dashboard_base_url.rstrip("/")
    if not page.url.startswith(origin):
        page.goto(settings.dashboard_login_url, wait_until="domcontentloaded")

    status = {
        "status": {
            "loggedIn": True,
            "userId": username,
            "permissions": permissions,
            "oAuth": {
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
        }
    }
    page.evaluate(
        """(authJson) => {
            localStorage.clear();
            localStorage.setItem('auth', authJson);
        }""",
        json.dumps(status, ensure_ascii=False),
    )
    page.reload(wait_until="domcontentloaded")


class AppUiAuth:
    """Orchestrates customer UI login (API inject by default)."""

    def __init__(
        self,
        settings: Settings,
        app_client: ApiClient,
        redis_client: RedisClient,
        mysql_client: MySQLClient,
    ) -> None:
        """Bind settings and backend clients used for API login + inject."""
        self._settings = settings
        self._app_client = app_client
        self._redis = redis_client
        self._mysql = mysql_client

    def login_via_api_inject(
        self,
        page: Page,
        cell_number: str,
        *,
        pin_code: str = "",
        otp_overwrite: str | None = None,
        skip_walkthrough: bool = True,
        skip_login_popup: bool = True,
        land_on_hub: bool = True,
    ) -> dict[str, str]:
        """Log in via API, inject tokens into localStorage, optionally land on hub."""
        auth = login_to_app(
            self._app_client,
            self._redis,
            self._mysql,
            cell_number,
            pin_code=pin_code,
            otp_overwrite=otp_overwrite,
        )
        inject_app_session(
            page,
            settings=self._settings,
            access_token=auth["access_token"],
            refresh_token=auth["refresh_token"],
            user_id=auth["user_id"],
            device_id=auth["device_id"],
            cell_number=cell_number,
            skip_walkthrough=skip_walkthrough,
        )
        if land_on_hub:
            page.goto(self._settings.app_hub_url, wait_until="domcontentloaded")
        if skip_login_popup:
            dismiss_login_popup_if_present(page)
        return auth

    def login_user_via_api_inject(
        self,
        page: Page,
        user: User,
        *,
        skip_walkthrough: bool = True,
        skip_login_popup: bool = True,
        land_on_hub: bool = True,
    ) -> User:
        """Inject tokens already present on a ``User`` (e.g. from ``UserFactory``)."""
        if not user.access_token or not user.user_id:
            raise ValueError("User is missing access_token/user_id for UI inject")
        inject_app_session(
            page,
            settings=self._settings,
            access_token=CHANGE_ME
            refresh_token=CHANGE_ME
            user_id=user.user_id,
            device_id=user.device_id,
            cell_number=user.user_cell_number,
            skip_walkthrough=skip_walkthrough,
        )
        if land_on_hub:
            page.goto(self._settings.app_hub_url, wait_until="domcontentloaded")
        if skip_login_popup:
            dismiss_login_popup_if_present(page)
        return user


class DashboardUiAuth:
    """Dashboard UI login via API + localStorage inject (Robot API handler)."""

    def __init__(
        self,
        settings: Settings,
        dashboard_client: ApiClient,
        microservice_client: ApiClient,
    ) -> None:
        """Bind settings and API clients used for dashboard inject login."""
        self._settings = settings
        self._dashboard_client = dashboard_client
        self._ms_client = microservice_client

    def login_via_api_inject(
        self,
        page: Page,
        username: str,
        password: CHANGE_ME
    ) -> dict[str, Any]:
        """Log in via dashboard API, inject auth, navigate home when configured."""
        auth = login_to_dashboard(self._dashboard_client, username, password)
        perm = get_admin_users_permissions(self._ms_client, username, zone="")
        if perm["status_code"] != 200:
            raise RuntimeError(
                f"GET admin users permissions failed: {perm['status_code']} {perm['body']}"
            )
        body = perm["body"] or {}
        permissions = body.get("permissions") if isinstance(body, dict) else None
        if permissions is None:
            raise RuntimeError(f"Permissions missing in response: {body!r}")
        inject_dashboard_session(
            page,
            settings=self._settings,
            access_token=auth["access_token"],
            refresh_token=auth["refresh_token"],
            username=username,
            permissions=permissions,
        )
        if self._settings.dashboard_home_url:
            page.goto(self._settings.dashboard_home_url, wait_until="domcontentloaded")
        return {**auth, "permissions": permissions}
