"""UI steps — thin orchestration; asserts live in ``landline_ui_asserts``."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from tests.config.settings import Settings
from tests.services.landline_ui_asserts import (
    assert_bill_confirm_details,
    assert_no_payable_period_offered,
    assert_on_app_hub,
    assert_on_landline_inquiry,
    assert_payment_period_sheet,
    assert_period_debt_state,
    assert_period_not_actionable,
    open_from_hub,
)
from tests.services.telephone_pool import TelephoneCase
from tests.ui.pages.app.bill.bill_confirm_page import BillConfirmPage
from tests.ui.pages.app.bill.bill_services_page import BillServicesPage
from tests.ui.pages.app.bill.landline_inquiry_page import LandlineInquiryPage, PaymentPeriod
from tests.ui.pages.app.hub_page import HubPage

scenarios("../features/bill/tci/tci_landline_ui.feature")
scenarios("../features/platform/ui_hub_smoke.feature")

# "a logged-in customer in the app" / "the customer opens the app hub" moved to
# tests/bdd/steps/conftest.py — pytest-bdd only reuses steps declared there across
# sibling step modules (see that file's docstring). Do not redefine here.


@when(parsers.re(r"^the customer opens (?P<feature>[A-Za-z0-9 -]+) from the hub$"))
def _(
    feature: str,
    hub_page: HubPage,
    bill_services_page: BillServicesPage,
    landline_inquiry_page: LandlineInquiryPage,
    settings: Settings,
) -> None:
    open_from_hub(
        feature,
        hub_page,
        bill_services_page,
        landline_inquiry_page,
        settings,
    )


@when("the customer inquires the pooled landline on the app")
def _(
    landline_inquiry_page: LandlineInquiryPage,
    telephone_case: TelephoneCase,
) -> None:
    landline_inquiry_page.inquire_landline(telephone_case.require_inquiry_id())


@when(parsers.re(r"^the customer opens the (?P<period>mid|final) payment period$"))
def _(
    landline_inquiry_page: LandlineInquiryPage,
    bill_confirm_page: BillConfirmPage,
    period: str,
) -> None:
    landline_inquiry_page.wait_for_payment_period_sheet()
    landline_inquiry_page.open_payment_period(period)
    bill_confirm_page.should_be_on_confirm()


@then("the customer is on the app hub")
def _(hub_page: HubPage, settings: Settings) -> None:
    assert_on_app_hub(hub_page, settings)


@then("the landline inquiry form is ready")
def _(landline_inquiry_page: LandlineInquiryPage, settings: Settings) -> None:
    assert_on_landline_inquiry(landline_inquiry_page, settings)


@then("the payment period sheet is shown for the pooled landline")
def _(
    landline_inquiry_page: LandlineInquiryPage,
    telephone_case: TelephoneCase,
) -> None:
    assert_payment_period_sheet(landline_inquiry_page, telephone_case.require_inquiry_id())


@then(parsers.re(r"^the (?P<term>mid|final) period is (?P<state>payable|without debt)$"))
def _(landline_inquiry_page: LandlineInquiryPage, term: str, state: str) -> None:
    assert_period_debt_state(landline_inquiry_page, term, state)


@then("the final payment period is not actionable")
def _(landline_inquiry_page: LandlineInquiryPage) -> None:
    landline_inquiry_page.wait_for_payment_period_sheet()
    assert_period_not_actionable(landline_inquiry_page, PaymentPeriod.FINAL)


@then("the bill confirm page shows the selected bill details")
def _(bill_confirm_page: BillConfirmPage, settings: Settings) -> None:
    assert_bill_confirm_details(bill_confirm_page, settings)


@then("no payable payment period is offered for the pooled landline")
def _(landline_inquiry_page: LandlineInquiryPage) -> None:
    assert_no_payable_period_offered(landline_inquiry_page)
