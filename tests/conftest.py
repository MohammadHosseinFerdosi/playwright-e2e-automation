"""Shared pytest fixtures — thin orchestrator for xdist-safe wiring.

Platform owner approves changes — see ``.cursor/rules/pytest-architecture.mdc``.

Every framework class (Settings, ApiClient, factories) is wired here via a
fixture, never imported as a module-level singleton — this is what makes
``pytest -n auto`` (xdist) safe.

Split is intentional (platform owner): reporting hooks, infrastructure
fixtures, and UI page fixtures live in sibling modules imported below.
Pytest only auto-loads this file, so imports keep discovery working.
"""

from tests.conftest_infra import (  # noqa: F401
    app_client,
    bill_id_service,
    business_factory,
    dashboard_access_token,
    dashboard_client,
    dashboard_ui_auth,
    company_business_token,
    platform_business_token,
    gl_admin_session,
    microservice_client,
    mongo_client,
    mysql_client,
    redis_client,
    settings,
    tci_client,
    telephone_bill_pool,
    user_factory,
    wallet_initializer,
)
from tests.conftest_reporting import (  # noqa: F401
    pytest_addoption,
    pytest_bdd_apply_tag,
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_runtest_makereport,
    pytest_sessionstart,
    pytest_terminal_summary,
)
from tests.conftest_ui import (  # noqa: F401
    app_ui_auth,
    bill_confirm_page,
    bill_services_page,
    browser_session,
    dashboard_bill_inquiry_modal,
    dashboard_bill_provider_weights_modal,
    dashboard_home_page,
    dashboard_login_page,
    dashboard_operator_picker_modal,
    dashboard_super_app_page,
    dashboard_topup_provider_weights_modal,
    hub_page,
    ipg_gateway_page,
    landline_inquiry_page,
    login_page,
    page,
    receipt_page,
    silver_page,
)
