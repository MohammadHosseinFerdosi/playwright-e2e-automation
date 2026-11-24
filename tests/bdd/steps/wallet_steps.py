"""Step definitions for tests/bdd/features/wallet/users_total_balance.feature."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.wallet_provider.wallets.total_balance import TotalBalanceBody
from tests.config.settings import Settings
from tests.services.assert_report import AssertionReport, assert_equals, assert_isinstance
from tests.services.wallet_balance import BalanceContext, WalletBalanceService
from tests.services.wallet_initializer import WalletInitializer

scenarios("../features/wallet/users_total_balance.feature")


@pytest.fixture
def wallet_balance_service(
    settings: Settings,
    wallet_initializer: WalletInitializer,
) -> WalletBalanceService:
    """Per-test WalletBalanceService for total-balance scenario setup and HTTP."""
    return WalletBalanceService(settings, wallet_initializer)


@given(
    parsers.re(r"^a logged-in customer with (?P<wallet_mix>[A-Za-z0-9 -]+)$"),
    target_fixture="balance_context",
)
def _(
    wallet_mix: str,
    wallet_balance_service: WalletBalanceService,
) -> BalanceContext:
    return wallet_balance_service.build_for_mix(wallet_mix.strip())


@given(
    "a logged-in customer without any wallet",
    target_fixture="balance_context",
)
def _(wallet_balance_service: WalletBalanceService) -> BalanceContext:
    return wallet_balance_service.build_without_wallet()


@given("an unknown user identity", target_fixture="unknown_user_id")
def _(wallet_balance_service: WalletBalanceService) -> str:
    return wallet_balance_service.unknown_user_id


@when(
    "the customer requests their aggregated balance",
    target_fixture="aggregated_balance_result",
)
def _(
    wallet_balance_service: WalletBalanceService,
    balance_context: BalanceContext,
) -> dict[str, Any]:
    return wallet_balance_service.request_aggregated_balance(balance_context)


@when(
    "the aggregated balance is requested for an unknown user",
    target_fixture="aggregated_balance_result",
)
def _(
    wallet_balance_service: WalletBalanceService,
    unknown_user_id: str,
) -> dict[str, Any]:
    return wallet_balance_service.request_unknown_user_balance(unknown_user_id)


@then("the aggregated balances match the expected amounts")
def _(balance_context: BalanceContext, aggregated_balance_result: dict[str, Any]) -> None:
    body = aggregated_balance_result["body"]
    assert_isinstance("Aggregated balance response body", body, TotalBalanceBody)
    AssertionReport("Aggregated balances match expected amounts").equals(
        "balance", actual=body.balance, expected=balance_context.expected_balance
    ).equals(
        "cashoutable_balance",
        actual=body.cashoutable_balance,
        expected=balance_context.expected_cashoutable,
    ).equals(
        "non_cashoutable_balance",
        actual=body.non_cashoutable_balance,
        expected=balance_context.expected_non_cashoutable,
    ).equals(
        "time_bound_balance",
        actual=body.time_bound_balance,
        expected=balance_context.expected_time_bound,
    ).assert_all()


@then("the aggregated balance response reports that the user was not found")
def _(
    aggregated_balance_result: dict[str, Any],
    wallet_balance_service: WalletBalanceService,
) -> None:
    assert_equals(
        "Aggregated balance failure reason",
        aggregated_balance_result["body"]["result"],
        wallet_balance_service.invalid_user_failure_content,
    )
