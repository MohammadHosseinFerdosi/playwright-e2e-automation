"""Dashboard Super App list — dashboard services entry points."""

from __future__ import annotations

from tests.ui.labels.dashboard import DashboardLabels as L
from tests.ui.pages.base_page import BasePage


class DashboardSuperAppPage(BasePage):
    """Super App management page (``/management-console/super-app``)."""

    PATH = "/management-console/super-app"

    LOCATORS = {
        "super_app_nav": f"css=div.expand-sub-item:has-text('{L.SUPER_APP}')",
        "page_heading": f"css=h1.header__title:has-text('{L.SUPER_APP_LIST}')",
        "platform_services": (f"xpath=//*[normalize-space()='{L.PLATFORM_SERVICES}']"),
        "bill_inquiry": f"css=div.service-item:has-text('{L.BILL_INQUIRY}')",
        "internet_package": (f"css=div.service-item:has-text('{L.INTERNET_PACKAGE}')"),
        "topup": f"css=div.service-item:has-text('{L.TOPUP}')",
        "success_toast": (f"xpath=//*[contains(normalize-space(.), '{L.SUCCESS_TOAST}')]"),
    }

    def open_from_settings(self) -> None:
        """Open Super App from the expanded Settings sidebar."""
        self.click_when_visible(self.LOCATORS["super_app_nav"])

    def should_be_on_super_app(self) -> None:
        """Wait until Super App path and page heading are visible."""
        self.wait_until_url_contains(self.PATH)
        self.expect_visible(self.LOCATORS["page_heading"])

    def should_show_platform_services(self) -> None:
        """Wait until Platform services section and bill inquiry tile show."""
        self.expect_visible(self.LOCATORS["platform_services"])
        self.expect_visible(self.LOCATORS["bill_inquiry"])

    def open_bill_inquiry(self) -> None:
        """Open the bill-inquiry service tile."""
        self.click_when_visible(self.LOCATORS["bill_inquiry"])

    def open_internet_package(self) -> None:
        """Open the internet-package service tile."""
        self.click_when_visible(self.LOCATORS["internet_package"])

    def open_topup(self) -> None:
        """Open the topup service tile."""
        self.click_when_visible(self.LOCATORS["topup"])

    def should_show_success_toast(self) -> None:
        """Wait until the success toast is visible after a confirmation."""
        self.expect_visible(self.LOCATORS["success_toast"])
