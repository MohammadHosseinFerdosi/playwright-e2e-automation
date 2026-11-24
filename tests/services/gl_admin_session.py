"""GL admin session Cookie.

The GL manual-transaction endpoint doesn't validate a JWT; it trusts a
caller-supplied User-Id (a fixed, non-secret test identity — see
``tests/api/gl/headers.py``) plus a live session Cookie.

Primary source: log into the same management-console dashboard
(``https://example.com/management-console``) that GL admin actions
are normally performed through, via the already-existing ``login_to_dashboard``
OAuth flow (``tests/services/auth.py``). If that gateway sets a session Cookie
on the response, ``httpx.Client`` captures it automatically and
``ApiClient.cookie_header()`` renders it as a header string.

Fallback source: a gitignored YAML file (``secrets/uat_gl_admin_session.yaml``)
for the case where the dashboard-derived cookie isn't accepted by GL's own
gateway. Domain caveat: the dashboard lives on ``example.com`` while
GL's manual-transaction endpoint is called via ``example.com`` — a
different subdomain. Cookies are domain-scoped, so whether the dashboard's
cookie is honored by GL depends on how its ``Domain`` attribute is set on the
gateway side. This has **not** been confirmed against live UAT yet — run the
``gl_incoming_transactions`` suite and check whether GL still returns 401/403
with the derived cookie; if so, the manual YAML fallback is the one to fill in.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from tests.api.client import ApiClient
from tests.config.settings import REPO_ROOT, Settings
from tests.services.auth import login_to_dashboard

_PLACEHOLDER = "CHANGE_ME"


class GlAdminSession(BaseModel):
    """Typed view of ``secrets/uat_gl_admin_session.yaml`` (manual fallback)."""

    model_config = ConfigDict(extra="ignore")

    cookie: str = _PLACEHOLDER

    def require_configured(self) -> str:
        """Return the live Cookie, or skip when it is missing/still ``CHANGE_ME``."""
        if not self.cookie or self.cookie == _PLACEHOLDER:
            pytest.skip(
                "GL admin session Cookie unavailable — dashboard login returned no "
                "Cookie and secrets/uat_gl_admin_session.yaml is missing/CHANGE_ME. "
                "Copy secrets/uat_gl_admin_session.example.yaml to "
                "secrets/uat_gl_admin_session.yaml and paste a live Cookie."
            )
        return self.cookie


def load_gl_admin_session(settings: Settings) -> GlAdminSession:
    """Load the manual-fallback GL admin session; placeholder if the file is absent."""
    path = Path(settings.gl_admin_session_secrets_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file():
        return GlAdminSession()
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return GlAdminSession()
    return GlAdminSession.model_validate(raw)


def cookie_from_dashboard_login(dashboard_client: ApiClient, settings: Settings) -> str:
    """Log into the management-console dashboard; return any Cookie it set.

    Reuses the staff login credentials already in ``config/environment-stage.yaml``
    (``DASHBOARD_USERNAME``/``DASHBOARD_PASSWORD`` — non-secret UAT test values,
    not real staff credentials). Returns ``""`` when the login response carried
    no ``Set-Cookie`` header.
    """
    login_to_dashboard(dashboard_client, settings.dashboard_username, settings.dashboard_password)
    return dashboard_client.cookie_header()


def resolve_gl_admin_cookie(
    dashboard_client: ApiClient,
    settings: Settings,
    manual_session: GlAdminSession,
) -> str:
    """Prefer a cookie derived from dashboard login; fall back to the manual YAML."""
    derived = cookie_from_dashboard_login(dashboard_client, settings)
    if derived:
        return derived
    return manual_session.require_configured()
