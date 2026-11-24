"""Wealth purchase/sale receipt screen (Playwright POM).

Verified against live UAT — the same route serves both flows, distinguished by a
query param and status text:

- Buy, reached back from the external gateway (``IpgGatewayPage``): cancelling
  lands here with status "عملیات ناموفق" (operation failed).
- Sell, reached directly (no external gateway involved): lands here with status
  "عملیات در انتظار" (pending settlement, up to 1 business day) and a
  ``walletAction=cashOut`` query param — Platform wallet withdrawals settle
  asynchronously, so "pending" is the real terminal state for a sale here, not
  an intermediate one to wait past.
"""

from __future__ import annotations

from tests.ui.labels.app import AppLabels as L
from tests.ui.pages.base_page import BasePage


class ReceiptPage(BasePage):
    """Wealth product purchase/sale receipt."""

    # Verified — reached from the external gateway (buy) or directly (sell); real
    # URL also carries ?trackingCode=... (and ?walletAction=cashOut for a sale),
    # but those values are dynamic/flow-specific.
    PATH = "/mini-app/wealth/receipt"

    LOCATORS = {
        "failed_status": f"xpath=//*[normalize-space()='{L.OPERATION_FAILED}']",
        "pending_status": f"xpath=//*[normalize-space()='{L.OPERATION_PENDING}']",
        "description": f"xpath=//*[normalize-space()='{L.SILVER_PURCHASE_DESCRIPTION}']",
    }

    def should_be_on_receipt(self) -> None:
        """Wait until the receipt route is reached."""
        self.wait_until_url_contains(self.PATH)

    def is_on_receipt(self) -> bool:
        """True when the browser URL is the receipt screen (non-throwing)."""
        return self.url_contains(self.PATH)

    def is_operation_failed(self) -> bool:
        """True when the receipt shows the "عملیات ناموفق" (failed) status (non-throwing)."""
        return self.is_visible(self.LOCATORS["failed_status"])

    def is_operation_pending(self) -> bool:
        """True when the receipt shows the "عملیات در انتظار" (pending) status (non-throwing)."""
        return self.is_visible(self.LOCATORS["pending_status"])

    def is_purchase_description_shown(self) -> bool:
        """True when the receipt shows the silver-purchase line item (non-throwing)."""
        return self.is_visible(self.LOCATORS["description"])
