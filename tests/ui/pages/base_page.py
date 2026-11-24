"""Shared Playwright page helpers — every page object inherits from ``BasePage``."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

LocatorLike = str | Locator
WaitUntilState = Literal["commit", "domcontentloaded", "load", "networkidle"]


class BasePage:
    """Port of common waits/clicks from ``src/pages/app/parent.resource``.

    Locators live as class attributes on subclasses. Actions are methods —
    step files must not call raw Playwright selectors.
    """

    PATH: str = ""

    def __init__(self, page: Page, base_url: str, default_timeout_ms: int = 20_000) -> None:
        """Bind a Playwright page to an origin and default interaction timeout."""
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.default_timeout_ms = default_timeout_ms
        self.page.set_default_timeout(default_timeout_ms)

    def absolute_url(self, path: str | None = None) -> str:
        """Build an absolute URL from ``base_url`` and a relative path."""
        relative = path if path is not None else self.PATH
        if not relative:
            return self.base_url
        if relative.startswith("http"):
            return relative
        return f"{self.base_url}/{relative.lstrip('/')}"

    def goto(
        self,
        path: str | None = None,
        *,
        wait_until: WaitUntilState = "domcontentloaded",
    ) -> None:
        """Navigate to ``path`` (or ``PATH``) under ``base_url``."""
        self.page.goto(self.absolute_url(path), wait_until=wait_until)

    def reload(self) -> None:
        """Reload the current page."""
        self.page.reload(wait_until="domcontentloaded")

    def url_contains(self, fragment: str) -> bool:
        """Return whether the current URL contains ``fragment``."""
        return fragment in self.page.url

    def wait_until_url_contains(self, fragment: str, timeout_ms: int | None = None) -> None:
        """Wait until the URL matches Playwright's ``**fragment**`` pattern."""
        timeout = timeout_ms if timeout_ms is not None else self.default_timeout_ms
        self.page.wait_for_url(f"**{fragment}**", timeout=timeout)

    def locator(self, selector: str) -> Locator:
        """Return a Playwright locator for a CSS/xpath selector string."""
        return self.page.locator(selector)

    def resolve(self, target: LocatorLike) -> Locator:
        """Normalize a selector string or locator to a ``Locator``."""
        if isinstance(target, str):
            return self.locator(target)
        return target

    def click_when_visible(self, target: LocatorLike, timeout_ms: int | None = None) -> None:
        """Wait until ``target`` is visible, then click the first match."""
        loc = self.resolve(target)
        timeout = timeout_ms if timeout_ms is not None else self.default_timeout_ms
        loc.first.wait_for(state="visible", timeout=timeout)
        loc.first.click(timeout=timeout)

    def fill_when_visible(
        self, target: LocatorLike, value: str, timeout_ms: int | None = None
    ) -> None:
        """Wait until ``target`` is visible, then fill it with ``value``."""
        loc = self.resolve(target)
        timeout = timeout_ms if timeout_ms is not None else self.default_timeout_ms
        loc.first.wait_for(state="visible", timeout=timeout)
        loc.first.fill(value, timeout=timeout)

    def type_when_visible(
        self,
        target: LocatorLike,
        value: str,
        *,
        delay_ms: float = 100,
        timeout_ms: int | None = None,
    ) -> None:
        """Wait until ``target`` is visible, focus it, then type ``value``."""
        loc = self.resolve(target)
        timeout = timeout_ms if timeout_ms is not None else self.default_timeout_ms
        loc.first.wait_for(state="visible", timeout=timeout)
        loc.first.click(timeout=timeout)
        loc.first.type(value, delay=delay_ms, timeout=timeout)

    def is_visible(self, target: LocatorLike, timeout_ms: int = 2_000) -> bool:
        """Return whether ``target`` becomes visible within ``timeout_ms``."""
        try:
            self.resolve(target).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    def expect_visible(self, target: LocatorLike, timeout_ms: int | None = None) -> None:
        """Wait until ``target`` is visible or raise on timeout."""
        timeout = timeout_ms if timeout_ms is not None else self.default_timeout_ms
        self.resolve(target).first.wait_for(state="visible", timeout=timeout)

    def screenshot(self, path: str | Path, *, full_page: bool = True) -> Path:
        """Capture a PNG screenshot to ``path`` and return that path."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(out), full_page=full_page)
        return out
