"""User/business wallet create/charge + balance-sweep teardown.

Port of ``src/services/backend/user-wallet-initializer-service.resource``:

- Customer: ``Get Initialized User With Charged Wallet Based On Configuration``
- Business: ``Get Initialized Business With Charged Wallet Based On Configuration``
- Teardown: ``Collect All Amount For Tear Down`` (customer spend-back + business transfer)

Business charge uses the shared charge-test business via business-transfer
(same as Robot) — Nemo admin cash-in is not required for this path.

Always run ``collect_all_amounts()`` after charging (wired via the
``wallet_initializer`` fixture teardown) so shared UAT balances do not drift.

Charge vs collect HTTP sequences live in collaborator modules; this class owns
registration + orchestration only.
"""

from __future__ import annotations

import time
from typing import Any

from tests.api.client import ApiClient, ApiSide
from tests.api.wallet_provider.wallets.total_balance import (
    TotalBalanceBody,
    get_wallets_users_total_balance,
)
from tests.config.constants import (
    BUSINESS_TYPE,
    CURRENCY_CRR,
    CURRENCY_IRR,
    CUSTOMER_TYPE,
)
from tests.config.settings import Settings
from tests.services.factories import Business, BusinessFactory, User, UserFactory
from tests.services.wallet_charge import WalletChargeCollaborator
from tests.services.wallet_collect import WalletCollectCollaborator
from tests.services.wallet_models import (
    BusinessWalletChargeConfig,
    BusinessWalletInfo,
    ChargedBusiness,
    ChargedUser,
    WalletChargeConfig,
    WalletInfo,
)

WALLET_EXPIRY_POLL_INTERVAL_SECONDS = 0.5
WALLET_EXPIRY_POLL_TIMEOUT_SECONDS = 60.0

__all__ = [
    "BusinessWalletChargeConfig",
    "BusinessWalletInfo",
    "ChargedBusiness",
    "ChargedUser",
    "WalletChargeConfig",
    "WalletInfo",
    "WalletInitializer",
]


class WalletInitializer:
    """Instance-owned charge list replaces Robot's suite-global list.

    ``@{CREATED_USER_LIST_IN_INITIAL_SECTION}`` is an instance attribute here.
    """

    def __init__(
        self,
        client: ApiClient,
        user_factory: UserFactory,
        settings: Settings,
        business_factory: BusinessFactory | None = None,
    ) -> None:
        if client.side is not ApiSide.MICROSERVICE:
            raise ValueError("WalletInitializer requires an ApiClient on the microservice side")
        self._client = client
        self._user_factory = user_factory
        self._business_factory = business_factory
        self._settings = settings
        self._charge_list: list[dict[str, str]] = []
        self._charge = WalletChargeCollaborator(client, settings)
        self._collect = WalletCollectCollaborator(client, settings, self._charge)

    def register_for_teardown(self, user_id: str, user_type: str = CUSTOMER_TYPE) -> None:
        """Port of Set To User Charge List."""
        if user_type not in (CUSTOMER_TYPE, BUSINESS_TYPE):
            raise ValueError(f"user_type must be {CUSTOMER_TYPE!r} or {BUSINESS_TYPE!r}")
        self._charge_list.append({"user_id": user_id, "type": user_type})

    def create_fresh_user(self, cell_number_prefix: str) -> User:
        """Port of Get A Fresh User — creates a user and registers for teardown."""
        if len(cell_number_prefix) != 4:
            raise ValueError(
                f"Cell Number Prefix Length Must Be Equal 4 but Found: {cell_number_prefix!r}"
            )
        user = self._user_factory.create(cell_number_prefix=cell_number_prefix)
        self.register_for_teardown(user.user_id, CUSTOMER_TYPE)
        return user

    def create_user_with_charged_wallets(
        self,
        cell_number_prefix: str,
        wallets_config: list[WalletChargeConfig],
    ) -> ChargedUser:
        """Port of Get Initialized User With Charged Wallet Based On Configuration."""
        user = self.create_fresh_user(cell_number_prefix)
        return self._charge.attach_and_charge_user_wallets(user, wallets_config)

    def create_fresh_business(
        self,
        roles: list[str] | None = None,
        zone: str | None = None,
    ) -> Business:
        """Port of Create Business For Initialize — registers business for teardown."""
        factory = self._require_business_factory()
        business = factory.create(roles=roles, zone=zone)
        self.register_for_teardown(business.business_id, BUSINESS_TYPE)
        return business

    def create_business_with_charged_wallets(
        self,
        wallets_config: list[BusinessWalletChargeConfig] | None = None,
        roles: list[str] | None = None,
        zone: str | None = None,
    ) -> ChargedBusiness:
        """Port of Get Initialized Business With Charged Wallet Based On Configuration.

        Empty ``wallets_config`` creates a business with no wallets (still registered
        for teardown).
        """
        business = self.create_fresh_business(roles=roles, zone=zone)
        return self._charge.charge_business_wallets(business, wallets_config)

    def wait_until_time_bound_balance(
        self,
        user_id: str,
        wallets: list[WalletInfo],
        expected_time_bound_balance: int,
        timeout_seconds: float = WALLET_EXPIRY_POLL_TIMEOUT_SECONDS,
    ) -> None:
        """Poll MS total-balance until time-bound matches after gift expiry.

        No-op when no wallet in ``wallets`` was created with ``should_be_expired``.
        Waits past the latest ``expires_at_epoch`` by polling (no fixed sleep).
        """
        expiries = [
            w.expires_at_epoch for w in wallets if w.expired and w.expires_at_epoch is not None
        ]
        if not expiries:
            return

        # Poll until expiry has passed *and* balance settles — no upfront sleep.
        deadline = max(expiries) + timeout_seconds
        last_body: Any = None
        while time.time() < deadline:
            if time.time() >= max(expiries):
                result = get_wallets_users_total_balance(self._client, user_id=user_id)
                body = result.get("body")
                last_body = body
                if result["status_code"] == 200 and isinstance(body, TotalBalanceBody):
                    if body.time_bound_balance == expected_time_bound_balance:
                        return
            time.sleep(WALLET_EXPIRY_POLL_INTERVAL_SECONDS)

        raise TimeoutError(
            f"timeBoundBalance did not settle to {expected_time_bound_balance} "
            f"for user_id={user_id} within poll window; last body={last_body}"
        )

    def collect_all_amounts(
        self,
        additional_users: list[dict[str, str]] | None = None,
    ) -> None:
        """Port of Collect All Amount For Tear Down (customer + business)."""
        self._collect.collect_handler(self._charge_list, CURRENCY_IRR)
        self._collect.collect_handler(self._charge_list, CURRENCY_CRR)
        if additional_users:
            self._collect.collect_handler(additional_users, CURRENCY_IRR)
            self._collect.collect_handler(additional_users, CURRENCY_CRR)

    def _require_business_factory(self) -> BusinessFactory:
        if self._business_factory is None:
            raise RuntimeError(
                "BusinessFactory is required for business wallet operations; "
                "use the wallet_initializer fixture (or pass business_factory=...)"
            )
        return self._business_factory
