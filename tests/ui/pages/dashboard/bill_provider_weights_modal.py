"""Dashboard modal — per-type inquiry provider weight distribution."""

from __future__ import annotations

from playwright.sync_api import Locator

from tests.ui.labels.dashboard import DashboardLabels as L
from tests.ui.pages.dashboard.provider_weights_modal import DashboardProviderWeightsModal


class DashboardBillProviderWeightsModal(DashboardProviderWeightsModal):
    """Bill-inquiry weight dialog with per-provider field helpers."""

    LOCATORS = {
        **DashboardProviderWeightsModal.LOCATORS,
        "finnotech": f"css=mat-dialog-container >> text={L.FINNOTECH}",
        "ghabzino": f"css=mat-dialog-container >> text={L.GHABZINO}",
        "tci": f"css=mat-dialog-container >> text={L.TCI}",
        "weight_sliders": "css=mat-dialog-container input.slider[type='range']",
    }

    def _weight_field_for_provider(self, provider_label: str) -> Locator:
        tile = self.page.locator(
            "css=mat-dialog-container "
            f">> xpath=.//*[normalize-space()={provider_label!r}]"
            "/ancestor::*[.//input[@type='tel']][1]"
        )
        field = tile.locator("css=input[type='tel']").first
        field.wait_for(state="visible", timeout=self.default_timeout_ms)
        return field

    def weight_for_provider(self, provider_label: str) -> int:
        """Read the weight input associated with a Farsi provider label."""
        raw = self._weight_field_for_provider(provider_label).input_value().strip()
        return int(float(raw)) if raw else 0

    def set_weight_for_provider(self, provider_label: str, value: int) -> None:
        """Set weight by provider label; Tab so Angular recalculates siblings."""
        field = self._weight_field_for_provider(provider_label)
        field.click(click_count=3)
        field.type(str(value), delay=40)
        field.press("Tab")
