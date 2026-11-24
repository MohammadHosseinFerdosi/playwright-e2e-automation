"""External Parsian/Shaparak bank payment gateway (Playwright POM).

Verified against live UAT: Platform's silver purchase "quick-payment" screen redirects
off-origin to a real bank IPG UI (``pec.shaparak.ir``) for its default "درگاه پرداخت
اینترنتی" (online gateway) method — Platform's own internal ``/ipg-mock`` is not
involved in this flow, and no successful-payment test credentials (CVV2, dynamic
password) are available here, so this page only models the cancel path.

Not a normal in-app page: it lives on a different origin reached only by redirect
(never navigated to directly), so ``base_url``/``PATH``/``goto()`` are unused —
only the inherited locator/click helpers matter here.
"""

from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from tests.ui.pages.base_page import BasePage


class IpgGatewayPage(BasePage):
    """External bank gateway screen reached from the wealth quick-payment screen."""

    # Matches ReceiptPage.PATH — duplicated rather than imported to keep this page
    # object self-contained (it has no other reason to depend on ReceiptPage).
    RECEIPT_PATH = "/mini-app/wealth/receipt"

    LOCATORS = {
        # Verified — cancel button on the external gateway page.
        "cancel_button": "css=#btnCancel",
    }

    def cancel(self) -> None:
        """Click "انصراف" (cancel) and wait for the redirect back to Platform's receipt.

        Same cross-origin race as ``SilverPage.confirm_and_pay()`` — the return trip
        can hop through an intermediate URL, so a ``wait_for_url`` timeout is only
        fatal when the browser truly never made it back.
        """
        self.click_when_visible(self.LOCATORS["cancel_button"])
        try:
            self.page.wait_for_url(f"**{self.RECEIPT_PATH}**", timeout=self.default_timeout_ms)
        except PlaywrightTimeoutError:
            if self.RECEIPT_PATH not in self.page.url:
                raise
