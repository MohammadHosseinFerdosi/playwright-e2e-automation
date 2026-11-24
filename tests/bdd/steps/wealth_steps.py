"""Step definitions for tests/bdd/features/wealth/silver_trade_ui.feature.

Every scenario here is verified end-to-end against live UAT, including the URL
actually changing on each click (not just a label being visible) —
``HubDestination.WEALTH_SILVER`` (hub's "سرمایه" tab), the overview -> "نقره"
tab redirect, and every step of the buy/sell flows below.

"Customer cancels a silver purchase at the payment gateway" and "Customer
sells silver and the sale is pending settlement" use
``settings.wealth_silver_kyc_test_cell_number`` (a pre-KYC'd, funded UAT
account — a fresh random user hits an identity/BNPL gate instead of the real
amount screen, see ``silver_page.py``). "تایید و پرداخت" on the quick-payment
screen redirects off-origin to a real bank gateway (``pec.shaparak.ir``) — no
successful-payment test credentials are available, so the buy scenario covers
the cancel/fail path, not a successful purchase. The sell flow never leaves
the Platform origin and settles asynchronously, so its receipt is checked for
"pending", not a final status.

"a logged-in customer in the app" / "the customer opens the app hub" are
shared steps declared in ``tests/bdd/steps/conftest.py`` — pytest-bdd only
reuses steps across sibling step modules from that file, so do not redefine
them here (see that conftest's docstring).
"""

from __future__ import annotations

from playwright.sync_api import Page
from pytest_bdd import given, parsers, scenarios, then, when

from tests.config.settings import Settings
from tests.services.assert_report import assert_truthy
from tests.ui.auth import AppUiAuth
from tests.ui.pages.app.hub_page import HubDestination, HubPage
from tests.ui.pages.app.wealth.ipg_gateway_page import IpgGatewayPage
from tests.ui.pages.app.wealth.receipt_page import ReceiptPage
from tests.ui.pages.app.wealth.silver_page import SilverPage

scenarios("../features/wealth/silver_trade_ui.feature")


@given("a logged-in customer with an existing silver wallet")
def _(app_ui_auth: AppUiAuth, page: Page, settings: Settings) -> None:
    app_ui_auth.login_via_api_inject(page, settings.wealth_silver_kyc_test_cell_number)


@when("the customer opens the silver trading screen from the hub")
def _(hub_page: HubPage, silver_page: SilverPage) -> None:
    hub_page.navigate_to(HubDestination.WEALTH_SILVER)
    silver_page.open_silver_tab()
    assert_truthy(
        f"Customer is redirected to the silver tab ({SilverPage.PATH})",
        silver_page.is_on_silver_tab(),
    )


@then(parsers.parse("the {action} action is available on the silver tab"))
def _(silver_page: SilverPage, action: str) -> None:
    assert_truthy(
        f"{action!r} action is visible on the silver tab", silver_page.is_action_visible(action)
    )


@then(parsers.parse("the {action} action is disabled while the customer holds no silver"))
def _(silver_page: SilverPage, action: str) -> None:
    assert_truthy(
        f"{action!r} action is disabled (zero silver balance)",
        silver_page.is_action_disabled(action),
    )


@when(parsers.parse("the customer opens {action} from the silver tab"))
def _(silver_page: SilverPage, action: str) -> None:
    silver_page.open_action(action)


@then(parsers.parse("the customer is redirected to the destination for {action}"))
def _(silver_page: SilverPage, action: str) -> None:
    assert_truthy(
        f"Customer is redirected to the real destination for {action!r}",
        silver_page.is_on_action_destination(action),
    )


@when("the customer views the silver purchase detail")
def _(silver_page: SilverPage) -> None:
    silver_page.open_buy_screen()


@when("the customer opens the silver amount screen")
def _(silver_page: SilverPage) -> None:
    silver_page.open_wallet_deposit_screen()


@when("the customer submits a silver purchase amount")
def _(silver_page: SilverPage) -> None:
    silver_page.submit_wallet_deposit_amount(amount="100000")


@when("the customer confirms and pays for the silver purchase")
def _(silver_page: SilverPage) -> None:
    silver_page.confirm_and_pay()


@when("the customer cancels the payment at the gateway")
def _(ipg_gateway_page: IpgGatewayPage) -> None:
    ipg_gateway_page.cancel()


@then("the customer is redirected to the silver purchase receipt")
def _(receipt_page: ReceiptPage) -> None:
    assert_truthy("Customer is redirected to the receipt screen", receipt_page.is_on_receipt())


@then("the receipt shows the operation failed")
def _(receipt_page: ReceiptPage) -> None:
    assert_truthy("Receipt shows the operation failed status", receipt_page.is_operation_failed())


@then("the receipt shows the silver purchase description")
def _(receipt_page: ReceiptPage) -> None:
    assert_truthy(
        "Receipt shows the silver purchase description",
        receipt_page.is_purchase_description_shown(),
    )


@when("the customer opens the silver sell amount screen")
def _(silver_page: SilverPage) -> None:
    silver_page.open_sell_amount_screen()


@when("the customer submits a silver sale amount")
def _(silver_page: SilverPage) -> None:
    silver_page.submit_sell_amount(amount="100000")


@when("the customer confirms the default bank account")
def _(silver_page: SilverPage) -> None:
    silver_page.confirm_bank_account()


@when("the customer confirms the silver sale")
def _(silver_page: SilverPage) -> None:
    silver_page.confirm_sale()


@then("the customer is redirected to the silver sale receipt")
def _(receipt_page: ReceiptPage) -> None:
    assert_truthy("Customer is redirected to the receipt screen", receipt_page.is_on_receipt())


@then("the receipt shows the operation pending")
def _(receipt_page: ReceiptPage) -> None:
    assert_truthy("Receipt shows the operation pending status", receipt_page.is_operation_pending())
