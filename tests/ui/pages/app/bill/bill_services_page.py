"""Bill type picker after hub → bill payment (Playwright POM)."""

from __future__ import annotations

from tests.api.bill_mng.bill_types import BillType
from tests.ui.labels.app import AppLabels as L
from tests.ui.pages.base_page import BasePage


class BillServicesPage(BasePage):
    """Bill services landing — choose utility type from the bill grid."""

    PATH = "/bill"
    LANDLINE_PATH = BillType.TELEPHONE.identifier_path

    LOCATORS = {
        "page_header": (
            f"xpath=//*[normalize-space()='{L.BILL_PAYMENT}' or "
            f"contains(normalize-space(.), '{L.BILL_PAYMENT}')]"
        ),
        "choose_type_hint": (
            f"xpath=//*[contains(normalize-space(.), '{L.CHOOSE_BILL_TYPE_HINT}')]"
        ),
        # Prefer the clickable tile chrome (same pattern as hub service tiles).
        "telecom_tile": f"css=div.framed-icon-wrapper:has-text('{L.TELECOM}')",
        "telecom_label": f"xpath=//*[normalize-space()='{L.TELECOM}']",
        "landline_tile": f"css=div.framed-icon-wrapper:has-text('{L.LANDLINE}')",
        "landline_label": f"xpath=//*[normalize-space()='{L.LANDLINE}']",
        "page_title_bill": (
            f"xpath=//*[contains(text(),'{L.BILL_PAYMENT}') or contains(text(),'{L.BILL}')]"
        ),
    }

    def current_url(self) -> str:
        """Return the browser URL."""
        return self.page.url

    def page_title(self) -> str:
        """Return the document title."""
        return self.page.title()

    def is_bill_chrome_visible(self) -> bool:
        """True when bill landing landmarks are on screen (non-throwing)."""
        if self.is_visible(self.LOCATORS["telecom_tile"], timeout_ms=2_000):
            return True
        if self.is_visible(self.LOCATORS["telecom_label"], timeout_ms=1_000):
            return True
        if self.is_visible(self.LOCATORS["choose_type_hint"], timeout_ms=1_000):
            return True
        return self.is_visible(self.LOCATORS["page_header"], timeout_ms=1_000)

    def should_be_on_bill_services(self) -> None:
        """Wait until /bill is in the URL and bill chrome is visible."""
        self.wait_until_url_contains(self.PATH)
        if self.is_visible(self.LOCATORS["telecom_tile"], timeout_ms=10_000):
            return
        if self.is_visible(self.LOCATORS["telecom_label"], timeout_ms=5_000):
            return
        if self.is_visible(self.LOCATORS["choose_type_hint"], timeout_ms=5_000):
            return
        if self.is_visible(self.LOCATORS["page_header"], timeout_ms=5_000):
            return
        self.expect_visible(self.LOCATORS["page_title_bill"], timeout_ms=10_000)

    def should_be_visible(self) -> None:
        """Backward-compatible alias for bill services landing wait."""
        self.should_be_on_bill_services()

    def open_landline_telephone(self) -> None:
        """Open TCI / landline inquiry from the bill-type grid."""
        if self.is_visible(self.LOCATORS["telecom_tile"], timeout_ms=5_000):
            self.click_when_visible(self.LOCATORS["telecom_tile"])
        elif self.is_visible(self.LOCATORS["landline_tile"], timeout_ms=2_000):
            self.click_when_visible(self.LOCATORS["landline_tile"])
        else:
            self._click_bill_type_label(L.TELECOM, fallback_label=L.LANDLINE)
        self.wait_until_url_contains(self.LANDLINE_PATH)

    def _click_bill_type_label(self, label: str, *, fallback_label: str) -> None:
        """Click the nearest interactive ancestor of an exact bill-type label."""
        for text in (label, fallback_label):
            target = self.page.get_by_text(text, exact=True).first
            if not self.is_visible(target, timeout_ms=2_000):
                continue
            clickable = target.locator(
                "xpath=ancestor::div[contains(@class,'framed-icon-wrapper') or "
                "contains(@class,'cursor-pointer') or contains(@class,'framed-icon') or "
                "@role='button'][1]"
            )
            if clickable.count():
                clickable.first.click(timeout=self.default_timeout_ms)
                return
            target.click(timeout=self.default_timeout_ms)
            return
        raise TimeoutError(f"Bill type tile not found for labels {label!r} / {fallback_label!r}")
