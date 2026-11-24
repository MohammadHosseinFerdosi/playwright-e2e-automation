"""Shared dashboard modal — provider weight distribution (bill inquiry + topup)."""

from __future__ import annotations

from playwright.sync_api import Page

from tests.ui.labels.dashboard import DashboardLabels as L
from tests.ui.pages.base_page import BasePage


class DashboardProviderWeightsModal(BasePage):
    """Service distribution dialog (Confirm enabled only when weights sum to 100)."""

    LOCATORS = {
        "dialog": "css=mat-dialog-container",
        "distribution_heading": (f"css=mat-dialog-container >> text={L.SERVICE_DISTRIBUTION}"),
        "confirm": (f"css=mat-dialog-container button:has-text('{L.CONFIRM_UPDATE}')"),
        "back": f"css=mat-dialog-container button:has-text('{L.BACK}')",
        "weight_inputs": "css=mat-dialog-container input[type='tel']",
    }

    def __init__(
        self,
        page: Page,
        base_url: str,
        default_timeout_ms: int = 20_000,
    ) -> None:
        """Bind Playwright page to the weight-distribution dialog."""
        super().__init__(page, base_url, default_timeout_ms=default_timeout_ms)

    def is_open(self) -> bool:
        """Return whether the distribution heading is currently visible."""
        return self.is_visible(self.LOCATORS["distribution_heading"], timeout_ms=1_500)

    def should_be_open(self, title: str) -> None:
        """Wait until the dialog shows ``title`` and the distribution heading.

        Args:
            title: Farsi dialog heading (resolved by the step layer).
        """
        self.expect_visible(self.LOCATORS["dialog"])
        self.expect_visible(f"css=mat-dialog-container >> text={title}")
        self.expect_visible(self.LOCATORS["distribution_heading"])

    def should_show_providers(self, *provider_labels: str) -> None:
        """Wait until each Farsi provider label is visible in the dialog.

        Args:
            provider_labels: Farsi provider names (resolved by the step layer).
        """
        for label in provider_labels:
            self.expect_visible(f"css=mat-dialog-container >> text={label}")

    def weight_values(self) -> list[int]:
        """Return current weight inputs left-to-right."""
        inputs = self.resolve(self.LOCATORS["weight_inputs"])
        values: list[int] = []
        for i in range(inputs.count()):
            raw = inputs.nth(i).input_value().strip()
            values.append(int(float(raw)) if raw else 0)
        return values

    def set_weight_at(self, index: int, value: int) -> None:
        """Set one weight field; Tab so Angular recalculates sibling weights."""
        inputs = self.resolve(self.LOCATORS["weight_inputs"])
        field = inputs.nth(index)
        field.wait_for(state="visible", timeout=self.default_timeout_ms)
        field.click(click_count=3)
        field.type(str(value), delay=40)
        field.press("Tab")

    def set_weights(self, *values: int) -> None:
        """Set every weight field in order."""
        for index, value in enumerate(values):
            self.set_weight_at(index, value)

    def click_back(self) -> None:
        """Click Back without waiting for the dialog to close."""
        self.click_when_visible(self.LOCATORS["back"])

    def click_confirm(self) -> None:
        """Click Confirm and wait until the dialog is hidden."""
        self.click_when_visible(self.LOCATORS["confirm"])
        self.resolve(self.LOCATORS["dialog"]).first.wait_for(
            state="hidden", timeout=self.default_timeout_ms
        )

    def confirm_is_enabled(self) -> bool:
        """Return whether Confirm is clickable (weights must total 100)."""
        loc = self.resolve(self.LOCATORS["confirm"]).first
        loc.wait_for(state="visible", timeout=self.default_timeout_ms)
        return loc.is_enabled()
