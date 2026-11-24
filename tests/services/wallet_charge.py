"""Wallet create/charge collaborators for ``WalletInitializer``.

Owns user-wallet payout and business-wallet create/charge HTTP sequences.
"""

from __future__ import annotations

import secrets
import string
import time

from tests.api.client import ApiClient
from tests.api.wallet_provider.admin.businesses import post_admin_wallets_businesses
from tests.api.wallet_provider.transactions.business_transfer import (
    post_transactions_business_transfer,
)
from tests.api.wallet_provider.transactions.payout import post_transactions_payout
from tests.api.wallet_provider.wallets.users import post_wallets_users
from tests.config.constants import (
    CURRENCY_CRR,
    CURRENCY_IRR,
    WALLET_DEFAULT_DEFINITION,
    WALLET_TIME_BOUND_DEFINITION,
)
from tests.config.settings import Settings
from tests.services.api_assert import ensure_ok
from tests.services.factories import Business, User
from tests.services.tracking import random_tracking_code
from tests.services.wallet_models import (
    BusinessWalletChargeConfig,
    BusinessWalletInfo,
    ChargedBusiness,
    ChargedUser,
    WalletChargeConfig,
    WalletInfo,
)

# Short TTL for gift wallets marked should_be_expired; callers poll until the
# aggregate time-bound balance settles (no fixed 40s Sleep clone from Robot).
WALLET_EXPIRATION_DELAY_SECONDS = 5


