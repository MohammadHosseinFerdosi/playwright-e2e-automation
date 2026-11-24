"""Browser session lifecycle — port of ``src/services/frontend/playwright/browser-service.resource``.

Class + fixture only (xdist-safe). Never keep a module-level Playwright singleton.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from tests.config.settings import Settings


@dataclass(frozen=True)
class Viewport:
    """Pixel dimensions for a Playwright browser context."""

    width: int
    height: int


class BrowserSession:
    """Owns one Playwright browser/context/page for a single test."""

    def __init__(self, settings: Settings) -> None:
        """Create an unstarted session bound to UI settings."""
        self._settings = settings
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page:
        """Return the live page, or raise if ``start()`` has not run."""
        if self._page is None:
            raise RuntimeError("BrowserSession has no page — call start() first")
        return self._page

    @property
    def context(self) -> BrowserContext:
        """Return the live context, or raise if ``start()`` has not run."""
        if self._context is None:
            raise RuntimeError("BrowserSession has no context — call start() first")
        return self._context

    def start(
        self,
        url: str | None = None,
        *,
        viewport: Viewport | None = None,
        context_options: dict[str, Any] | None = None,
        launch_args: list[str] | None = None,
    ) -> Page:
        """Launch browser/context/page, start tracing, and navigate to ``url``."""
        if self._page is not None:
            return self._page

        engine, headless = self._resolve_browser_alias(self._settings.ui_browser_alias)
        self._playwright = sync_playwright().start()
        browser_type = getattr(self._playwright, engine)
        launch_kwargs: dict[str, Any] = {"headless": headless}
        if launch_args:
            launch_kwargs["args"] = launch_args
        if self._settings.ui_slow_mo_ms:
            launch_kwargs["slow_mo"] = self._settings.ui_slow_mo_ms
        if engine == "chromium":
            # Bundled Chromium's CDN download is unreachable from some networks
            # (geo-blocked) — launch the system-installed Google Chrome instead.
            launch_kwargs["channel"] = "chrome"
        self._browser = browser_type.launch(**launch_kwargs)
        browser = self._browser
        if browser is None:
            raise RuntimeError("Playwright browser failed to launch")

        vp = viewport or self._resolve_viewport(self._settings.ui_view_mode)
        co: dict[str, Any] = dict(context_options or {})
        co.setdefault("viewport", {"width": vp.width, "height": vp.height})
        co.setdefault("locale", "fa-IR")
        self._context = browser.new_context(**co)
        context = self._context
        if context is None:
            raise RuntimeError("Playwright browser context failed to create")
        context.set_default_timeout(self._settings.ui_default_timeout_ms)
        context.set_default_navigation_timeout(self._settings.ui_navigation_timeout_ms)
        # Always record — cheap relative to a debugging session with no repro info.
        # Caller decides whether to keep (save_trace) or throw away (discard_trace)
        # once the test outcome is known, via the browser_session fixture teardown.
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        self._page = context.new_page()

        target = url or self._settings.app_base_url
        self._page.goto(target, wait_until="domcontentloaded")
        return self._page

    def capture_screenshot_bytes(self, *, full_page: bool = True) -> bytes | None:
        """PNG bytes of the current page, or ``None`` if there's no live page to shoot."""
        if self._page is None:
            return None
        try:
            if self._page.is_closed():
                return None
            return self._page.screenshot(full_page=full_page)
        except Exception:
            # Page may be mid-crash after the failure that triggered this capture —
            # a failed screenshot should never mask the original test failure.
            return None

    def save_trace(self, path: str | Path) -> Path | None:
        """Stop tracing and write the trace to ``path``. Call before ``close()``."""
        if self._context is None:
            return None
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        self._context.tracing.stop(path=str(out))
        return out

    def discard_trace(self) -> None:
        """Stop tracing without saving — for tests that passed."""
        if self._context is not None:
            self._context.tracing.stop()

    def close(self) -> None:
        """Close context, browser, and Playwright driver if started."""
        if self._context is not None:
            self._context.close()
            self._context = None
            self._page = None
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def _resolve_viewport(self, view_mode: str) -> Viewport:
        """view_mode 'mobile' -> phone-sized viewport; anything else (default 'desktop') -> desktop."""
        if view_mode.strip().lower() == "mobile":
            return Viewport(
                width=self._settings.ui_mobile_viewport_width,
                height=self._settings.ui_mobile_viewport_height,
            )
        return Viewport(
            width=self._settings.ui_viewport_width,
            height=self._settings.ui_viewport_height,
        )

    @staticmethod
    def _resolve_browser_alias(alias: str) -> tuple[str, bool]:
        """Maps CHROME|HEADLESSCHROME|… → (engine, headless)."""
        normalized = alias.upper().replace("_", "").replace("-", "")
        mapping = {
            "CHROME": ("chromium", False),
            "HEADLESSCHROME": ("chromium", True),
            "FIREFOX": ("firefox", False),
            "HEADLESSFIREFOX": ("firefox", True),
            "EDGE": ("chromium", False),
            "HEADLESSEDGE": ("chromium", True),
            "CHROMIUM": ("chromium", True),
            "WEBKIT": ("webkit", True),
        }
        if normalized not in mapping:
            raise ValueError(f"Unsupported browser alias: {alias!r}")
        return mapping[normalized]
