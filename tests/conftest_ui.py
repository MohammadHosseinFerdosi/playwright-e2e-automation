"""Playwright UI fixtures — browser session and page objects.

Imported into ``tests/conftest.py`` (pytest only auto-loads that entry point).
"""

from __future__ import annotations

from collections.abc import Iterator

import allure
import pytest
from playwright.sync_api import Page

from tests.api.client import ApiClient
from tests.config.settings import Settings
from tests.conftest_reporting import ALLURE_RESULTS_DIR, safe_name
from tests.services.db.mysql_client import MySQLClient
from tests.services.db.redis_client import RedisClient
from tests.ui.auth import AppUiAuth
from tests.ui.browser import BrowserSession
from tests.ui.pages.app.bill.bill_confirm_page import BillConfirmPage
from tests.ui.pages.app.bill.bill_services_page import BillServicesPage
from tests.ui.pages.app.bill.landline_inquiry_page import LandlineInquiryPage
from tests.ui.pages.app.hub_page import HubPage
from tests.ui.pages.app.login_page import LoginPage
from tests.ui.pages.app.wealth.ipg_gateway_page import IpgGatewayPage
from tests.ui.pages.app.wealth.receipt_page import ReceiptPage
from tests.ui.pages.app.wealth.silver_page import SilverPage
from tests.ui.pages.dashboard.bill_inquiry_modal import DashboardBillInquiryModal
from tests.ui.pages.dashboard.bill_provider_weights_modal import (
    DashboardBillProviderWeightsModal,
)
from tests.ui.pages.dashboard.home_page import DashboardHomePage
from tests.ui.pages.dashboard.login_page import DashboardLoginPage
from tests.ui.pages.dashboard.operator_picker_modal import DashboardOperatorPickerModal
from tests.ui.pages.dashboard.super_app_page import DashboardSuperAppPage
from tests.ui.pages.dashboard.topup_provider_weights_modal import (
    DashboardTopupProviderWeightsModal,
)


@pytest.fixture
def browser_session(request: pytest.FixtureRequest, settings: Settings) -> Iterator[BrowserSession]:
    """One browser/context/page per test — port of Start Browser Session.

    On failure (setup or call phase), attaches a screenshot + Playwright trace to
    the Allure result before closing. On a pass, discards the trace to save disk.
    """
    session = BrowserSession(settings)
    yield session

    setup_rep = getattr(request.node, "rep_setup", None)
    call_rep = getattr(request.node, "rep_call", None)
    failed = bool((setup_rep and setup_rep.failed) or (call_rep and call_rep.failed))

    if failed:
        name = safe_name(request.node.name)
        png = session.capture_screenshot_bytes()
        if png:
            allure.attach(
                png, name=f"screenshot-{name}", attachment_type=allure.attachment_type.PNG
            )
        trace_path = session.save_trace(ALLURE_RESULTS_DIR / "traces" / f"{name}.zip")
        if trace_path and trace_path.exists():
            allure.attach.file(
                str(trace_path), name=f"trace-{name}", attachment_type=allure.attachment_type.ZIP
            )
    else:
        session.discard_trace()

    session.close()


@pytest.fixture
def page(browser_session: BrowserSession, settings: Settings) -> Page:
    """Open app origin; callers inject auth or navigate as needed."""
    return browser_session.start(settings.app_base_url)


@pytest.fixture
def app_ui_auth(
    settings: Settings,
    app_client: ApiClient,
    redis_client: RedisClient,
    mysql_client: MySQLClient,
) -> AppUiAuth:
    """App UI auth helper (OTP login + cookie injection)."""
    return AppUiAuth(settings, app_client, redis_client, mysql_client)


@pytest.fixture
def hub_page(page: Page, settings: Settings) -> HubPage:
    """App hub page object."""
    return HubPage(
        page,
        settings.app_base_url,
        hub_path=settings.hub_page_path,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def login_page(page: Page, settings: Settings) -> LoginPage:
    """App login page object."""
    return LoginPage(
        page,
        settings.app_base_url,
        settings.app_login_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def bill_services_page(page: Page, settings: Settings) -> BillServicesPage:
    """Bill services landing page object."""
    return BillServicesPage(
        page,
        settings.app_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def landline_inquiry_page(page: Page, settings: Settings) -> LandlineInquiryPage:
    """Landline bill inquiry page object."""
    return LandlineInquiryPage(
        page,
        settings.app_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def bill_confirm_page(page: Page, settings: Settings) -> BillConfirmPage:
    """Bill payment confirm page object."""
    return BillConfirmPage(
        page,
        settings.app_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def silver_page(page: Page, settings: Settings) -> SilverPage:
    """Wealth silver-trading page object (PLACEHOLDER — see silver_page.py TODOs)."""
    return SilverPage(
        page,
        settings.app_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def ipg_gateway_page(page: Page, settings: Settings) -> IpgGatewayPage:
    """External bank payment gateway page object (see module docstring)."""
    return IpgGatewayPage(
        page,
        settings.app_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def receipt_page(page: Page, settings: Settings) -> ReceiptPage:
    """Wealth purchase/sale receipt page object."""
    return ReceiptPage(
        page,
        settings.app_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def dashboard_login_page(page: Page, settings: Settings) -> DashboardLoginPage:
    """Dashboard login page object."""
    return DashboardLoginPage(
        page,
        settings.dashboard_base_url,
        settings.dashboard_login_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def dashboard_home_page(page: Page, settings: Settings) -> DashboardHomePage:
    """Dashboard home page object."""
    return DashboardHomePage(
        page,
        settings.dashboard_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def dashboard_super_app_page(page: Page, settings: Settings) -> DashboardSuperAppPage:
    """Dashboard super-app page object."""
    return DashboardSuperAppPage(
        page,
        settings.dashboard_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def dashboard_bill_inquiry_modal(page: Page, settings: Settings) -> DashboardBillInquiryModal:
    """Dashboard bill inquiry modal page object."""
    return DashboardBillInquiryModal(
        page,
        settings.dashboard_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def dashboard_bill_provider_weights_modal(
    page: Page, settings: Settings
) -> DashboardBillProviderWeightsModal:
    """Dashboard bill provider-weights modal page object."""
    return DashboardBillProviderWeightsModal(
        page,
        settings.dashboard_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def dashboard_operator_picker_modal(page: Page, settings: Settings) -> DashboardOperatorPickerModal:
    """Dashboard operator picker modal page object."""
    return DashboardOperatorPickerModal(
        page,
        settings.dashboard_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )


@pytest.fixture
def dashboard_topup_provider_weights_modal(
    page: Page, settings: Settings
) -> DashboardTopupProviderWeightsModal:
    """Dashboard top-up provider-weights modal page object."""
    return DashboardTopupProviderWeightsModal(
        page,
        settings.dashboard_base_url,
        default_timeout_ms=settings.ui_default_timeout_ms,
    )
