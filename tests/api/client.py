"""HTTP client — port of Robot session helpers.

One ``ApiClient`` instance = one Robot "session": one reusable ``httpx.Client``,
never a per-call session and never a module-level singleton (see
``.cursor/rules/pytest-architecture.mdc``). Always constructed via a pytest fixture.
"""

import json
import logging
from enum import Enum
from types import TracebackType
from typing import Any

import httpx

from tests.config.settings import Settings
from tests.services.assert_report import attach_http_exchange

logger = logging.getLogger(__name__)


def _decode_http_body(content: bytes) -> Any:
    """Decode a request body as JSON when possible, otherwise UTF-8 text."""
    if not content:
        return None
    text = content.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


class ApiSide(str, Enum):
    """Port of ``${api_call_side}``.

    Only the sides locked in target-framework.md are supported so far — add a new
    member the moment a real endpoint needs it.
    """

    APP = "app"
    MICROSERVICE = "microservice"
    DASHBOARD = "dashboard"
    GENERAL = "general"


class ApiClient:
    """Port of ``Create A Session``. Holds one ``httpx.Client`` for its lifetime."""

    def __init__(
        self,
        settings: Settings,
        side: ApiSide,
        auth_header: str | None = None,
    ) -> None:
        self._settings = settings
        self._side = side
        self._auth_header = auth_header
        self._client = httpx.Client(
            base_url=self._build_base_url(),
            headers=self._build_headers(),
            timeout=settings.session_default_timeout,
            verify=settings.session_default_verify,
        )

    @property
    def side(self) -> ApiSide:
        """Which ``api_call_side`` this client was built for.

        Endpoint functions branch on this the same way Robot keywords branch on
        ``${api_call_side}`` (e.g. adding a microservice-specific path prefix).
        """
        return self._side

    def cookie_header(self) -> str:
        """Serialize cookies captured from ``Set-Cookie`` response headers so far.

        ``httpx.Client`` keeps a cookie jar automatically across requests made
        on the same instance — this just renders it as a ``name=value; ...``
        string for endpoints (like GL's admin gateway) that expect a literal
        ``Cookie`` header rather than relying on httpx to resend it.
        """
        return "; ".join(f"{name}={value}" for name, value in self._client.cookies.items())

    def _build_base_url(self) -> str:
        """Port of ``Path Builder``."""
        if self._side is ApiSide.MICROSERVICE:
            return self._settings.microservice_base_url
        if self._side is ApiSide.APP:
            return self._settings.app_base_url + self._settings.gateway_path
        if self._side is ApiSide.DASHBOARD:
            return self._settings.dashboard_base_url + self._settings.gateway_path
        if self._side is ApiSide.GENERAL:
            return self._settings.general_base_url + self._settings.gateway_path
        raise ValueError(f"Unsupported api_call_side: {self._side!r}")

    def _build_headers(self) -> dict[str, str]:
        """Port of ``Session Header Builder``.

        Microservice calls never carry the Authorization header, matching the
        Robot IF branch.
        """
        if self._side is ApiSide.MICROSERVICE or not self._auth_header:
            return {}
        return {"Authorization": self._auth_header}

    def ms_path(self, path: str, prefix: str) -> str:
        """Prefix ``path`` when this client is on the microservice side."""
        if self._side is ApiSide.MICROSERVICE:
            return prefix + path
        return path

    def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Send GET; return ``{status_code, body}``."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Send POST; return ``{status_code, body}``."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Send PUT; return ``{status_code, body}``."""
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Send PATCH; return ``{status_code, body}``."""
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Send DELETE; return ``{status_code, body}``."""
        return self._request("DELETE", path, **kwargs)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._client.request(method, path, **kwargs)
        body: Any = None
        if response.content:
            try:
                body = response.json()
            except ValueError:
                # Gateway/UAT sometimes returns empty or non-JSON error pages;
                # keep status_code usable for callers/teardown instead of crashing.
                body = {"_raw": response.text}
        self._attach_exchange(response, body)
        return {"status_code": response.status_code, "body": body}

    def _attach_exchange(self, response: httpx.Response, response_body: Any) -> None:
        try:
            request = response.request
            attach_http_exchange(
                method=str(request.method),
                url=str(request.url),
                request_headers={str(key): str(value) for key, value in request.headers.items()},
                request_body=_decode_http_body(request.content),
                status_code=response.status_code,
                response_headers={str(key): str(value) for key, value in response.headers.items()},
                response_body=response_body,
            )
        except Exception:
            logger.debug("Allure HTTP attach failed", exc_info=True)

    def close(self) -> None:
        """Port of ``Delete A Session``."""
        self._client.close()

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
