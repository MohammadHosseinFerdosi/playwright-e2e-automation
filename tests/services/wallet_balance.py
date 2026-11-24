"""Wallet total-balance context builders for aggregated-balance scenarios.

Owns Gherkin wallet-mix dispatch, expected-balance math, and total-balance
HTTP helpers so BDD steps stay thin orchestration.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient, ApiSide
from tests.api.wallet_provider.wallets.total_balance import (
    TotalBalanceBody,
    get_wallets_users_total_balance,
)
from tests.config.constants import (
    WALLET_DEFAULT_DEFINITION,
    WALLET_TIME_BOUND_DEFINITION,
)
from tests.config.settings import REPO_ROOT, Settings
from tests.services.assert_report import (
    AssertionReport,
    assert_isinstance,
    assert_status_ok,
)
from tests.services.wallet_initializer import (
    WalletChargeConfig,
    WalletInitializer,
)

_TOTAL_BALANCE_YAML = REPO_ROOT / "data" / "wallet" / "users-total-balance-variables.yaml"
_secure_rand = random.SystemRandom()


class TotalBalanceVariables(BaseModel):
    """Suite variables from ``users-total-balance-variables.yaml``."""

    model_config = ConfigDict(extra="ignore")

    user_cell_number_prefix: str = Field(alias="USER_CELL_NUMBER_PREFIX")
    invalid_user_id: str = Field(alias="INVALID_USER_ID")
    invalid_user_id_failure_content: dict[str, Any] = Field(alias="INVALID_USER_ID_FAILURE_CONTENT")


@lru_cache(maxsize=1)
def load_total_balance_variables(
    path: Path | None = None,
) -> TotalBalanceVariables:
    """Load and validate total-balance suite YAML once per process."""
    raw = yaml.safe_load((path or _TOTAL_BALANCE_YAML).read_text(encoding="utf-8")) or {}
    return TotalBalanceVariables.model_validate(raw)


@dataclass(frozen=True)
class BalanceContext:
    """Logged-in customer plus expected aggregate fields for assertions."""

    cell_number: str
    access_token: CHANGE_ME
    expected_balance: int
    expected_cashoutable: int
    expected_non_cashoutable: int
    expected_time_bound: int


@dataclass(frozen=True)
class _WalletMixPlan:
    """How to build wallets and expected aggregates for one Outline row."""

    configs: Callable[[int, int], list[WalletChargeConfig]]
    expects: Callable[[int, int], tuple[int, int, int, int]]
    wait_for_expiry: bool


def _charge_amount_pair() -> tuple[int, int]:
    """Match Robot Initialize User And Wallets: random 100–200, cashoutable = all - 50."""
    wallet_charge_amount = _secure_rand.randint(100, 200)
    cashoutable = wallet_charge_amount - 50
    return wallet_charge_amount, cashoutable


_WALLET_MIXES: dict[str, _WalletMixPlan] = {
    "default and time-bound wallets": _WalletMixPlan(
        configs=lambda amount, cashoutable: [
            WalletChargeConfig(
                definition=WALLET_TIME_BOUND_DEFINITION,
                should_be_expired=True,
                wallet_charge_amount=amount,
            ),
            WalletChargeConfig(
                definition=WALLET_TIME_BOUND_DEFINITION,
                wallet_charge_amount=amount,
            ),
            WalletChargeConfig(
                definition=WALLET_DEFAULT_DEFINITION,
                wallet_charge_amount=amount,
                cashoutable_charge_amount=cashoutable,
            ),
            WalletChargeConfig(
                definition=WALLET_TIME_BOUND_DEFINITION,
                wallet_charge_amount=0,
            ),
        ],
        expects=lambda amount, cashoutable: (
            amount + amount,
            cashoutable,
            amount - cashoutable,
            amount,
        ),
        wait_for_expiry=True,
    ),
    "only time-bound wallets": _WalletMixPlan(
        configs=lambda amount, _cashoutable: [
            WalletChargeConfig(
                definition=WALLET_TIME_BOUND_DEFINITION,
                should_be_expired=True,
                wallet_charge_amount=amount,
            ),
            WalletChargeConfig(
                definition=WALLET_TIME_BOUND_DEFINITION,
                wallet_charge_amount=amount,
            ),
            WalletChargeConfig(
                definition=WALLET_TIME_BOUND_DEFINITION,
                wallet_charge_amount=0,
            ),
        ],
        expects=lambda amount, _cashoutable: (amount, 0, 0, amount),
        wait_for_expiry=True,
    ),
    "only an expired time-bound wallet": _WalletMixPlan(
        configs=lambda amount, _cashoutable: [
            WalletChargeConfig(
                definition=WALLET_TIME_BOUND_DEFINITION,
                should_be_expired=True,
                wallet_charge_amount=amount,
            ),
        ],
        expects=lambda _amount, _cashoutable: (0, 0, 0, 0),
        wait_for_expiry=True,
    ),
    "only a default wallet": _WalletMixPlan(
        configs=lambda amount, cashoutable: [
            WalletChargeConfig(
                definition=WALLET_DEFAULT_DEFINITION,
                wallet_charge_amount=amount,
                cashoutable_charge_amount=cashoutable,
            ),
        ],
        expects=lambda amount, cashoutable: (
            amount,
            cashoutable,
            amount - cashoutable,
            0,
        ),
        wait_for_expiry=False,
    ),
    "only a cashoutable default wallet": _WalletMixPlan(
        configs=lambda amount, _cashoutable: [
            WalletChargeConfig(
                definition=WALLET_DEFAULT_DEFINITION,
                wallet_charge_amount=amount,
                cashoutable_charge_amount=amount,
            ),
        ],
        expects=lambda amount, _cashoutable: (amount, amount, 0, 0),
        wait_for_expiry=False,
    ),
    "only a non-cashoutable default wallet": _WalletMixPlan(
        configs=lambda amount, _cashoutable: [
            WalletChargeConfig(
                definition=WALLET_DEFAULT_DEFINITION,
                wallet_charge_amount=amount,
                cashoutable_charge_amount=0,
            ),
        ],
        expects=lambda amount, _cashoutable: (amount, 0, amount, 0),
        wait_for_expiry=False,
    ),
}

WALLET_MIX_STEP = r"^a logged-in customer with (?P<wallet_mix>[A-Za-z0-9 -]+)$"


def known_wallet_mixes() -> list[str]:
    """Registered Outline wallet-mix keys, for the regex unit test."""
    return sorted(_WALLET_MIXES)


class WalletBalanceService:
    """Build BalanceContext rows and fetch aggregated balance over HTTP."""

    def __init__(
        self,
        settings: Settings,
        wallet_initializer: WalletInitializer,
    ) -> None:
        self._settings = settings
        self._wallet_initializer = wallet_initializer
        self._vars = load_total_balance_variables()

    @property
    def unknown_user_id(self) -> str:
        """Configured user id that does not exist in UAT."""
        return self._vars.invalid_user_id

    @property
    def invalid_user_failure_content(self) -> dict[str, Any]:
        """Expected ``body.result`` when total-balance is called for an unknown user."""
        return self._vars.invalid_user_id_failure_content

    def build_for_mix(self, wallet_mix: str) -> BalanceContext:
        """Create a charged customer matching a Scenario Outline wallet mix.

        Args:
            wallet_mix: Outline key from
                ``a logged-in customer with {wallet_mix}``.

        Returns:
            Context with access token and expected aggregate balances.

        Raises:
            KeyError: Unknown mix — lists registered Outline keys.
        """
        plan = _WALLET_MIXES.get(wallet_mix)
        if plan is None:
            raise KeyError(f"No wallet mix for {wallet_mix!r}; known mixes: {known_wallet_mixes()}")

        amount, cashoutable = _charge_amount_pair()
        user = self._wallet_initializer.create_user_with_charged_wallets(
            self._vars.user_cell_number_prefix,
            plan.configs(amount, cashoutable),
        )
        expected_balance, expected_cashoutable, expected_non, expected_tb = plan.expects(
            amount, cashoutable
        )
        if plan.wait_for_expiry:
            self._wallet_initializer.wait_until_time_bound_balance(
                user.user_id,
                user.wallets,
                expected_tb,
            )
        return self._require_token_context(
            cell_number=user.user_cell_number,
            access_token=CHANGE_ME
            expected_balance=expected_balance,
            expected_cashoutable=expected_cashoutable,
            expected_non_cashoutable=expected_non,
            expected_time_bound=expected_tb,
        )

    def build_without_wallet(self) -> BalanceContext:
        """Create a fresh logged-in customer with no wallets (all balances zero)."""
        user = self._wallet_initializer.create_fresh_user(self._vars.user_cell_number_prefix)
        return self._require_token_context(
            cell_number=user.user_cell_number,
            access_token=CHANGE_ME
            expected_balance=0,
            expected_cashoutable=0,
            expected_non_cashoutable=0,
            expected_time_bound=0,
        )

    def request_aggregated_balance(self, context: BalanceContext) -> dict[str, Any]:
        """GET total balance as the logged-in customer (APP side).

        Args:
            context: Customer token + expected aggregates (token used for auth).

        Returns:
            ``{status_code, body}`` envelope with a parsed ``TotalBalanceBody``.
        """
        with ApiClient(
            self._settings,
            ApiSide.APP,
            auth_header=f"Bearer {context.access_token}",
        ) as client:
            result = get_wallets_users_total_balance(client)
        assert_status_ok("Get total balance", result)
        assert_isinstance("Get total balance response body", result["body"], TotalBalanceBody)
        return result

    def request_unknown_user_balance(self, user_id: str) -> dict[str, Any]:
        """GET total balance for a user id that was never created (microservice side).

        Returns:
            Failure envelope; asserts status is not 200 and ``body.result`` exists.
        """
        with ApiClient(self._settings, ApiSide.MICROSERVICE) as client:
            result = get_wallets_users_total_balance(client, user_id=user_id)
        body = result.get("body")
        AssertionReport("Get total balance for unknown user").check(
            "HTTP status is a failure (not 200)",
            result["status_code"] != 200,
            detail=f"status_code={result['status_code']}",
        ).check(
            "body.result present",
            isinstance(body, dict) and "result" in body,
            detail=f"body={body!r}",
        ).attach_json("response", result).assert_all()
        return result

    @staticmethod
    def _require_token_context(
        *,
        cell_number: str,
        access_token: str | None,
        expected_balance: int,
        expected_cashoutable: int,
        expected_non_cashoutable: int,
        expected_time_bound: int,
    ) -> BalanceContext:
        if not access_token:
            raise RuntimeError(
                "Charged user missing access_token — UserFactory should return tokens "
                "from the create-time login"
            )
        return BalanceContext(
            cell_number=cell_number,
            access_token=CHANGE_ME
            expected_balance=expected_balance,
            expected_cashoutable=expected_cashoutable,
            expected_non_cashoutable=expected_non_cashoutable,
            expected_time_bound=expected_time_bound,
        )
