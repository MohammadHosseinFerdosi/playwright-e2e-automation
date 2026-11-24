"""Dashboard Super App — bill inquiry provider config UI steps (thin)."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.config.settings import Settings
from tests.services.bill_inquiry_admin import (
    BillInquiryAdminSession,
    bind_bill_inquiry_admin,
)
from tests.services.dashboard_bill_ui import (
    assert_distribution_shown,
    assert_inquiry_confirm_state,
    assert_inquiry_provider_weight,
    assert_inquiry_providers,
    assert_inquiry_weights,
    assert_inquiry_weights_match_noted,
    open_bill_distribution,
    set_first_provider_weight,
    set_inquiry_provider_weight,
    set_inquiry_weights,
)
from tests.ui.pages.dashboard.bill_inquiry_modal import DashboardBillInquiryModal
from tests.ui.pages.dashboard.bill_provider_weights_modal import (
    DashboardBillProviderWeightsModal,
)
from tests.ui.pages.dashboard.super_app_page import DashboardSuperAppPage

scenarios("../features/dashboard/bill_inquiry_provider_weights.feature")
scenarios("../features/dashboard/bill_inquiry_admin_weights_api.feature")


@pytest.fixture
def bill_inquiry_admin(
    request: pytest.FixtureRequest,
    microservice_client: ApiClient,
    settings: Settings,
) -> BillInquiryAdminSession:
    """Per-scenario electricity admin config note/restore session."""
    return bind_bill_inquiry_admin(request, microservice_client, settings)


@given("the admin notes the current electricity inquiry distributions")
def _(bill_inquiry_admin: BillInquiryAdminSession) -> None:
    bill_inquiry_admin.note_electricity_distributions()


@when(
    parsers.re(
        r"^the admin sets electricity inquiry weights to (?P<raw>[-0-9, and]+) via the admin API$"
    )
)
def _(raw: str, bill_inquiry_admin: BillInquiryAdminSession) -> None:
    bill_inquiry_admin.set_electricity_weights(raw)


@when("the admin restores the noted electricity inquiry distributions")
def _(bill_inquiry_admin: BillInquiryAdminSession) -> None:
    bill_inquiry_admin.restore_noted_distributions()


@then("the admin bills config update succeeds")
def _(bill_inquiry_admin: BillInquiryAdminSession) -> None:
    bill_inquiry_admin.assert_put_succeeded()


@then(parsers.re(r"^the admin bills config update is rejected as (?P<result_title>[A-Za-z0-9_]+)$"))
def _(bill_inquiry_admin: BillInquiryAdminSession, result_title: str) -> None:
    bill_inquiry_admin.assert_put_rejected(result_title)


@when("the staff closes the bill inquiry picker")
def _(dashboard_bill_inquiry_modal: DashboardBillInquiryModal) -> None:
    dashboard_bill_inquiry_modal.close()


@when(parsers.re(r"^the staff opens (?P<bill_type>electricity|landline) inquiry distribution$"))
def _open_bill_distribution(
    bill_type: str,
    dashboard_super_app_page: DashboardSuperAppPage,
    dashboard_bill_inquiry_modal: DashboardBillInquiryModal,
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
) -> None:
    open_bill_distribution(
        bill_type,
        dashboard_super_app_page,
        dashboard_bill_inquiry_modal,
        dashboard_bill_provider_weights_modal,
    )


@when("the staff notes the current inquiry weights")
def _(
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
    bill_inquiry_admin: BillInquiryAdminSession,
) -> None:
    bill_inquiry_admin.note_ui_weights(dashboard_bill_provider_weights_modal.weight_values())


@when("the staff notes the current electricity admin inquiry distributions")
def _(bill_inquiry_admin: BillInquiryAdminSession) -> None:
    bill_inquiry_admin.note_electricity_distributions()


@when(parsers.re(r"^the staff sets the first provider weight to (?P<value>-?\d+)$"))
def _(
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
    value: str,
) -> None:
    set_first_provider_weight(dashboard_bill_provider_weights_modal, value)


@when(parsers.re(r"^the staff sets inquiry weights to (?P<raw>[-0-9, and]+)$"))
def _(
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
    raw: str,
) -> None:
    set_inquiry_weights(dashboard_bill_provider_weights_modal, raw)


@when(
    parsers.re(
        r"^the staff sets the inquiry weight for (?P<provider>[A-Za-z0-9]+) to (?P<value>-?\d+)$"
    )
)
def _(
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
    provider: str,
    value: str,
) -> None:
    set_inquiry_provider_weight(dashboard_bill_provider_weights_modal, provider, value)


@when("the staff goes back from inquiry distribution")
def _(dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal) -> None:
    dashboard_bill_provider_weights_modal.click_back()


@when("the staff confirms inquiry distribution update")
def _(dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal) -> None:
    dashboard_bill_provider_weights_modal.click_confirm()


@when("the staff restores the noted electricity admin inquiry distributions")
def _(bill_inquiry_admin: BillInquiryAdminSession) -> None:
    bill_inquiry_admin.restore_noted_distributions()


@then("the bill inquiry picker is shown")
def _(dashboard_bill_inquiry_modal: DashboardBillInquiryModal) -> None:
    dashboard_bill_inquiry_modal.should_be_open()


@then("the bill inquiry lists the utility bill types")
def _(dashboard_bill_inquiry_modal: DashboardBillInquiryModal) -> None:
    dashboard_bill_inquiry_modal.should_list_bill_types()


@then(parsers.re(r"^the inquiry distribution is shown for (?P<bill_type>[A-Za-z0-9 ]+)$"))
def _(
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
    bill_type: str,
) -> None:
    assert_distribution_shown(dashboard_bill_provider_weights_modal, bill_type)


@then(
    parsers.re(
        r"^the inquiry distribution shows providers "
        r"(?P<first>[A-Za-z0-9]+) and (?P<second>[A-Za-z0-9]+)$"
    )
)
def _(
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
    first: str,
    second: str,
) -> None:
    assert_inquiry_providers(dashboard_bill_provider_weights_modal, first, second)


@then(parsers.re(r"^the inquiry weights are (?P<raw>[-0-9, and]+)$"))
def _(
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
    raw: str,
) -> None:
    assert_inquiry_weights(dashboard_bill_provider_weights_modal, raw)


@then(parsers.re(r"^the inquiry weight for (?P<provider>[A-Za-z0-9]+) is (?P<value>-?\d+)$"))
def _(
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
    provider: str,
    value: str,
) -> None:
    assert_inquiry_provider_weight(dashboard_bill_provider_weights_modal, provider, value)


@then("the inquiry weights match the noted values")
def _(
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
    bill_inquiry_admin: BillInquiryAdminSession,
) -> None:
    assert_inquiry_weights_match_noted(
        dashboard_bill_provider_weights_modal, bill_inquiry_admin.ui_values
    )


@then(parsers.re(r"^the electricity admin inquiry weights are (?P<raw>[-0-9, and]+)$"))
def _(bill_inquiry_admin: BillInquiryAdminSession, raw: str) -> None:
    bill_inquiry_admin.assert_electricity_weights(raw)


@then("the electricity admin inquiry distributions match the noted values")
def _(bill_inquiry_admin: BillInquiryAdminSession) -> None:
    bill_inquiry_admin.assert_electricity_matches_noted()


@then(parsers.re(r"^inquiry distribution confirm is (?P<state>enabled|disabled)$"))
def _inquiry_confirm_state(
    state: str,
    dashboard_bill_provider_weights_modal: DashboardBillProviderWeightsModal,
) -> None:
    assert_inquiry_confirm_state(dashboard_bill_provider_weights_modal, state)
