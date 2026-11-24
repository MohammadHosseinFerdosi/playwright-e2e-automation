"""Silver trading page — buy/sell silver from the wealth product (Playwright POM).

Verified against live UAT: the hub's "سرمایه" bottom-nav tab (see
``HubPage.LOCATORS["wealth_silver"]``) lands on the wealth mini-app overview
(``OVERVIEW_PATH``), which hosts tabs for gold/silver/fixed-income/crowdfunding.
Clicking its "نقره" tab routes to a real sibling URL, ``PATH`` — that redirect
was previously unverified: the old check only asserted the "نقره" *tab label*
was visible, which is already true on the overview screen before the tab is
even clicked, so it silently passed without ever navigating anywhere. Fixed
by asserting the URL actually changes to ``PATH`` and that silver-tab-only
content (the "خرید" action button) is visible.

A one-time promo modal ("درآمد ثابت کیف ثروت...") covers the full viewport the
first time the overview loads — it dims the tab bar behind it (backdrop) but
Playwright still resolves the "نقره" tab-header as present, so the plain
tab-header locator alone timed out waiting for a click that the modal was
swallowing. ``open_silver_tab()`` dismisses it first (same pattern as
``tests.ui.auth.dismiss_login_popup_if_present`` for the hub's own notice).

The "خرید" action button on the silver tab and its redirect are verified
against live UAT: it is account-independent — both a fresh random OTP user
and a pre-KYC'd account land on the same ``BUY_DESTINATION_PATH`` detail
screen. What differs *after* that (confirmed separately) is account-dependent:
a fresh/never-KYC'd account is routed into a one-time identity/BNPL form
(national code + birth date + postal code) before any amount can be entered,
while an already-KYC'd, funded account goes straight to a real amount input
(``aria-label="مبلغ مورد نظر"``) and a stable ``#WALLET_SILVER_CASH_IN``
confirm button.

The rest of the silver tab's action row is also verified against live UAT
(fresh, zero-balance account): "تراکنش‌ها" and "درخواست" are always enabled
and redirect to ``TRANSACTIONS_PATH`` / ``REQUEST_CREDIT_PATH``; "تبدیل" and
"فروش" are visible but *disabled* (no redirect on click) whenever the account
holds zero silver — that is correct product behavior, not a bug, so their
checks assert "visible + disabled" rather than a redirect. The "نقره کیف
ثروت" info card redirects to the same ``BUY_DESTINATION_PATH`` as "خرید".

The sell flow (``SELL_AMOUNT_PATH`` -> ``SELL_BANK_ACCOUNT_PATH`` ->
``SELL_CONFIRMATION_PATH`` -> receipt) is verified end-to-end against live UAT
with the same pre-KYC'd, funded account, once it actually holds silver (a
zero-balance account never reaches it — "فروش" stays disabled). Unlike the
buy flow, it never leaves the Platform origin — no external gateway — and the
resulting receipt shows "عملیات در انتظار" (pending settlement, up to 1
business day), not a final success/fail status.
"""

from __future__ import annotations

from enum import Enum

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from tests.ui.labels.app import AppLabels as L
from tests.ui.pages.base_page import BasePage


class SilverTabAction(str, Enum):
    """Named silver-tab controls for the Scenario Outline dispatch methods below."""

    BUY = "buy"
    TRANSACTIONS = "transactions"
    REQUEST_CREDIT = "request credit"
    WEALTH_BAG_CARD = "silver wealth bag"
    CONVERT = "convert"
    SELL = "sell"


