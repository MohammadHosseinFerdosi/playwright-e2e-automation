"""Step definitions for tests/bdd/features/wallet/user_wallet_transfer.feature."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.config.settings import Settings
from tests.services.assert_report import assert_equals
from tests.services.transfer_service import TransferContext, TransferService
from tests.services.wallet_initializer import WalletInitializer

scenarios("../features/wallet/user_wallet_transfer.feature")


@pytest.fixture
def transfer_service(
    settings: Settings,
    wallet_initializer: WalletInitializer,
    microservice_client: ApiClient,
) -> TransferService:
    """Per-test TransferService wired to settings, initializer, and MS client."""
    return TransferService(settings, wallet_initializer, microservice_client)


@given(
    "a funded source customer and a destination customer",
    target_fixture="transfer_context",
)
def _(transfer_service: TransferService) -> TransferContext:
    return transfer_service.create_funded_pair()


@when("the source customer transfers a valid amount to the destination")
def _(
    transfer_service: TransferService,
    transfer_context: TransferContext,
) -> None:
    transfer_service.execute_valid_transfer(transfer_context)


@when(
    parsers.re(
        r"^the source customer attempts a transfer that is "
        r"(?P<condition>[A-Za-z0-9 -]+)$"
    ),
)
def _(
    condition: str,
    transfer_service: TransferService,
    transfer_context: TransferContext,
) -> None:
    transfer_service.attempt_invalid_transfer(condition, transfer_context)


@then("the source wallet balance decreases by the transfer amount")
def _(
    transfer_context: TransferContext,
    transfer_service: TransferService,
) -> None:
    assert_equals(
        "Source wallet balance decrease",
        transfer_service.source_balance_decrease(transfer_context),
        transfer_context.transfer_amount,
    )


@then("the destination wallet balance increases by the transfer amount")
def _(
    transfer_context: TransferContext,
    transfer_service: TransferService,
) -> None:
    assert_equals(
        "Destination wallet balance increase",
        transfer_service.dest_balance_increase(transfer_context),
        transfer_context.transfer_amount,
    )


@then(parsers.re(r"^the transfer is rejected with (?P<expected_outcome>[A-Za-z0-9 -]+)$"))
def _(
    expected_outcome: str,
    transfer_context: TransferContext,
    transfer_service: TransferService,
) -> None:
    transfer_service.assert_ticket_rejected(expected_outcome, transfer_context)
