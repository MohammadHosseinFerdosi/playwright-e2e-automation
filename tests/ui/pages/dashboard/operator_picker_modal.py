"""Dashboard modal — pick a mobile operator under topup / internet package."""

from __future__ import annotations

from tests.ui.labels.dashboard import DashboardLabels as L
from tests.ui.pages.base_page import BasePage


class DashboardOperatorPickerModal(BasePage):
    """Operator grid after opening topup or internet package."""

    LOCATORS = {
        "dialog": "css=mat-dialog-container",
        "select_operator_hint": (f"css=mat-dialog-container >> text={L.SELECT_OPERATOR}"),
        "close": f"css=mat-dialog-container button:has-text('{L.CLOSE}')",
        "operator_tile": "css=mat-dialog-container button.config-tile",
    }

    def is_open(self) -> bool:
        """Return whether the select-operator hint is currently visible."""
        return self.is_visible(self.LOCATORS["select_operator_hint"], timeout_ms=1_500)

    def should_be_open(self, product_title: str) -> None:
        """Wait until the dialog shows the product title and operator hint.

        Args:
            product_title: Farsi product heading (resolved by the step layer).
        """
        self.expect_visible(self.LOCATORS["dialog"])
        self.expect_visible(f"css=mat-dialog-container >> text={product_title}")
        self.expect_visible(self.LOCATORS["select_operator_hint"])

    def should_list_operators(self, labels: tuple[str, ...]) -> None:
        """Wait until each operator tile label is visible."""
        for label in labels:
            self.expect_visible(f"css=mat-dialog-container button.config-tile:has-text('{label}')")

    def open_operator(self, label: str) -> None:
        """Click an operator tile by its Farsi label."""
        self.click_when_visible(f"css=mat-dialog-container button.config-tile:has-text('{label}')")

    def close(self) -> None:
        """Close the dialog and wait until it is hidden."""
        self.click_when_visible(self.LOCATORS["close"])
        self.resolve(self.LOCATORS["dialog"]).first.wait_for(
            state="hidden", timeout=self.default_timeout_ms
        )
