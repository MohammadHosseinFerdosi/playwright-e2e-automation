"""Dashboard modal — pick a utility bill type under bill inquiry."""

from __future__ import annotations

from tests.ui.labels.dashboard import BILL_TYPE_TILES
from tests.ui.labels.dashboard import DashboardLabels as L
from tests.ui.pages.base_page import BasePage


class DashboardBillInquiryModal(BasePage):
    """Bill-type picker dialog on the Super App page."""

    LOCATORS = {
        "dialog": "css=mat-dialog-container",
        "title": (f"css=mat-dialog-container .item-title:has-text('{L.BILL_INQUIRY}')"),
        "select_type_hint": (f"css=mat-dialog-container >> text={L.SELECT_BILL_TYPE}"),
        "bill_type_tile": "css=mat-dialog-container button.config-tile",
        "close": f"css=mat-dialog-container button:has-text('{L.CLOSE}')",
        "electricity": (f"css=mat-dialog-container button.config-tile:has-text('{L.ELECTRICITY}')"),
        "landline": (f"css=mat-dialog-container button.config-tile:has-text('{L.LANDLINE}')"),
    }

    def is_open(self) -> bool:
        """Return whether the bill-inquiry title is currently visible."""
        return self.is_visible(self.LOCATORS["title"], timeout_ms=1_500)

    def should_be_open(self) -> None:
        """Wait until the bill-type picker dialog chrome is visible."""
        self.expect_visible(self.LOCATORS["dialog"])
        self.expect_visible(self.LOCATORS["title"])
        self.expect_visible(self.LOCATORS["select_type_hint"])

    def should_list_bill_types(self) -> None:
        """Wait until every known bill-type tile label is visible."""
        for label in BILL_TYPE_TILES:
            self.expect_visible(f"css=mat-dialog-container button.config-tile:has-text('{label}')")

    def close(self) -> None:
        """Close the dialog and wait until it is hidden."""
        self.click_when_visible(self.LOCATORS["close"])
        self.resolve(self.LOCATORS["dialog"]).first.wait_for(
            state="hidden", timeout=self.default_timeout_ms
        )

    def open_bill_type(self, label: str) -> None:
        """Click a bill-type tile by its Farsi label."""
        self.click_when_visible(f"css=mat-dialog-container button.config-tile:has-text('{label}')")

    def open_electricity(self) -> None:
        """Open the electricity bill-type weight dialog."""
        self.open_bill_type(L.ELECTRICITY)

    def open_landline(self) -> None:
        """Open the landline bill-type weight dialog."""
        self.open_bill_type(L.LANDLINE)