class SilverPage(BasePage):
    """Silver sub-tab inside the wealth mini-app — buy/sell silver."""

    # Wealth mini-app overview — reached via the hub's "سرمایه" bottom-nav tab.
    OVERVIEW_PATH = "/mini-app/wealth/main/overview"
    # Silver sub-tab — reached by clicking the "نقره" tab from the overview. Verified.
    PATH = "/mini-app/wealth/main/silvers"
    # Silver detail/buy screen — reached by clicking "خرید" from the silver tab, or by
    # clicking the "نقره کیف ثروت" info card (same destination). Verified,
    # account-independent (same destination for a fresh user or an already-KYC'd one).
    BUY_DESTINATION_PATH = "/mini-app/wealth/silvers/WALLET_SILVER"
    # Verified — silver-tab "تراکنش‌ها" button destination.
    TRANSACTIONS_PATH = "/mini-app/wealth/transactions"
    # Verified — silver-tab "درخواست" (credit) button destination.
    REQUEST_CREDIT_PATH = "/mini-app/wealth/bnpl"
    # Verified — real amount-entry screen, reached from BUY_DESTINATION_PATH's sticky
    # bottom "خرید" button. Only reachable for an already-KYC'd account — a fresh
    # account is routed into the identity/BNPL form instead (see module docstring).
    WALLET_DEPOSIT_PATH = "/mini-app/wealth/wallet-deposit/wallet_silver"
    # Verified — payment-method review screen, reached after confirming the amount.
    QUICK_PAYMENT_PATH = "/mini-app/wealth/quick-payment/wallet_silver"
    # Verified — external Parsian/Shaparak bank gateway host. "تایید و پرداخت" on the
    # quick-payment screen redirects off-origin to this real bank IPG UI (Platform's
    # own internal /ipg-mock is not involved in this flow) — a fully separate origin,
    # so it's checked by hostname rather than a BasePage-style path.
    GATEWAY_HOST = "pec.shaparak.ir"
    # Verified — real amount-entry screen for a sale, reached from the silver tab's
    # "فروش" action button. Same KYC'd-account-only caveat as WALLET_DEPOSIT_PATH —
    # a fresh account's "فروش" is disabled (zero balance), not just ungated.
    SELL_AMOUNT_PATH = "/mini-app/wealth/wallet-withdraw/wallet_silver"
    # Verified — destination bank-account picker, reached after confirming the amount.
    SELL_BANK_ACCOUNT_PATH = "/mini-app/wealth/select-bank-account/wallet_silver"
    # Verified — final sale review screen, reached after confirming the bank account.
    SELL_CONFIRMATION_PATH = "/mini-app/wealth/wallet-withdraw-confirmation/wallet_silver"

    LOCATORS = {
        # Verified — the "جدید" badge sits alongside the label, not inside its own
        # text node, so a tab-header + contains(text(),...) xpath never matches;
        # normalize-space() (full descendant text) resolves to the inner label node.
        "silver_tab": f"xpath=//*[normalize-space()='{L.SILVER}']",
        # Verified — one-time overview promo modal ("درآمد ثابت کیف ثروت...").
        "promo_modal_dismiss": f"xpath=//*[normalize-space()='{L.GOT_IT}']",
        # Verified — the promo modal's bottom-sheet backdrop. It stays attached and
        # pointer-event-intercepting for a beat after "متوجه شدم" is clicked (closing
        # animation), even once the visible content is gone — wait for it to hide
        # before the next click, or that click can silently hit the stale backdrop.
        "bottom_sheet_backdrop": "css=.bottom-sheet-container",
        # Verified — silver-tab action button; redirects to BUY_DESTINATION_PATH.
        "buy_tab": f"xpath=//*[normalize-space()='{L.BUY}']",
        # Verified — disabled (no redirect) whenever the account holds zero silver.
        # normalize-space()='فروش' alone also matches two ancestor wrappers around this
        # leaf label div — pinned to the leaf via its stable "text-onback-*" class so
        # get_attribute("class") reliably sees the "text-onback-disabled" state.
        "sell_tab": f"xpath=//div[contains(@class,'text-onback') and normalize-space()='{L.SELL}']",
        # Verified — always enabled; redirects to TRANSACTIONS_PATH.
        "transactions_button": f"xpath=//*[normalize-space()='{L.TRANSACTIONS}']",
        # Verified — disabled (no redirect) whenever the account holds zero silver.
        # See "sell_tab" above — pinned to the leaf label div for the same reason.
        "convert_button": f"xpath=//div[contains(@class,'text-onback') and normalize-space()='{L.CONVERT}']",
        # Verified — always enabled; redirects to REQUEST_CREDIT_PATH.
        "request_credit_button": f"xpath=//*[normalize-space()='{L.REQUEST_CREDIT}']",
        # Verified — info card; redirects to BUY_DESTINATION_PATH (same as "buy_tab").
        "wealth_bag_card": f"xpath=//*[contains(text(),'{L.SILVER_WEALTH_BAG}')]",
        # Verified — sticky bottom <button> on the buy/detail screen (distinct element
        # from "buy_tab" above, same label). Redirects to WALLET_DEPOSIT_PATH.
        "buy_detail_confirm_button": f"xpath=//button[normalize-space()='{L.BUY}']",
        # Verified — real amount field on the wallet-deposit screen (KYC'd account only).
        "wealth_amount_input": f"xpath=//input[@aria-label='{L.WEALTH_AMOUNT_FIELD}']",
        # Verified — stable id, submits the amount; redirects to QUICK_PAYMENT_PATH.
        "wealth_amount_confirm_button": "css=#WALLET_SILVER_CASH_IN",
        # Verified — stable id on the quick-payment screen; redirects off-origin to
        # the external gateway (GATEWAY_HOST). Default-selected payment method is
        # "درگاه پرداخت اینترنتی" (online gateway, no fee) — not changed by this click.
        "confirm_and_pay_button": "css=#CONFIRM_AND_QUICK_PAYMENT",
        # Verified — shared by both the sell-amount and bank-account screens (same
        # label both times, different screens — each caller waits on its own URL).
        "confirm_and_continue_button": f"xpath=//button[normalize-space()='{L.CONFIRM_AND_CONTINUE}']",
        # Verified — stable id on the sell confirmation screen; redirects to the
        # cash-out receipt (?walletAction=cashOut).
        "confirm_sale_button": "css=#CONFIRM_AND_CASH_OUT",
    }

    def open(self) -> None:
        """Navigate to the wealth overview, then open the "نقره" tab."""
        self.goto(self.OVERVIEW_PATH)
        self.open_silver_tab()

    def open_silver_tab(self) -> None:
        """Dismiss the overview promo modal if present, click "نقره", wait for it to load."""
        self.dismiss_promo_modal_if_present()
        self.click_when_visible(self.LOCATORS["silver_tab"])
        self.should_be_on_silver()

    def dismiss_promo_modal_if_present(self, timeout_ms: int = 3_000) -> None:
        """Close the overview promo modal when present; no-op when absent.

        Also waits for its bottom-sheet backdrop to clear after the close click —
        see LOCATORS["bottom_sheet_backdrop"] for why (closing-animation race that
        intermittently swallowed the very next click, e.g. on "نقره").
        """
        if not self.is_visible(self.LOCATORS["promo_modal_dismiss"], timeout_ms=timeout_ms):
            return
        self.click_when_visible(self.LOCATORS["promo_modal_dismiss"], timeout_ms=timeout_ms)
        backdrop = self.resolve(self.LOCATORS["bottom_sheet_backdrop"])
        try:
            backdrop.first.wait_for(state="hidden", timeout=8_000)
        except PlaywrightTimeoutError:
            pass

    def should_be_on_silver(self) -> None:
        """Wait until the silver sub-tab route is reached and its content is visible."""
        self.wait_until_url_contains(self.PATH)
        self.expect_visible(self.LOCATORS["buy_tab"])

    def is_on_silver_tab(self) -> bool:
        """True when the browser URL is the silver sub-tab route (non-throwing)."""
        return self.url_contains(self.PATH)

    def is_buy_button_visible(self, timeout_ms: int = 5_000) -> bool:
        """True when the "خرید" action button is visible on the silver tab (non-throwing)."""
        return self.is_visible(self.LOCATORS["buy_tab"], timeout_ms=timeout_ms)

    def open_buy_screen(self) -> None:
        """Click "خرید" on the silver tab and wait for the real redirect."""
        self.click_when_visible(self.LOCATORS["buy_tab"])
        self.wait_until_url_contains(self.BUY_DESTINATION_PATH)

    def is_on_buy_screen(self) -> bool:
        """True when the browser URL is the silver buy/detail screen (non-throwing)."""
        return self.url_contains(self.BUY_DESTINATION_PATH)

    def open_wallet_deposit_screen(self) -> None:
        """Click the sticky bottom "خرید" on the buy/detail screen; wait for the redirect.

        KYC'd-account-only path — see module docstring for the fresh-account BNPL branch.
        """
        self.click_when_visible(self.LOCATORS["buy_detail_confirm_button"])
        self.wait_until_url_contains(self.WALLET_DEPOSIT_PATH)

    def is_on_wallet_deposit_screen(self) -> bool:
        """True when the browser URL is the real amount-entry screen (non-throwing)."""
        return self.url_contains(self.WALLET_DEPOSIT_PATH)

    def submit_wallet_deposit_amount(self, amount: str) -> None:
        """Enter ``amount`` (rial) and confirm; wait for the quick-payment redirect."""
        self.fill_when_visible(self.LOCATORS["wealth_amount_input"], amount)
        self.click_when_visible(self.LOCATORS["wealth_amount_confirm_button"])
        self.wait_until_url_contains(self.QUICK_PAYMENT_PATH)

    def is_on_quick_payment_screen(self) -> bool:
        """True when the browser URL is the payment-method review screen (non-throwing)."""
        return self.url_contains(self.QUICK_PAYMENT_PATH)

    def confirm_and_pay(self) -> None:
        """Confirm the default payment method; wait for the redirect to the gateway.

        The gateway redirect is a real cross-origin navigation that itself hops
        twice (bare token URL, then one adding a cookie-support query param) —
        ``wait_for_url``'s event-based matching can race that second hop and time
        out even though the browser already reached the gateway. Treat the
        timeout as non-fatal when the URL already reflects success by then.
        """
        self.click_when_visible(self.LOCATORS["confirm_and_pay_button"])
        try:
            self.page.wait_for_url(f"**{self.GATEWAY_HOST}**", timeout=self.default_timeout_ms)
        except PlaywrightTimeoutError:
            if not self.is_on_payment_gateway():
                raise

    def is_on_payment_gateway(self) -> bool:
        """True when the browser URL is the external bank gateway (non-throwing)."""
        return self.GATEWAY_HOST in self.page.url

    def is_sell_button_visible(self, timeout_ms: int = 5_000) -> bool:
        """True when the "فروش" action button is visible on the silver tab (non-throwing)."""
        return self.is_visible(self.LOCATORS["sell_tab"], timeout_ms=timeout_ms)

    def is_sell_button_enabled(self) -> bool:
        """True when "فروش" is enabled — false whenever the account holds zero silver.

        This is a custom Angular ``<div>`` control, not a native disabled button — it
        carries no ``disabled``/``aria-disabled`` attribute, only a CSS class
        (``text-onback-disabled``), so ``Locator.is_enabled()`` always reports true.
        """
        class_name = self.resolve(self.LOCATORS["sell_tab"]).first.get_attribute("class") or ""
        return "disabled" not in class_name

    def open_sell_amount_screen(self) -> None:
        """Click "فروش" on the silver tab and wait for the real redirect.

        KYC'd-account-only path in practice — a fresh/zero-balance account has
        "فروش" disabled rather than gated behind an identity form (see
        ``is_sell_button_enabled()``).
        """
        self.click_when_visible(self.LOCATORS["sell_tab"])
        self.wait_until_url_contains(self.SELL_AMOUNT_PATH)

    def is_on_sell_amount_screen(self) -> bool:
        """True when the browser URL is the real sell amount-entry screen (non-throwing)."""
        return self.url_contains(self.SELL_AMOUNT_PATH)

    def submit_sell_amount(self, amount: str) -> None:
        """Enter ``amount`` (rial) and confirm; wait for the bank-account redirect."""
        self.fill_when_visible(self.LOCATORS["wealth_amount_input"], amount)
        self.click_when_visible(self.LOCATORS["confirm_and_continue_button"])
        self.wait_until_url_contains(self.SELL_BANK_ACCOUNT_PATH)

    def is_on_sell_bank_account_screen(self) -> bool:
        """True when the browser URL is the destination bank-account picker (non-throwing)."""
        return self.url_contains(self.SELL_BANK_ACCOUNT_PATH)

    def confirm_bank_account(self) -> None:
        """Confirm the pre-selected default bank account; wait for the review redirect."""
        self.click_when_visible(self.LOCATORS["confirm_and_continue_button"])
        self.wait_until_url_contains(self.SELL_CONFIRMATION_PATH)

    def is_on_sell_confirmation_screen(self) -> bool:
        """True when the browser URL is the final sale review screen (non-throwing)."""
        return self.url_contains(self.SELL_CONFIRMATION_PATH)

    def confirm_sale(self) -> None:
        """Confirm the sale ("تایید فروش") and wait for the receipt redirect."""
        self.click_when_visible(self.LOCATORS["confirm_sale_button"])
        # Matches ReceiptPage.PATH — see IpgGatewayPage for why this is duplicated
        # rather than imported (keeps this page object self-contained).
        self.wait_until_url_contains("/mini-app/wealth/receipt")

    def is_convert_button_visible(self, timeout_ms: int = 5_000) -> bool:
        """True when the "تبدیل" action button is visible on the silver tab (non-throwing)."""
        return self.is_visible(self.LOCATORS["convert_button"], timeout_ms=timeout_ms)

    def is_convert_button_enabled(self) -> bool:
        """True when "تبدیل" is enabled — false whenever the account holds zero silver.

        Same custom-``<div>``-control caveat as ``is_sell_button_enabled()`` — checks
        the ``text-onback-disabled`` CSS class, not a native disabled attribute.
        """
        class_name = self.resolve(self.LOCATORS["convert_button"]).first.get_attribute("class") or ""
        return "disabled" not in class_name

    def is_transactions_button_visible(self, timeout_ms: int = 5_000) -> bool:
        """True when the "تراکنش‌ها" action button is visible on the silver tab (non-throwing)."""
        return self.is_visible(self.LOCATORS["transactions_button"], timeout_ms=timeout_ms)

    def open_transactions(self) -> None:
        """Click "تراکنش‌ها" on the silver tab and wait for the real redirect."""
        self.click_when_visible(self.LOCATORS["transactions_button"])
        self.wait_until_url_contains(self.TRANSACTIONS_PATH)

    def is_on_transactions_screen(self) -> bool:
        """True when the browser URL is the silver transactions screen (non-throwing)."""
        return self.url_contains(self.TRANSACTIONS_PATH)

    def is_request_credit_button_visible(self, timeout_ms: int = 5_000) -> bool:
        """True when the "درخواست" action button is visible on the silver tab (non-throwing)."""
        return self.is_visible(self.LOCATORS["request_credit_button"], timeout_ms=timeout_ms)

    def open_request_credit(self) -> None:
        """Click "درخواست" on the silver tab and wait for the real redirect."""
        self.click_when_visible(self.LOCATORS["request_credit_button"])
        self.wait_until_url_contains(self.REQUEST_CREDIT_PATH)

    def is_on_request_credit_screen(self) -> bool:
        """True when the browser URL is the credit-request screen (non-throwing)."""
        return self.url_contains(self.REQUEST_CREDIT_PATH)

    def is_wealth_bag_card_visible(self, timeout_ms: int = 5_000) -> bool:
        """True when the "نقره کیف ثروت" info card is visible on the silver tab (non-throwing)."""
        return self.is_visible(self.LOCATORS["wealth_bag_card"], timeout_ms=timeout_ms)

    def open_wealth_bag_card(self) -> None:
        """Click the "نقره کیف ثروت" info card and wait for the real redirect."""
        self.click_when_visible(self.LOCATORS["wealth_bag_card"])
        self.wait_until_url_contains(self.BUY_DESTINATION_PATH)

    def is_action_visible(self, action: SilverTabAction | str) -> bool:
        """True when the named silver-tab control is visible (non-throwing)."""
        visible_checks = {
            SilverTabAction.BUY: self.is_buy_button_visible,
            SilverTabAction.TRANSACTIONS: self.is_transactions_button_visible,
            SilverTabAction.REQUEST_CREDIT: self.is_request_credit_button_visible,
            SilverTabAction.WEALTH_BAG_CARD: self.is_wealth_bag_card_visible,
            SilverTabAction.CONVERT: self.is_convert_button_visible,
            SilverTabAction.SELL: self.is_sell_button_visible,
        }
        return visible_checks[SilverTabAction(action)]()

    def is_action_disabled(self, action: SilverTabAction | str) -> bool:
        """True when the named silver-tab control is disabled (zero-silver accounts)."""
        enabled_checks = {
            SilverTabAction.CONVERT: self.is_convert_button_enabled,
            SilverTabAction.SELL: self.is_sell_button_enabled,
        }
        return not enabled_checks[SilverTabAction(action)]()

    def open_action(self, action: SilverTabAction | str) -> None:
        """Click the named silver-tab control and wait for its real redirect."""
        open_actions = {
            SilverTabAction.BUY: self.open_buy_screen,
            SilverTabAction.TRANSACTIONS: self.open_transactions,
            SilverTabAction.REQUEST_CREDIT: self.open_request_credit,
            SilverTabAction.WEALTH_BAG_CARD: self.open_wealth_bag_card,
        }
        open_actions[SilverTabAction(action)]()

    def is_on_action_destination(self, action: SilverTabAction | str) -> bool:
        """True when the browser URL matches the named action's real destination."""
        destination_checks = {
            SilverTabAction.BUY: self.is_on_buy_screen,
            SilverTabAction.TRANSACTIONS: self.is_on_transactions_screen,
            SilverTabAction.REQUEST_CREDIT: self.is_on_request_credit_screen,
            SilverTabAction.WEALTH_BAG_CARD: self.is_on_buy_screen,
        }
        return destination_checks[SilverTabAction(action)]()
