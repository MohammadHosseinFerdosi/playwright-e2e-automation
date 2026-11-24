"""Landline (TCI) inquiry UI — form + payment-period sheet.

App route: ``/bill/identifier/{BillType.TELEPHONE}`` (= ``/bill/identifier/7``).

Live UAT period rows (``bill-applet-type-picker``):
- payable → ``cursor-pointer`` + price in ``button.style-link`` / ``.button-label``
- without debt → ``is-disabled`` + without-debt label
"""

from __future__ import annotations

from enum import Enum

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from tests.api.bill_mng.bill_types import BillType
from tests.services.persian_digits import phone_display_variants
from tests.ui.labels.app import AppLabels as L
from tests.ui.pages.base_page import BasePage


class PaymentPeriod(str, Enum):
    """Payment period options on the landline debt sheet."""

    MID = "mid"
    FINAL = "final"


class PeriodDebtState(str, Enum):
    """Expected debt state for a mid/final period row."""

    PAYABLE = "payable"
    WITHOUT_DEBT = "without debt"


class LandlineInquiryPage(BasePage):
    """Landline bill inquiry form and payment-period bottom sheet."""

    BILL_TYPE = BillType.TELEPHONE
    PATH = BillType.TELEPHONE.identifier_path

    _PERIOD_LABEL = {
        PaymentPeriod.MID: L.PERIOD_MID,
        PaymentPeriod.FINAL: L.PERIOD_FINAL,
    }

    LOCATORS = {
        "page_header": f"xpath=//*[normalize-space()='{L.LANDLINE_BILL}']",
        "debt_inquiry_tab": f"xpath=//*[normalize-space()='{L.DEBT_INQUIRY}']",
        "phone_label": (f"xpath=//*[contains(normalize-space(.), '{L.LANDLINE_NUMBER}')]"),
        "inquiry_input": (
            'css=ui-form-field[formcontrolname="cellNumber"] input[type="tel"], '
            'input[type="tel"][inputmode="numeric"]'
        ),
        "inquire_button": (f"xpath=//button[contains(normalize-space(.), '{L.SAVE_AND_INQUIRE}')]"),
        "period_sheet": "css=bill-applet-type-picker, .bottom-sheet-container.open",
        "period_sheet_title": (f"xpath=//*[normalize-space()='{L.SELECT_PAYMENT_PERIOD}']"),
    }

    def current_url(self) -> str:
        """Return the browser URL."""
        return self.page.url

    def page_title(self) -> str:
        """Return the document title."""
        return self.page.title()

    def is_inquiry_form_visible(self) -> bool:
        """True when the inquiry form landmarks are on screen (non-throwing)."""
        if self.is_visible(self.LOCATORS["inquiry_input"], timeout_ms=2_000):
            return True
        if self.is_visible(self.LOCATORS["phone_label"], timeout_ms=1_000):
            return True
        return self.is_visible(self.LOCATORS["page_header"], timeout_ms=1_000)

    def should_be_on_landline_inquiry(self) -> None:
        """Wait until landline inquiry route and form chrome are ready."""
        self.wait_until_url_contains(self.PATH)
        if self.is_visible(self.LOCATORS["inquiry_input"], timeout_ms=10_000):
            return
        if self.is_visible(self.LOCATORS["phone_label"], timeout_ms=5_000):
            return
        self.expect_visible(self.LOCATORS["inquire_button"], timeout_ms=10_000)

    def enter_inquiry_id(self, inquiry_id: str) -> None:
        """Fill the landline inquiry phone / id field."""
        self.fill_when_visible(self.LOCATORS["inquiry_input"], inquiry_id)

    def submit_inquiry(self) -> None:
        """Click Save and Inquire when the button is enabled."""
        button = self.resolve(self.LOCATORS["inquire_button"]).first
        expect(button).to_be_enabled(timeout=self.default_timeout_ms)
        button.click(timeout=self.default_timeout_ms)

    def inquire_landline(self, inquiry_id: str) -> None:
        """Fill inquiry id and submit in one step."""
        self.enter_inquiry_id(inquiry_id)
        self.submit_inquiry()

    def wait_for_payment_period_sheet(self, timeout_ms: int = 30_000) -> None:
        """Wait until the payment-period bottom sheet is open."""
        self.expect_visible(self.LOCATORS["period_sheet_title"], timeout_ms=timeout_ms)
        self.expect_visible(self.LOCATORS["period_sheet"], timeout_ms=timeout_ms)

    def is_payment_period_sheet_visible(self) -> bool:
        """Return whether the period sheet title is visible."""
        return self.is_visible(self.LOCATORS["period_sheet_title"], timeout_ms=3_000)

    def _sheet_root(self) -> Locator:
        return self.page.locator("bill-applet-type-picker").first

    def period_label(self, period: PaymentPeriod | str) -> str:
        """Resolve mid/final (enum or English key) to the Farsi row label."""
        key = period if isinstance(period, PaymentPeriod) else PaymentPeriod(period.strip().lower())
        return self._PERIOD_LABEL[key]

    def period_row(self, period: PaymentPeriod | str) -> Locator:
        """Surface row for mid/final inside the type-picker sheet."""
        label = self.period_label(period)
        # Live DOM: div.surface-back.(cursor-pointer|is-disabled) wrapping span period label.
        return (
            self._sheet_root()
            .locator(
                "xpath=.//div[contains(@class,'surface-back')]"
                f"[.//span[normalize-space()='{label}']]"
            )
            .first
        )

    def period_row_text(self, period: PaymentPeriod | str) -> str:
        """Return visible text of the mid/final period row."""
        row = self.period_row(period)
        row.wait_for(state="visible", timeout=self.default_timeout_ms)
        return row.inner_text()

    def period_row_classes(self, period: PaymentPeriod | str) -> str:
        """Return the CSS class attribute of the mid/final period row."""
        row = self.period_row(period)
        row.wait_for(state="visible", timeout=self.default_timeout_ms)
        return row.get_attribute("class") or ""

    def is_period_label_visible(self, period: PaymentPeriod | str) -> bool:
        """Return whether the period label span is visible in the sheet."""
        label = self.period_label(period)
        try:
            self._sheet_root().locator(
                f"xpath=.//span[normalize-space()='{label}']"
            ).first.wait_for(state="visible", timeout=5_000)
            return True
        except PlaywrightTimeoutError:
            return False

    def period_is_clickable(self, period: PaymentPeriod | str) -> bool:
        """Return whether the period row looks enabled for payment."""
        classes = self.period_row_classes(period)
        return "cursor-pointer" in classes and "is-disabled" not in classes

    def period_is_disabled(self, period: PaymentPeriod | str) -> bool:
        """Return whether the period row has the disabled class."""
        return "is-disabled" in self.period_row_classes(period)

    def period_shows_payable(self, period: PaymentPeriod | str) -> bool:
        """Payable: enabled row + rial price (not without-debt)."""
        row = self.period_row(period)
        row.wait_for(state="visible", timeout=self.default_timeout_ms)
        text = row.inner_text()
        price = row.locator("button.style-link .button-label, .button-label, button.style-link")
        has_price = price.filter(has_text=L.RIAL).count() > 0 or (
            L.RIAL in text and L.WITHOUT_DEBT not in text
        )
        return self.period_is_clickable(period) and has_price and L.WITHOUT_DEBT not in text

    def period_shows_without_debt(self, period: PaymentPeriod | str) -> bool:
        """Without debt: disabled row + without-debt label."""
        row = self.period_row(period)
        row.wait_for(state="visible", timeout=self.default_timeout_ms)
        has_label = row.locator(f"xpath=.//span[normalize-space()='{L.WITHOUT_DEBT}']").count() > 0
        return self.period_is_disabled(period) and (has_label or L.WITHOUT_DEBT in row.inner_text())

    def is_phone_line_visible_for(self, inquiry_id: str) -> bool:
        """Return whether the sheet shows the inquired phone (ASCII or Persian digits)."""
        ascii_id, persian_id = phone_display_variants(inquiry_id)
        root = self._sheet_root()
        prefix = L.FOR_NUMBER_PREFIX
        for candidate in (ascii_id, persian_id):
            loc = root.locator(
                "xpath=.//span[contains(normalize-space(.), "
                f"'{prefix} {candidate}') or contains(normalize-space(.), "
                f"'{prefix}{candidate}')]"
            )
            try:
                loc.first.wait_for(state="visible", timeout=2_000)
                return True
            except PlaywrightTimeoutError:
                continue
        return False

    def open_payment_period(self, period: PaymentPeriod | str) -> None:
        """Click a payable period row (price control preferred over the row)."""
        row = self.period_row(period)
        row.wait_for(state="visible", timeout=self.default_timeout_ms)
        if not self.period_is_clickable(period):
            raise AssertionError(
                f"Period {self.period_label(period)!r} is not clickable "
                f"(classes={self.period_row_classes(period)!r})"
            )
        # Prefer the price/action control when present; fall back to the row.
        action = row.locator("button.style-link").first
        if action.count() > 0 and action.is_visible():
            action.click(timeout=self.default_timeout_ms)
            return
        row.click(timeout=self.default_timeout_ms)

    def period_does_not_navigate_to_confirm(
        self, period: PaymentPeriod | str, *, settle_ms: int = 2_000
    ) -> bool:
        """Attempt interaction on a disabled row; confirm must not open."""
        before = self.page.url
        row = self.period_row(period)
        row.click(timeout=self.default_timeout_ms, force=True)
        try:
            self.page.wait_for_url("**/bill/confirm**", timeout=settle_ms)
            return False
        except PlaywrightTimeoutError:
            return "/bill/confirm" not in self.page.url and before.split("?")[0] in self.page.url
