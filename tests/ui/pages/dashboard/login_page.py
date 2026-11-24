"""Dashboard login — port of APP Login To DASHBOARD Handler locators."""

from __future__ import annotations

from playwright.sync_api import Page

from tests.ui.labels.dashboard import DashboardLabels as L
from tests.ui.pages.base_page import BasePage


class DashboardLoginPage(BasePage):
    """Staff login form for the management console."""

    LOCATORS = {
        "user_id": 'css=input[formcontrolname="userId"]',
        "password": 'css=input[formcontrolname="password"]',
        "submit": (f'css=button.login-form__form-submit:has-text("{L.LOGIN_SUBMIT}")'),
    }

    def __init__(
        self,
        page: Page,
        base_url: str,
        login_url: str,
        default_timeout_ms: int = 20_000,
    ) -> None:
        """Bind Playwright page and absolute dashboard login URL."""
        super().__init__(page, base_url, default_timeout_ms=default_timeout_ms)
        self._login_url = login_url

    def open(self) -> None:
        """Navigate to the dashboard login URL."""
        self.page.goto(self._login_url, wait_until="domcontentloaded")

    def login(self, username: str, password: str) -> None:
        """Fill credentials and submit the login form."""
        if "/management-console/login" not in self.page.url:
            self.open()
        if "/management-console/login" not in self.page.url:
            raise RuntimeError(f"Expected dashboard login URL, got {self.page.url!r}")
        self.type_when_visible(self.LOCATORS["user_id"], username)
        self.type_when_visible(self.LOCATORS["password"], password)
        self.click_when_visible(self.LOCATORS["submit"])
