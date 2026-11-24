"""Hub (services) page — port of ``src/pages/app/hub.resource``."""

from __future__ import annotations

from enum import Enum

from playwright.sync_api import Page

from tests.ui.auth import dismiss_login_popup_if_present
from tests.ui.labels.app import AppLabels as L
from tests.ui.pages.base_page import BasePage


class HubDestination(str, Enum):
    """Named hub tiles / bottom-nav targets for ``navigate_to``."""

    WALLET_MANAGEMENT = "wallet-management"
    TOP_UP = "top_up"
    INTERNET_PACKAGE = "internet_package"
    C2C = "C2C"
    BILL = "bill"
    DRIVING_FINE = "driving_fine"
    TOLL = "toll"
    TAXI = "taxi"
    CHARITY = "charity"
    QR_SCANNER = "qr"
    PAY = "transactions"
    WEALTH_SILVER = "wealth_silver"  # verified against UAT — bottom-nav "سرمایه" tab


class HubPage(BasePage):
    """Customer hub — service tiles and bottom navigation."""

    PATH = "/hub"

    LOCATORS = {
        "wallet_management": f"xpath=//div[contains(text(),'{L.WALLET}')]",
        "welcome_to_new_app": (
            "xpath=//button[@class='bt-1 mode-form ngx-button size-large style-fill']"
        ),
        "top_up": f"xpath=//div[*[contains(text(),'{L.BUY_TOP_UP}')]]",
        "internet_package": (f"xpath=//div[*[contains(text(),'{L.INTERNET_PACKAGE}')]]"),
        "c2c": f"xpath=//div[*[contains(text(),'{L.CARD_TO_CARD}')]]",
        "bill": f"xpath=//div[*[contains(text(),'{L.BILL_PAYMENT}')]]",
        # Live UAT hub tile (services preview) — preferred over text match.
        "bill_tracker": '[data-tracker="casm-services-preview-div-receipt-bill"]',
        "driving_fine": (f"xpath=//div[*[contains(text(),'{L.DRIVING_FINE_INQUIRY}')]]"),
        "toll": f"xpath=//div[*[contains(text(),'{L.ROAD_TOLL}')]]",
        "taxi": f"xpath=//div[*[contains(text(),'{L.TAXI}')]]",
        "charity": f"xpath=//div[*[contains(text(),'{L.CHARITY}')]]",
        "qr_scanner": f"xpath=//div[*[contains(text(),'{L.BARCODE_SCANNER}')]]",
        "home": "xpath=//i[@class='icon icon-home-bold']",
        "hub_tab": (
            "xpath=//div[contains(@class, 'bottom-navigation') or "
            "contains(@class, 'bottom-navigation-items-item')]"
            f"//*[normalize-space()='{L.SERVICES}']"
        ),
        "all_services": f"xpath=//*[normalize-space()='{L.ALL_SERVICES}']",
        "stores": "xpath=//i[contains(@class,'icon-bag')]",
        "pay": (
            "xpath=//div[contains(@class, 'bottom-navigation-items-item-title') "
            f"and contains(text(), '{L.PAY}')]"
        ),
        "profile": "xpath=//i[contains(@class,'icon-person')]",
        # Verified against live UAT: same bottom-navigation-tab shape as "pay" above.
        "wealth_silver": (
            "xpath=//div[contains(@class, 'bottom-navigation-items-item-title') "
            f"and contains(text(), '{L.WEALTH_TILE}')]"
        ),
    }

    def __init__(
        self,
        page: Page,
        base_url: str,
        hub_path: str = "/hub",
        default_timeout_ms: int = 20_000,
    ) -> None:
        """Bind Playwright page; override hub path from settings when provided."""
        super().__init__(page, base_url, default_timeout_ms=default_timeout_ms)
        self.PATH = hub_path if hub_path.startswith("/") else f"/{hub_path}"

    def open(self) -> None:
        """Navigate to the hub and wait until chrome is visible."""
        self.goto(self.PATH)
        self.should_be_on_hub()

    def current_url(self) -> str:
        """Return the browser URL."""
        return self.page.url

    def page_title(self) -> str:
        """Return the document title."""
        return self.page.title()

    def is_wealth_tab_visible(self, timeout_ms: int = 5_000) -> bool:
        """True when the Wealth ("سرمایه") bottom-nav tab is visible (non-throwing)."""
        return self.is_visible(self.LOCATORS["wealth_silver"], timeout_ms=timeout_ms)

    def is_hub_chrome_visible(self) -> bool:
        """True when any stable hub landmark is on screen (non-throwing)."""
        if self.is_visible(self.LOCATORS["bill_tracker"], timeout_ms=2_000):
            return True
        if self.is_visible(self.LOCATORS["bill"], timeout_ms=1_000):
            return True
        if self.is_visible(self.LOCATORS["all_services"], timeout_ms=1_000):
            return True
        return self.is_visible(self.LOCATORS["hub_tab"], timeout_ms=1_000)

    def should_be_on_hub(self) -> None:
        """Wait until hub path is in the URL and hub chrome is visible."""
        self.wait_until_url_contains(self.PATH)
        # Prefer bill tile (stable for TCI path); fall back to All Services / Services tab.
        if self.is_visible(self.LOCATORS["bill_tracker"], timeout_ms=15_000):
            return
        if self.is_visible(self.LOCATORS["bill"], timeout_ms=5_000):
            return
        if self.is_visible(self.LOCATORS["all_services"], timeout_ms=5_000):
            return
        self.expect_visible(self.LOCATORS["hub_tab"], timeout_ms=10_000)

    def back_to_hub(self) -> None:
        """Tap the Services bottom-nav item and wait for hub chrome."""
        self.click_when_visible(self.LOCATORS["hub_tab"])
        self.should_be_on_hub()

    def navigate_to(self, destination: HubDestination) -> None:
        """Open a hub tile / bottom-nav target by destination enum."""
        if not self.url_contains(self.PATH):
            self.back_to_hub()
        key_map = {
            HubDestination.WALLET_MANAGEMENT: "wallet_management",
            HubDestination.TOP_UP: "top_up",
            HubDestination.INTERNET_PACKAGE: "internet_package",
            HubDestination.C2C: "c2c",
            HubDestination.BILL: "bill",
            HubDestination.DRIVING_FINE: "driving_fine",
            HubDestination.TOLL: "toll",
            HubDestination.TAXI: "taxi",
            HubDestination.CHARITY: "charity",
            HubDestination.QR_SCANNER: "qr_scanner",
            HubDestination.PAY: "pay",
            HubDestination.WEALTH_SILVER: "wealth_silver",
        }
        locator_key = key_map[destination]
        self.click_when_visible(self.LOCATORS[locator_key])

    def open_bill_payment(self) -> None:
        """Open bill payment from the hub (tracker first, text fallback)."""
        if not self.url_contains(self.PATH):
            self.back_to_hub()
        # Late hub notice can land after auth dismiss — clear overlay before click.
        dismiss_login_popup_if_present(self.page)
        if self.is_visible(self.LOCATORS["bill_tracker"], timeout_ms=8_000):
            self.click_when_visible(self.LOCATORS["bill_tracker"])
            return
        self.navigate_to(HubDestination.BILL)
