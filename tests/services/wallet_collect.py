"""Wallet teardown/collect collaborators for ``WalletInitializer``.

Sweeps customer and business balances back to the shared charge-test business.
"""

from __future__ import annotations

from tests.api.client import ApiClient
from tests.api.nemo.admin.businesses_config_search import (
    BusinessWalletsConfigSearchBody,
    post_admin_wallets_businesses_config_search,
)
from tests.api.wallet_provider.transactions.business_transfer import (
    post_transactions_business_transfer,
)
from tests.api.wallet_provider.transactions.spend_payex import post_transactions_spend_payex
from tests.api.wallet_provider.transactions.spend_verify import post_transactions_spend_verify
from tests.api.wallet_provider.wallets.admin_users import get_admin_wallets_users
from tests.api.wallet_provider.wallets.businesses_balance import (
    BusinessWalletBalanceBody,
    get_wallets_businesses_balance,
)
from tests.config.constants import BUSINESS_TYPE, CURRENCY_IRR, CUSTOMER_TYPE
from tests.config.settings import Settings
from tests.services.api_assert import ensure_ok
from tests.services.tracking import random_tracking_code
from tests.services.wallet_charge import WalletChargeCollaborator


class WalletCollectCollaborator:
    """Collect leftover balances for charged users/businesses on teardown."""

    def __init__(
        self,
        client: ApiClient,
        settings: Settings,
        charge: WalletChargeCollaborator,
    ) -> None:
        self._client = client
        self._settings = settings
        self._charge = charge

    def collect_handler(self, user_list: list[dict[str, str]], currency: str) -> None:
        """Port of Collect Handler — customer spend-back + business transfer-back.

        Args:
            user_list: Entries shaped ``{"user_id": ..., "type": customer|business}``.
            currency: Currency code for the customer collect pass.
        """
        for user in user_list:
            user_type = user["type"]
            if user_type == CUSTOMER_TYPE:
                self._collect_customer(user["user_id"], currency)
            elif user_type == BUSINESS_TYPE:
                # Business teardown discovers wallets via Nemo config search and
                # transfers each positive balance once; currency loop is a no-op
                # for the second pass once balances are zero.
                if currency == CURRENCY_IRR:
                    self._collect_business(user["user_id"])
            else:
                raise ValueError(f"Unknown user type for teardown: {user_type!r}")

    def _collect_customer(self, user_id: str, currency: str) -> None:
        result = get_admin_wallets_users(self._client, user_id, currency)
        body = result.get("body")
        if result["status_code"] != 200 or not isinstance(body, dict):
            raise RuntimeError(
                f"Admin wallet balances lookup failed for user_id={user_id} "
                f"currency={currency}: status_code={result['status_code']} body={body}"
            )
        balances = body.get("balances") or []
        for item in balances:
            balance = item.get("balance") or 0
            if balance > 0:
                self._spend_to_business_wallet_for_teardown(
                    user_id,
                    balance,
                    item["walletName"],
                    currency,
                )

    def _collect_business(self, business_id: str) -> None:
        restrictions = [
            {
                "type": "collection",
                "field": "businessIds",
                "values": [business_id],
            }
        ]
        search = post_admin_wallets_businesses_config_search(
            self._client, restrictions=restrictions, orders=[]
        )
        body = search.get("body")
        if search["status_code"] != 200 or not isinstance(body, BusinessWalletsConfigSearchBody):
            raise RuntimeError(
                f"Business wallet config search failed for business_id={business_id}: "
                f"status_code={search['status_code']} body={body}"
            )

        for wallet in body.wallets:
            balance_result = get_wallets_businesses_balance(
                self._client, business_id, wallet.wallet_name
            )
            balance_body = balance_result.get("body")
            if balance_result["status_code"] != 200 or not isinstance(
                balance_body, BusinessWalletBalanceBody
            ):
                raise RuntimeError(
                    f"Business balance lookup failed for business_id={business_id} "
                    f"wallet={wallet.wallet_name!r}: {balance_body}"
                )
            if balance_body.balance <= 0:
                continue
            dest_wallet = self._charge.charge_source_wallet_for_currency(balance_body.currency)
            ensure_ok(
                post_transactions_business_transfer(
                    self._client,
                    source_business_id=business_id,
                    source_wallet_name=wallet.wallet_name,
                    destination_business_id=self._settings.business_id_for_charge_test_wallets,
                    destination_wallet_name=dest_wallet,
                    amount=balance_body.balance,
                    currency=balance_body.currency,
                    tracking_code=random_tracking_code(12),
                ),
                context=(
                    f"Collect business wallet {wallet.wallet_name!r} for business_id={business_id}"
                ),
            )

    def _spend_to_business_wallet_for_teardown(
        self,
        user_id: str,
        amount: int,
        wallet_name: str,
        currency: str,
    ) -> None:
        dest_wallet = self._charge.charge_source_wallet_for_currency(currency)
        source_list = [{"userId": user_id, "walletName": wallet_name, "amount": amount}]
        destinations = [
            {
                "businessId": self._settings.business_id_for_charge_test_wallets,
                "walletName": dest_wallet,
                "amount": amount,
            }
        ]
        pay_result = ensure_ok(
            post_transactions_spend_payex(self._client, source_list, destinations, currency),
            context=f"Spend-pay teardown for user_id={user_id} wallet={wallet_name!r}",
        )

        pay_body = pay_result["body"] or {}
        ensure_ok(
            post_transactions_spend_verify(
                self._client,
                pay_body["trackingCode"],
                pay_body["confirmationCode"],
            ),
            context=f"Spend-verify teardown for user_id={user_id} wallet={wallet_name!r}",
        )
