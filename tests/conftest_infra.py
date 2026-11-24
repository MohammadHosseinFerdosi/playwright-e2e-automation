"""Infrastructure fixtures — settings, HTTP/DB clients, factories, tokens.

Imported into ``tests/conftest.py`` (pytest only auto-loads that entry point).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.api.client import ApiClient, ApiSide
from tests.api.tci.client import TciClient
from tests.config.settings import Settings
from tests.services.auth import login_business, login_to_dashboard
from tests.services.bill_ids import BillIdService
from tests.services.db.mongo_client import MongoDbClient
from tests.services.db.mysql_client import MySQLClient
from tests.services.db.redis_client import RedisClient
from tests.services.factories import BusinessFactory, UserFactory
from tests.services.gl_admin_session import load_gl_admin_session, resolve_gl_admin_cookie
from tests.services.telephone_pool import TelephoneBillPool, load_telephone_bill_pool
from tests.services.wallet_initializer import WalletInitializer
from tests.ui.auth import DashboardUiAuth


@pytest.fixture(scope="session")
def settings(request: pytest.FixtureRequest) -> Settings:
    """Session settings with optional CLI overrides for UI browser behaviour."""
    overrides: dict[str, object] = {}
    view_mode = request.config.getoption("--ui-view-mode")
    if view_mode:
        overrides["ui_view_mode"] = view_mode
    if request.config.getoption("--headed"):
        overrides["ui_browser_alias"] = "CHROME"
    slow_mo = request.config.getoption("--slow-mo")
    if slow_mo:
        overrides["ui_slow_mo_ms"] = slow_mo
    return Settings(**overrides)  # type: ignore[arg-type]


@pytest.fixture(scope="session")
def microservice_client(settings: Settings) -> Iterator[ApiClient]:
    """Session-scoped microservice ``ApiClient`` closed at session end."""
    client = ApiClient(settings, ApiSide.MICROSERVICE)
    yield client
    client.close()


@pytest.fixture
def mysql_client(settings: Settings) -> Iterator[MySQLClient]:
    """Function-scoped MySQL client — one instance per test, closed on teardown.

    Replaces Robot's global ``_connection``/``_cursor`` pattern for xdist safety.
    """
    with MySQLClient(settings) as client:
        yield client


@pytest.fixture
def redis_client(settings: Settings) -> Iterator[RedisClient]:
    """Function-scoped Redis client — one instance per test, closed on teardown.

    Supports ``standalone`` and ``second_standalone`` masters (sentinel not yet).
    """
    with RedisClient(settings) as client:
        yield client


@pytest.fixture
def mongo_client(settings: Settings) -> Iterator[MongoDbClient]:
    """Function-scoped MongoDB client — xdist-safe, no module globals."""
    with MongoDbClient(settings) as client:
        yield client


@pytest.fixture
def app_client(settings: Settings) -> Iterator[ApiClient]:
    """APP-side client with ``APP_BASIC_AUTH`` — for send-sms / activate / login."""
    with ApiClient(settings, ApiSide.APP, auth_header=settings.app_basic_auth) as client:
        yield client


@pytest.fixture
def business_factory(microservice_client: ApiClient) -> BusinessFactory:
    """Fresh-business factory on the microservice side."""
    return BusinessFactory(microservice_client)


@pytest.fixture
def user_factory(
    app_client: ApiClient,
    redis_client: RedisClient,
    mysql_client: MySQLClient,
) -> UserFactory:
    """Fresh app-user factory — port of Generate A Fresh User."""
    return UserFactory(app_client, redis_client, mysql_client)


@pytest.fixture
def wallet_initializer(
    microservice_client: ApiClient,
    user_factory: UserFactory,
    business_factory: BusinessFactory,
    settings: Settings,
) -> Iterator[WalletInitializer]:
    """User/business wallet create/charge with mandatory Collect All Amount teardown.

    Always sweeps remaining balances back to the test business on fixture
    teardown — do not skip this, or shared UAT wallet state drifts.
    """
    initializer = WalletInitializer(
        microservice_client,
        user_factory,
        settings,
        business_factory=business_factory,
    )
    yield initializer
    initializer.collect_all_amounts()


@pytest.fixture
def bill_id_service() -> BillIdService:
    """Checksum-valid billId/payId helpers for bill-mng validation suites."""
    return BillIdService()


@pytest.fixture(scope="session")
def telephone_bill_pool(settings: Settings) -> TelephoneBillPool:
    """Curated landline / TCI pool from gitignored secrets YAML."""
    return load_telephone_bill_pool(settings)


@pytest.fixture
def gl_admin_session(settings: Settings, dashboard_client: ApiClient) -> str:
    """GL admin session Cookie — derived from a dashboard login when possible.

    Falls back to the gitignored secrets YAML (skips if that's also unset).
    Function-scoped (like ``dashboard_client``) so each test gets a fresh
    login rather than reusing one that may have expired mid-run.
    """
    return resolve_gl_admin_cookie(dashboard_client, settings, load_gl_admin_session(settings))


@pytest.fixture
def tci_client(telephone_bill_pool: TelephoneBillPool) -> Iterator[TciClient | None]:
    """TCI proxy client — ``None`` when credentials are absent (steps skip)."""
    creds = telephone_bill_pool.tci
    if creds is None:
        yield None
        return
    client = TciClient(creds)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def dashboard_client(settings: Settings) -> Iterator[ApiClient]:
    """DASHBOARD-side client with ``DASHBOARD_BASIC_AUTH``."""
    auth = settings.dashboard_basic_auth or None
    with ApiClient(settings, ApiSide.DASHBOARD, auth_header=auth) as client:
        yield client


@pytest.fixture
def dashboard_ui_auth(
    settings: Settings,
    dashboard_client: ApiClient,
    microservice_client: ApiClient,
) -> DashboardUiAuth:
    """Dashboard UI auth helper (cookie / token injection)."""
    return DashboardUiAuth(settings, dashboard_client, microservice_client)


@pytest.fixture
def platform_business_token(settings: Settings) -> str:
    """Login as the Platform business — shared across payment steps that need it.

    Matches Robot's ``Login For Business ${PLATFORM_UESERNAME} ${PLATFORM_PASSWORD}``.
    """
    with ApiClient(
        settings, ApiSide.GENERAL, auth_header=settings.business_basic_auth
    ) as login_client:
        return login_business(login_client, settings.platform_username, settings.platform_password)


@pytest.fixture
def company_business_token(settings: Settings) -> str:
    """Login as the Company business.

    Matches Robot's ``Login For Business ${COMPANY_USERNAME} ${COMPANY_PASSWORD}``.
    """
    with ApiClient(
        settings, ApiSide.GENERAL, auth_header=settings.business_basic_auth
    ) as login_client:
        return login_business(login_client, settings.company_username, settings.company_password)


@pytest.fixture
def dashboard_access_token(dashboard_client: ApiClient, settings: Settings) -> str:
    """Staff OAuth access token for dashboard admin APIs."""
    auth = login_to_dashboard(
        dashboard_client, settings.dashboard_username, settings.dashboard_password
    )
    return auth["access_token"]
