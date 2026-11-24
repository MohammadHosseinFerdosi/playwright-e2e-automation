"""Bill confirm / pay page after choosing a payable period.

Route: ``/bill/confirm?ticket=...`` — assert bill identity + amount only.
"""

from __future__ import annotations

from tests.ui.labels.app import AppLabels as L
from tests.ui.pages.base_page import BasePage


class BillConfirmPage(BasePage):
    """Bill payment confirm — bill id / pay id / amount landmarks."""

    PATH = "/bill/confirm"

    LOCATORS = {
        "page_header": f"xpath=//*[normalize-space()='{L.BILL_PAYMENT}']",
        "bill_type": (f"xpath=//*[contains(normalize-space(.), '{L.LANDLINE_BILL}')]"),
        "bill_id_label": (f"xpath=//*[contains(normalize-space(.), '{L.BILL_ID}')]"),
        "pay_id_label": (f"xpath=//*[contains(normalize-space(.), '{L.PAY_ID}')]"),
        "amount_label": (f"xpath=//*[contains(normalize-space(.), '{L.PAYMENT_AMOUNT}')]"),
        "rial_amount": (f"xpath=//*[contains(normalize-space(.), '{L.RIAL}')]"),
    }

    def current_url(self) -> str:
        """Return the browser URL."""
        return self.page.url

    def page_title(self) -> str:
        """Return the document title."""
        return self.page.title()

    def should_be_on_confirm(self, timeout_ms: int | None = None) -> None:
        """Wait until confirm route loads and bill identity chrome is visible."""
        timeout = timeout_ms if timeout_ms is not None else self.default_timeout_ms
        self.page.wait_for_url(f"**{self.PATH}**", timeout=timeout)
        if self.is_visible(self.LOCATORS["bill_id_label"], timeout_ms=10_000):
            return
        self.expect_visible(self.LOCATORS["page_header"], timeout_ms=10_000)

    def is_bill_identity_visible(self) -> bool:
        """Return whether bill-id and pay-id labels are both visible."""
        return self.is_visible(
            self.LOCATORS["bill_id_label"], timeout_ms=3_000
        ) and self.is_visible(self.LOCATORS["pay_id_label"], timeout_ms=2_000)

    def is_payment_amount_visible(self) -> bool:
        """Return whether payment amount (or at least a rial amount) is visible."""
        if self.is_visible(self.LOCATORS["amount_label"], timeout_ms=3_000):
            return self.is_visible(self.LOCATORS["rial_amount"], timeout_ms=2_000)
        return self.is_visible(self.LOCATORS["rial_amount"], timeout_ms=2_000)