class WalletChargeCollaborator:
    """Create and fund user/business wallets via microservice APIs."""

    def __init__(self, client: ApiClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def attach_and_charge_user_wallets(
        self,
        user: User,
        wallets_config: list[WalletChargeConfig],
    ) -> ChargedUser:
        """Build wallets for ``user`` and payout configured amounts.

        Args:
            user: Fresh user already registered for teardown.
            wallets_config: Per-wallet create/charge instructions.

        Returns:
            Charged user snapshot including wallet names and totals.
        """
        wallets = self._build_wallets(user.user_id, wallets_config)
        total = self._payout_to_user_wallets(user.user_id, wallets)
        return ChargedUser(
            user_id=user.user_id,
            user_cell_number=user.user_cell_number,
            user_national_code=user.user_national_code,
            access_token=user.access_token,
            wallets=wallets,
            total_initial_amount=total,
        )

    def charge_business_wallets(
        self,
        business: Business,
        wallets_config: list[BusinessWalletChargeConfig] | None,
    ) -> ChargedBusiness:
        """Create and optionally fund business wallets on ``business``.

        Args:
            business: Fresh business already registered for teardown.
            wallets_config: Optional per-wallet create/charge instructions.

        Returns:
            Charged business snapshot.
        """
        wallets: list[BusinessWalletInfo] = []
        for config in wallets_config or []:
            self._create_business_wallet(business.business_id, config.definition, config.currency)
            initial = 0
            if config.wallet_charge_amount > 0:
                self._charge_business_wallet(
                    destination_business_id=business.business_id,
                    destination_wallet_name=config.definition,
                    amount=config.wallet_charge_amount,
                    currency=config.currency,
                )
                initial = config.wallet_charge_amount
            wallets.append(
                BusinessWalletInfo(
                    name=config.definition,
                    initial_amount=initial,
                    currency=config.currency,
                )
            )
        return ChargedBusiness(
            business_id=business.business_id,
            business_name=business.business_name,
            user_name=business.user_name,
            password=business.password,
            wallets=wallets,
        )

    def charge_source_wallet_for_currency(self, currency: str) -> str:
        """Resolve the shared charge-test business wallet name for ``currency``."""
        if currency == CURRENCY_IRR:
            return self._settings.business_wallet_for_charge_test_wallets
        if currency == CURRENCY_CRR:
            return self._settings.business_wallet_for_charge_credit_test_wallets
        raise ValueError(f"Unsupported currency for charge/teardown: {currency!r}")

    def _build_wallets(
        self,
        user_id: str,
        wallets_config: list[WalletChargeConfig],
    ) -> list[WalletInfo]:
        wallets: list[WalletInfo] = []
        for config in wallets_config:
            if config.definition == WALLET_TIME_BOUND_DEFINITION:
                suffix = "".join(secrets.choice(string.ascii_lowercase) for _ in range(8))
                now = int(time.time())
                if config.should_be_expired:
                    expires_at_epoch = float(now + WALLET_EXPIRATION_DELAY_SECONDS)
                    expiration_ms = int(expires_at_epoch * 1000)
                else:
                    expires_at_epoch = None
                    expiration_ms = (now * 1000) + 100_000_000

                wallet_name = self._create_wallet_for_user(
                    WALLET_TIME_BOUND_DEFINITION, suffix, user_id, expiration_ms
                )
                wallets.append(
                    WalletInfo(
                        name=wallet_name,
                        type=WALLET_TIME_BOUND_DEFINITION,
                        initial_amount=config.wallet_charge_amount,
                        expired=config.should_be_expired,
                        expires_at_epoch=expires_at_epoch,
                    )
                )
            elif config.definition == WALLET_DEFAULT_DEFINITION:
                wallets.append(
                    WalletInfo(
                        name=WALLET_DEFAULT_DEFINITION,
                        type=WALLET_DEFAULT_DEFINITION,
                        initial_amount=config.wallet_charge_amount,
                        cashoutable_amount=config.cashoutable_charge_amount,
                    )
                )
            else:
                raise ValueError(f"Wallet definition undefined in wallet list: {config!r}")
        return wallets

    def _create_wallet_for_user(
        self,
        definition_name: str,
        wallet_name: str,
        user_id: str,
        expiration_date: int,
    ) -> str:
        full_name = f"{definition_name}_{wallet_name}"
        ensure_ok(
            post_wallets_users(self._client, user_id, full_name, expiration_date=expiration_date),
            context=f"Create wallet {wallet_name!r} for user_id={user_id}",
        )
        return full_name

    def _create_business_wallet(
        self,
        business_id: str,
        wallet_name: str,
        currency: str = CURRENCY_IRR,
    ) -> None:
        ensure_ok(
            post_admin_wallets_businesses(
                self._client, business_id, wallet_name, currency=currency
            ),
            context=f"Create business wallet {wallet_name!r} for business_id={business_id}",
        )

    def _charge_business_wallet(
        self,
        destination_business_id: str,
        destination_wallet_name: str,
        amount: int,
        currency: str,
    ) -> None:
        source_wallet = self.charge_source_wallet_for_currency(currency)
        ensure_ok(
            post_transactions_business_transfer(
                self._client,
                source_business_id=self._settings.business_id_for_charge_test_wallets,
                source_wallet_name=source_wallet,
                destination_business_id=destination_business_id,
                destination_wallet_name=destination_wallet_name,
                amount=amount,
                currency=currency,
                tracking_code=random_tracking_code(18),
            ),
            context=(
                f"Charge business wallet {destination_wallet_name!r} "
                f"for business_id={destination_business_id}"
            ),
        )

    def _payout_to_user_wallets(self, user_id: str, wallets: list[WalletInfo]) -> int:
        total = 0
        description = "Payout from test business for pytest wallet initializer"
        for wallet in wallets:
            if wallet.initial_amount <= 0:
                continue
            sale_tracking_code = random_tracking_code(16)
            ensure_ok(
                post_transactions_payout(
                    self._client,
                    amount=wallet.initial_amount,
                    source_business_id=self._settings.business_id_for_charge_test_wallets,
                    source_business_wallet_name=(
                        self._settings.business_wallet_for_charge_test_wallets
                    ),
                    destination_user_id=user_id,
                    destination_user_wallet_name=wallet.name,
                    cashoutable_amount=wallet.cashoutable_amount,
                    sale_tracking_code=sale_tracking_code,
                    description=description,
                ),
                context=f"Payout wallet {wallet.name!r} to user_id={user_id}",
            )
            total += wallet.initial_amount
        return total
