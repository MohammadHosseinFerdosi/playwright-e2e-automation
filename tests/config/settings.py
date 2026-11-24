"""Typed settings loaded from the shared legacy config file.

Defaults plus shared keys from ``config/environment-stage.yaml``.
Reuses the existing YAML — see docs/framework/target-framework.md "Config" row.

MS path prefixes live in ``tests/api/ms_paths.py`` (also YAML-sourced).
Business constants live in ``tests/config/constants.py`` (CONSTANTS.yaml).
"""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_YAML = REPO_ROOT / "config" / "environment-stage.yaml"


class Settings(BaseSettings):
    """Typed Platform UAT settings loaded from ``config/environment-stage.yaml``."""

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    # --- Base URLs ---
    app_base_url: str = Field(validation_alias=AliasChoices("APP_BASE_URL"))
    microservice_base_url: str = Field(validation_alias=AliasChoices("MICROSERVICE_BASE_URL"))
    dashboard_base_url: str = Field(validation_alias=AliasChoices("DASHBOARD_BASE_URL"))
    general_base_url: str = Field(validation_alias=AliasChoices("GENERAL_BASE_URL"))
    web_base_url: str = Field(default="", validation_alias=AliasChoices("WEB_BASE_URL"))
    db_base_url: str = Field(default="", validation_alias=AliasChoices("DB_BASE_URL"))
    gateway_path: str = Field(validation_alias=AliasChoices("GATEWAY_PATH"))

    mockit_routes_url: str = Field(default="", validation_alias=AliasChoices("MOCKIT_ROUTES_URL"))
    mockit_url: str = Field(default="", validation_alias=AliasChoices("MOCKIT_URL"))
    mockit_url_2: str = Field(default="", validation_alias=AliasChoices("MOCKIT_URL_2"))
    charisma_url: str = Field(default="", validation_alias=AliasChoices("CHARISMA_URL"))

    session_default_timeout: float | None = Field(
        default=None, validation_alias=AliasChoices("SESSION_DEFAULT_TIMEOUT")
    )
    session_default_verify: bool = Field(
        default=True, validation_alias=AliasChoices("SESSION_DEFAULT_VERIFY")
    )

    # --- Auth / business identities ---
    business_basic_auth: str = Field(validation_alias=AliasChoices("BUSINESS_BASIC_AUTH"))
    app_basic_auth: str = Field(validation_alias=AliasChoices("APP_BASIC_AUTH"))
    platform_username: str = Field(validation_alias=AliasChoices("PLATFORM_UESERNAME"))
    platform_password: str = Field(validation_alias=AliasChoices("PLATFORM_PASSWORD"))
    platform_business_id: str = Field(
        default="", validation_alias=AliasChoices("PLATFORM_BUSINESS_ID")
    )
    platform_coupon_funder_wallet_name: str = Field(
        default="refund",
        validation_alias=AliasChoices("PLATFORM_COUPON_FUNDER_WALLET_NAME"),
    )
    company_username: str = Field(validation_alias=AliasChoices("COMPANY_USERNAME"))
    company_password: str = Field(validation_alias=AliasChoices("COMPANY_PASSWORD"))
    company_business_id: str = Field(
        default="", validation_alias=AliasChoices("COMPANY_BUSINESS_ID")
    )
    company_user_id: str = Field(default="", validation_alias=AliasChoices("COMPANY_USER_ID"))
    user_access_username: str = Field(
        default="", validation_alias=AliasChoices("USER_ACCESS_USERNAME")
    )
    user_access_password: str = Field(
        default="", validation_alias=AliasChoices("USER_ACCESS_PASSWORD")
    )

    # MySQL — used by MySQLClient (port of mysql-db-service.resource config builder)
    mysql_db_default_host: str = Field(validation_alias=AliasChoices("MYSQL_DB_DEFAULT_HOST"))
    mysql_db_default_port: int = Field(validation_alias=AliasChoices("MYSQL_DB_DEFAULT_PORT"))
    mysql_db_default_pass: str = Field(validation_alias=AliasChoices("MYSQL_DB_DEFAULT_PASS"))
    wallet_provider_mysql_db_host: str = Field(
        validation_alias=AliasChoices("WALLET_PROVIDER_MYSQL_DB_HOST")
    )
    wallet_provider_mysql_db_pass: str = Field(
        validation_alias=AliasChoices("WALLET_PROVIDER_MYSQL_DB_PASS")
    )
    general_ledger_mysql_db_host: str = Field(
        validation_alias=AliasChoices("GENERAL_LEDGER_MYSQL_DB_HOST")
    )
    general_ledger_mysql_db_pass: str = Field(
        validation_alias=AliasChoices("GENERAL_LEDGER_MYSQL_DB_PASS")
    )

    # Redis — sentinel-backed master used by RedisClient for OTP; second for later ports
    redis_platform_sentinel_hosts: list[str] = Field(
        validation_alias=AliasChoices("REDIS_PLATFORM_SENTINEL_HOSTS")
    )
    redis_platform_sentinel_master_name: str = Field(
        validation_alias=AliasChoices("REDIS_PLATFORM_SENTINEL_MASTER_NAME")
    )
    redis_platform_second_standalone_host: str = Field(
        default="",
        validation_alias=AliasChoices("REDIS_PLATFORM_SECOND_STANDALONE_HOST"),
    )
    redis_platform_second_standalone_port: int = Field(
        default=0,
        validation_alias=AliasChoices("REDIS_PLATFORM_SECOND_STANDALONE_PORT"),
    )

    # Mongo — connection defaults for future MongoClient (B5)
    mongo_db_default_host: str = Field(
        default="", validation_alias=AliasChoices("MONGO_DB_DEFAULT_HOST", "HOST")
    )
    mongo_db_default_port: int = Field(
        default=27017, validation_alias=AliasChoices("MONGO_DB_DEFAULT_PORT", "PORT")
    )
    mongo_db_default_pass: str = Field(
        default="",
        validation_alias=AliasChoices("MONGO_DB_DEFAULT_PASS", "PASSWORD"),
    )
    purchase_mng_db_name: str = Field(
        default="", validation_alias=AliasChoices("PURCHASE_MNG_DB_MANE")
    )
    purchase_mng_purchase_collection: str = Field(
        default="purchases",
        validation_alias=AliasChoices("PURCHASE_MNG_PURCHASE_COLLECTION"),
    )
    tgs_db_name: str = Field(default="", validation_alias=AliasChoices("TGS_DB_NAME"))
    nemo_db_name: str = Field(default="", validation_alias=AliasChoices("NEMO_DB_NAME"))
    report_mng_db_name: str = Field(default="", validation_alias=AliasChoices("REPORT_MNG_DB_NAME"))
    refund_db_name: str = Field(default="", validation_alias=AliasChoices("REFUND_DB_NAME"))
    switch_psp_db_name: str = Field(default="", validation_alias=AliasChoices("SWITCH_PSP_DB_NAME"))
    switch_psp_terminals_collection: str = Field(
        default="terminals",
        validation_alias=AliasChoices("SWITCH_PSP_TERMINALS_COLLECTION"),
    )
    switch_psp_ipg_details_choice: str = Field(
        default="ipg_choice_details",
        validation_alias=AliasChoices("SWITCH_PSP_IPG_DETAILS_CHOICE"),
    )
    credit_user: str = Field(default="", validation_alias=AliasChoices("CREDIT_USER"))
    digital_signature_user: str = Field(
        default="", validation_alias=AliasChoices("DIGITAL_SIGNATURE_USER")
    )
    score_user: str = Field(default="", validation_alias=AliasChoices("SCORE_USER"))
    underwriting_user: str = Field(default="", validation_alias=AliasChoices("underwriting_USER"))
    app_subscription_user: str = Field(
        default="", validation_alias=AliasChoices("APP_SUBSCRIPTION_USER")
    )

    # Postgres — for future PostgresClient (PCM / TMS)
    postgres_db_collateral_management_host: str = Field(
        default="",
        validation_alias=AliasChoices("POSTGRES_DB_COLLATERAL_MANAGEMENT_HOST"),
    )
    postgres_db_collateral_management_port: int = Field(
        default=5432,
        validation_alias=AliasChoices("POSTGRES_DB_COLLATERAL_MANAGEMENT_PORT"),
    )
    postgres_db_collateral_management_user: str = Field(
        default="",
        validation_alias=AliasChoices("POSTGRES_DB_COLLATERAL_MANAGEMENT_USER"),
    )
    postgres_db_collateral_management_pass: str = Field(
        default="",
        validation_alias=AliasChoices("POSTGRES_DB_COLLATERAL_MANAGEMENT_PASS"),
    )
    postgres_db_treasury_statement_user: str = Field(
        default="",
        validation_alias=AliasChoices("POSTGRES_DB_TREASURY_STATMENT_USER"),
    )
    postgres_db_treasury_statement_pass: str = Field(
        default="",
        validation_alias=AliasChoices("POSTGRES_DB_TREASURY_STATMENT_PASS"),
    )

    # RabbitMQ — for future queue client
    rabbitmq_url: str = Field(default="", validation_alias=AliasChoices("RABBITMQ_URL"))
    rabbitmq_port: int = Field(default=0, validation_alias=AliasChoices("RABBITMQ_PORT"))
    rabbitmq_user: str = Field(default="", validation_alias=AliasChoices("RABBITMQ_USER"))
    rabbitmq_pass: str = Field(default="", validation_alias=AliasChoices("RABBITMQ_PASS"))

    # Wallet charge / teardown source business (user-wallet-initializer-service)
    business_id_for_charge_test_wallets: str = Field(
        validation_alias=AliasChoices("BUSINESS_ID_FOR_CHARGE_TEST_WALLETS")
    )
    business_wallet_for_charge_test_wallets: str = Field(
        validation_alias=AliasChoices("BUSINESS_WALLET_FOR_CHARGE_TEST_WALLETS")
    )
    business_wallet_for_charge_credit_test_wallets: str = Field(
        validation_alias=AliasChoices("BUSINESS_WALLET_FOR_CHARGE_CREDIT_TEST_WALLETS")
    )

    # Landline / TCI Option E pool (gitignored YAML — see secrets/*.example.yaml)
    telephone_bills_secrets_path: str = Field(
        default="secrets/uat_telephone_bills.yaml",
        validation_alias=AliasChoices("TELEPHONE_BILLS_SECRETS_PATH"),
    )

    # GL admin session Cookie for the manual financial-transactions endpoint —
    # gitignored YAML, see secrets/uat_gl_admin_session.example.yaml.
    gl_admin_session_secrets_path: str = Field(
        default="secrets/uat_gl_admin_session.yaml",
        validation_alias=AliasChoices("GL_ADMIN_SESSION_SECRETS_PATH"),
    )

    # App / dashboard UI (Playwright)
    app_login_url: str = Field(validation_alias=AliasChoices("APP_LOGIN_URL"))
    app_hub_url: str = Field(validation_alias=AliasChoices("APP_HUB_URL"))
    hub_page_path: str = Field(default="/hub", validation_alias=AliasChoices("HUB_PAGE_PATH"))
    # Pre-KYC'd, funded UAT account — see config/environment-stage.yaml comment.
    wealth_silver_kyc_test_cell_number: str = Field(
        default="", validation_alias=AliasChoices("WEALTH_SILVER_KYC_TEST_CELL_NUMBER")
    )
    confirm_page_path: str = Field(
        default="/confirm", validation_alias=AliasChoices("CONFIRM_PAGE_PATH")
    )
    top_up_page_path: str = Field(
        default="/top-up", validation_alias=AliasChoices("TOP_UP_PAGE_PATH")
    )
    internet_page_path: str = Field(
        default="/internet", validation_alias=AliasChoices("INTERNET_PAGE_PATH")
    )
    internet_bundles_page_path: str = Field(
        default="/internet/purchase",
        validation_alias=AliasChoices("INTERNET_BUNDLES_PAGE_PATH"),
    )
    upg_page_path: str = Field(default="/web-pay", validation_alias=AliasChoices("UPG_PAGE_PATH"))
    ipg_mock_path: str = Field(default="/ipg-mock", validation_alias=AliasChoices("IPG_MOCK_PATH"))
    dashboard_login_url: str = Field(validation_alias=AliasChoices("DASHBOARD_LOGIN_URL"))
    dashboard_home_url: str = Field(default="", validation_alias=AliasChoices("DASHBOARD_HOME_URL"))
    dashboard_basic_auth: str = Field(
        default="", validation_alias=AliasChoices("DASHBOARD_BASIC_AUTH")
    )
    dashboard_username: str = Field(default="", validation_alias=AliasChoices("DASHBOARD_USERNAME"))
    dashboard_password: str = Field(default="", validation_alias=AliasChoices("DASHBOARD_PASSWORD"))

    # Playwright browser — aliases match Robot CONSTANTS (CHROME, HEADLESSCHROME, …)
    ui_browser_alias: str = Field(
        default="HEADLESSCHROME",
        validation_alias=AliasChoices("UI_BROWSER_ALIAS", "BROWSER_ALIAS"),
    )
    ui_default_timeout_ms: int = Field(
        default=20_000, validation_alias=AliasChoices("UI_DEFAULT_TIMEOUT_MS")
    )
    # Delay (ms) before every Playwright action — 0 by default; set >0 to
    # visually slow a run down (e.g. via the --slow-mo pytest flag).
    ui_slow_mo_ms: int = Field(default=0, validation_alias=AliasChoices("UI_SLOW_MO_MS"))
    ui_navigation_timeout_ms: int = Field(
        default=60_000, validation_alias=AliasChoices("UI_NAVIGATION_TIMEOUT_MS")
    )
    # "desktop" (default) or "mobile" — which viewport preset new browser
    # sessions use when a test doesn't request one explicitly.
    ui_view_mode: str = Field(default="desktop", validation_alias=AliasChoices("UI_VIEW_MODE"))
    ui_viewport_width: int = Field(default=1440, validation_alias=AliasChoices("UI_VIEWPORT_WIDTH"))
    ui_viewport_height: int = Field(
        default=900, validation_alias=AliasChoices("UI_VIEWPORT_HEIGHT")
    )
    ui_mobile_viewport_width: int = Field(
        default=390, validation_alias=AliasChoices("UI_MOBILE_VIEWPORT_WIDTH")
    )
    ui_mobile_viewport_height: int = Field(
        default=844, validation_alias=AliasChoices("UI_MOBILE_VIEWPORT_HEIGHT")
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Prefer constructor overrides, then the shared stage YAML file."""
        return (
            init_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=ENVIRONMENT_YAML),
        )
