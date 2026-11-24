"""Shared BDD steps for all modules under ``tests/bdd/steps/``.

pytest-bdd only reuses steps from ``conftest.py`` (not from sibling step modules).
"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page
from pytest_bdd import given, parsers, then, when

from tests.api.bill_mng.bills.config import get_bills_config
from tests.api.bill_mng.headers import BILL_IT_PRIMARY_USER_ID
from tests.api.client import ApiClient
from tests.api.tci.client import TciClient
from tests.config.settings import Settings
from tests.services.bill_config_asserts import (
    assert_bill_business_rejection,
    assert_bill_configuration_lists_active_types,
    assert_bill_configuration_succeeds,
)
from tests.services.dashboard_topup_ui import open_from_dashboard
from tests.services.debit import bank_transfer_asserts as bt_assert
from tests.services.debit import nemo_cash_out_fixtures as nemo_fixtures
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow
from tests.services.debit.duplicate_route_asserts import assert_duplicate_route_single_row
from tests.services.debit.nemo_cash_out import NemoCashOutFlow
from tests.services.factories import User, UserFactory
from tests.services.telephone_pool import (
    TelephoneBillPool,
    TelephoneCase,
    require_tci_client,
)
from tests.ui.auth import AppUiAuth, DashboardUiAuth, require_dashboard_credentials
from tests.ui.pages.app.hub_page import HubPage
from tests.ui.pages.dashboard.home_page import DashboardHomePage
from tests.ui.pages.dashboard.operator_picker_modal import DashboardOperatorPickerModal
from tests.ui.pages.dashboard.super_app_page import DashboardSuperAppPage
from tests.ui.pages.dashboard.topup_provider_weights_modal import (
    DashboardTopupProviderWeightsModal,
)

# --- App UI (shared across all app-facing feature files: bill, wealth, …) --------


@given("a logged-in customer in the app", target_fixture="ui_customer")
def _logged_in_customer_in_app(
    user_factory: UserFactory,
    app_ui_auth: AppUiAuth,
    page: Page,
) -> User:
    user = user_factory.create()
    app_ui_auth.login_user_via_api_inject(page, user)
    return user


@when("the customer opens the app hub")
def _customer_opens_app_hub(hub_page: HubPage) -> None:
    hub_page.open()


@given(
    parsers.re(r'^the telephone bill pool has an? "(?P<case_name>[A-Za-z0-9_]+)" case$'),
    target_fixture="telephone_case",
)
def _telephone_pool_case(case_name: str, telephone_bill_pool: TelephoneBillPool) -> TelephoneCase:
    """Shared by Platform validate, TCI provider, and landline UI features."""
    return telephone_bill_pool.require_prepared_case(case_name)


@given("a Platform business access token", target_fixture="access_token")
def _platform_business_access_token(platform_business_token: str) -> str:
    return platform_business_token


@given("a Company business access token", target_fixture="access_token")
def _company_business_access_token(company_business_token: str) -> str:
    return company_business_token


@given(
    "a customer identity for bill management",
    target_fixture="bill_user_id",
)
def _bill_customer_identity() -> str:
    """MS bill-mng trusts User-Id; IT primary UUID is enough for validation/config."""
    return BILL_IT_PRIMARY_USER_ID


@when(
    "the customer requests bill configuration",
    target_fixture="bill_config_result",
)
def _request_bill_configuration(
    bill_user_id: str, microservice_client: ApiClient
) -> dict[str, Any]:
    return get_bills_config(microservice_client, bill_user_id)


@then("the bill configuration request succeeds")
def _bill_configuration_succeeds(bill_config_result: dict[str, Any]) -> None:
    assert_bill_configuration_succeeds(bill_config_result)


@then("the bill configuration lists active bill types")
def _bill_configuration_lists_active_types(bill_config_result: dict[str, Any]) -> None:
    assert_bill_configuration_lists_active_types(bill_config_result)


@then(parsers.re(r"^the bill inquiry is rejected as (?P<result_title>[A-Za-z0-9_]+)$"))
def _bill_inquiry_rejected(bill_inquiry_result: dict[str, Any], result_title: str) -> None:
    assert_bill_business_rejection(bill_inquiry_result, result_title.strip())


@then(parsers.re(r"^the bill payment init is rejected as (?P<result_title>[A-Za-z0-9_]+)$"))
def _bill_init_rejected(bill_init_result: dict[str, Any], result_title: str) -> None:
    assert_bill_business_rejection(bill_init_result, result_title.strip())


# --- Dashboard Super App (shared by bill + topup/IPKG features) -------------------


@given("a logged-in staff user on the dashboard")
def _logged_in_staff_on_dashboard(
    dashboard_ui_auth: DashboardUiAuth,
    page: Page,
    settings: Settings,
    dashboard_home_page: DashboardHomePage,
) -> None:
    username, password = require_dashboard_credentials(settings)
    dashboard_ui_auth.login_via_api_inject(page, username, password)
    dashboard_home_page.should_be_on_home()


@given("the staff is on the Super App page")
@when("the staff opens Super App settings")
def _staff_on_super_app(
    dashboard_home_page: DashboardHomePage,
    dashboard_super_app_page: DashboardSuperAppPage,
) -> None:
    dashboard_home_page.open_settings()
    dashboard_super_app_page.open_from_settings()
    dashboard_super_app_page.should_be_on_super_app()


@when(parsers.re(r"^the staff opens (?P<tile>[A-Za-z0-9 -]+) from the dashboard$"))
def _staff_opens_tile_from_dashboard(
    tile: str,
    dashboard_super_app_page: DashboardSuperAppPage,
    dashboard_operator_picker_modal: DashboardOperatorPickerModal,
    dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal,
) -> None:
    open_from_dashboard(
        tile,
        dashboard_super_app_page,
        dashboard_operator_picker_modal,
        dashboard_topup_provider_weights_modal,
    )


@then("dashboard services are shown on the Super App page")
def _dashboard_services_shown(dashboard_super_app_page: DashboardSuperAppPage) -> None:
    dashboard_super_app_page.should_be_on_super_app()
    dashboard_super_app_page.should_show_platform_services()


@then("a success toast is shown on the Super App page")
def _success_toast_shown(dashboard_super_app_page: DashboardSuperAppPage) -> None:
    dashboard_super_app_page.should_be_on_super_app()
    dashboard_super_app_page.should_show_success_toast()


# --- TCI client (skip when credentials / client missing) -------------------------


@pytest.fixture
def required_tci_client(tci_client: TciClient | None) -> TciClient:
    """Skip when root ``tci_client`` is ``None`` (missing TCI secrets)."""
    return require_tci_client(tci_client)


# --- Debit bank-transfer (shared by gateway / Mellat / Shahin / Manual) ----------


@given(parsers.re(r"^cash-out goes through (?P<gateway>[A-Za-z0-9 ]+)$"))
def _cash_out_goes_through_gateway(gateway: str, bt_flow: BankTransferFlow) -> None:
    bt_flow.pin_named_gateway(gateway)


@given(parsers.re(r"^a Nemo customer can (?P<capability>[A-Za-z0-9 -]+)$"))
def _nemo_customer_capability(capability: str, nemo_flow: NemoCashOutFlow) -> None:
    nemo_fixtures.prepare_customer_capability(nemo_flow, capability)


@then("the call is rejected as invalid input")
def _call_rejected_as_invalid_input(bt_ctx: BankTransferContext) -> None:
    bt_assert.assert_title_rejected(bt_ctx, expected_title="INVALID_PARAMETER")


@then(
    parsers.re(
        r"^(?:the )?duplicate (?P<route_kind>[A-Za-z0-9 ]+?) "
        r"routes? keeps? a single transfer row$"
    )
)
def _duplicate_route_keeps_single_row(route_kind: str, bt_ctx: BankTransferContext) -> None:
    assert_duplicate_route_single_row(bt_ctx, route_kind)
