"""Dashboard home — sidebar entry after staff session inject."""

from __future__ import annotations

from tests.ui.labels.dashboard import DashboardLabels as L
from tests.ui.pages.base_page import BasePage


class DashboardHomePage(BasePage):
    """Operational dashboard home (``/management-console/home``)."""

    PATH = "/management-console/home"

    LOCATORS = {
        "settings_nav": (f"css=div.navigation-bar-collapse-item:has-text('{L.SETTINGS}')"),
        "page_heading": (f"xpath=//*[contains(normalize-space(.), '{L.OPERATIONAL_DASHBOARD}')]"),
    }

    def should_be_on_home(self) -> None:
        """Wait until home path and Settings nav are visible."""
        self.wait_until_url_contains(self.PATH)
        self.expect_visible(self.LOCATORS["settings_nav"])

    def open_settings(self) -> None:
        """Expand Settings in the sidebar navigation."""
        self.click_when_visible(self.LOCATORS["settings_nav"])
