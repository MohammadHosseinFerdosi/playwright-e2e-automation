"""User wallet transfer orchestration for BDD scenarios.

Owns YAML vars, invalid-condition dispatch, non-cashoutable amount math,
ticket/pay HTTP calls, and rejection outcome checks so step files stay thin.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient, ApiSide
from tests.api.nemo.user_wallet_transfer.get_wallets_transfer import (
    WalletsTransferInfoBody,
    get_wallets_transfer,
)
from tests.api.nemo.user_wallet_transfer.pay_wallet import (
    TransferPayWalletBody,
    post_wallets_transfer_pay_wallet,
)
from tests.api.nemo.user_wallet_transfer.post_wallet_transfer import (
    TransferTicketBody,
    post_wallets_transfer,
)
from tests.api.wallet_provider.wallets.balance import (
    WalletBalanceBody,
    get_wallets_users_balance,
)
from tests.config.constants import WALLET_DEFAULT_DEFINITION
from tests.config.settings import REPO_ROOT, Settings
from tests.services.assert_report import (
    AssertionReport,
    assert_equals,
    assert_isinstance,
    assert_status_ok,
)
from tests.services.wallet_initializer import (
    ChargedUser,
    WalletChargeConfig,
    WalletInitializer,
)

_TRANSFER_YAML = REPO_ROOT / "data" / "wallet" / "wallet-transfer-variables.yaml"

# Match wallet total-balance cell-prefix convention (fresh users, not fixed Robot cells).
USER_CELL_NUMBER_PREFIX = "0945"

# Fresh users need enough cashoutable balance for a mid-range transfer (Robot reused
# fixed cells with leftover funds; we size payout explicitly).
_SOURCE_TOTAL_AMOUNT = 15_000
_SOURCE_CASHOUTABLE_AMOUNT = 10_000
_DEST_SEED_AMOUNT = 100
_VALID_TRANSFER_AMOUNT = 5_000

_secure_rand = random.SystemRandom()


class TransferVariables(BaseModel):
    """Suite variables from ``wallet-transfer-variables.yaml``."""

    model_config = ConfigDict(extra="ignore")

    user_wallet_name: str = Field(alias="USER_WALLET_NAME")
    agent_value: str = Field(alias="AGENT_VALUE")
    user_ip_value: str = Field(alias="USER_IP_VALUE")
    type_value: str = Field(alias="TYPE_VALUE")
    invalid_dest_cellnum: str = Field(alias="INVALID_DEST_CELLNUM")
    invalid_source_user_id: str = Field(alias="INVALID_SOURCE_USER_ID")
    under_limit_amount: int = Field(alias="UNDER_LIMIT_AMOUNT")
    over_limit_amount: int = Field(alias="OVER_LIMIT_AMOUNT")
    invalid_amount: str = Field(alias="INVALID_AMOUNT")
    incorrect_cellnum_msg: str = Field(alias="INCORRECT_CELLNUM_MSG")
    out_limit_error_msg: str = Field(alias="OUT_LIMIT_ERROR_MSG")
    insufficient_amount_msg: str = Field(alias="INSUFFICIENT_AMOUNT_MSG")
    incorrect_input_data_msg: str = Field(alias="INCORRECT_INPUT_DATA_MSG")
    same_wallet_error_msg: str = Field(alias="SAME_WALLET_ERROR_MSG")


@lru_cache(maxsize=1)
def load_transfer_variables(path: Path | None = None) -> TransferVariables:
    """Load and validate wallet-transfer suite YAML once per process."""
    raw = yaml.safe_load((path or _TRANSFER_YAML).read_text(encoding="utf-8")) or {}
    # YAML parses `-562` as int; the ticket API still wants a string payload.
    if "INVALID_AMOUNT" in raw and raw["INVALID_AMOUNT"] is not None:
        raw["INVALID_AMOUNT"] = str(raw["INVALID_AMOUNT"]).strip()
    if "INVALID_DEST_CELLNUM" in raw:
        raw["INVALID_DEST_CELLNUM"] = str(raw["INVALID_DEST_CELLNUM"])
    if "INVALID_SOURCE_USER_ID" in raw:
        raw["INVALID_SOURCE_USER_ID"] = str(raw["INVALID_SOURCE_USER_ID"])
    return TransferVariables.model_validate(raw)


@dataclass
class TransferContext:
    """Per-scenario source/dest customers plus transfer attempt state."""

    source: ChargedUser
    dest: ChargedUser
    source_initial_balance: int
    dest_initial_balance: int
    transfer_amount: int = 0
    ticket_result: dict[str, Any] = field(default_factory=dict)
    pay_result: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TransferAttempt:
    """Resolved ticket parameters for one invalid-transfer Outline condition."""

    user_id: str
    amount: int | str
    dest_cell_number: str


def _amount_as_int(amount: int | str) -> int:
    text = str(amount)
    return int(amount) if text.lstrip("-").isdigit() else 0


def _ticket_error_payload(ticket_result: dict[str, Any]) -> tuple[int, Any]:
    status = int(ticket_result["status_code"])
    body = ticket_result.get("body")
    if isinstance(body, dict):
        return status, body.get("result")
    return status, None


class TransferService:
    """Create funded pair, run valid/invalid transfers, assert rejection outcomes."""

    def __init__(
        self,
        settings: Settings,
        wallet_initializer: WalletInitializer,
        microservice_client: ApiClient,
    ) -> None:
        self._settings = settings
        self._wallet_initializer = wallet_initializer
        self._ms = microservice_client
        self._vars = load_transfer_variables()
        self._outcome_messages: dict[str, str | None] = {
            "incorrect member cell": self._vars.incorrect_cellnum_msg,
            "out of limit": self._vars.out_limit_error_msg,
            "insufficient balance": self._vars.insufficient_amount_msg,
            "incorrect input data": self._vars.incorrect_input_data_msg,
            "same wallet": self._vars.same_wallet_error_msg,
            # status-only, matching Robot Ticket Error Should Be Returned
            "ticket rejection": None,
        }

    def create_funded_pair(self) -> TransferContext:
        """Provision source (funded) and destination (seeded) customers.

        Returns:
            Context with initial balances snapshot for later delta asserts.
        """
        source = self._wallet_initializer.create_user_with_charged_wallets(
            USER_CELL_NUMBER_PREFIX,
            [
                WalletChargeConfig(
                    definition=WALLET_DEFAULT_DEFINITION,
                    wallet_charge_amount=_SOURCE_TOTAL_AMOUNT,
                    cashoutable_charge_amount=_SOURCE_CASHOUTABLE_AMOUNT,
                ),
            ],
        )
        dest = self._wallet_initializer.create_user_with_charged_wallets(
            USER_CELL_NUMBER_PREFIX,
            [
                WalletChargeConfig(
                    definition=WALLET_DEFAULT_DEFINITION,
                    wallet_charge_amount=_DEST_SEED_AMOUNT,
                    cashoutable_charge_amount=_DEST_SEED_AMOUNT,
                ),
            ],
        )
        if not source.access_token:
            raise RuntimeError(
                "Source user missing access_token — UserFactory should return tokens "
                "from the create-time login"
            )
        return TransferContext(
            source=source,
            dest=dest,
            source_initial_balance=self.read_wallet_balance(source.user_id),
            dest_initial_balance=self.read_wallet_balance(dest.user_id),
        )

    def execute_valid_transfer(self, context: TransferContext) -> None:
        """Ticket + pay a mid-range cashoutable amount from source to dest (APP)."""
        context.transfer_amount = _VALID_TRANSFER_AMOUNT
        ticket_result = self.request_transfer_ticket(
            side=ApiSide.APP,
            user_id=context.source.user_id,
            amount=context.transfer_amount,
            dest_cell_number=context.dest.user_cell_number,
            access_token=CHANGE_ME
        )
        context.ticket_result = ticket_result
        assert_status_ok("Create transfer ticket", ticket_result)
        ticket_body = ticket_result["body"]
        assert_isinstance("Transfer ticket response body", ticket_body, TransferTicketBody)

        with ApiClient(
            self._settings,
            ApiSide.APP,
            auth_header=f"Bearer {context.source.access_token}",
        ) as client:
            pay_result = post_wallets_transfer_pay_wallet(
                client,
                ticket=ticket_body.ticket,
                user_ip=self._vars.user_ip_value,
                transfer_type=self._vars.type_value,
                agent=self._vars.agent_value,
            )
        context.pay_result = pay_result
        assert_status_ok("Pay transfer ticket", pay_result)
        assert_isinstance("Transfer pay response body", pay_result["body"], TransferPayWalletBody)

    def attempt_invalid_transfer(self, condition: str, context: TransferContext) -> None:
        """Build params for ``condition``, POST ticket on microservice side, store result.

        Args:
            condition: Outline key from
                ``the source customer attempts a transfer that is {condition}``.
            context: Funded source/dest pair; mutated with amount + ticket result.
        """
        attempt = self.build_invalid_attempt(condition.strip(), context)
        context.transfer_amount = _amount_as_int(attempt.amount)
        context.ticket_result = self.request_transfer_ticket(
            side=ApiSide.MICROSERVICE,
            user_id=attempt.user_id,
            amount=attempt.amount,
            dest_cell_number=attempt.dest_cell_number,
        )

    def build_invalid_attempt(self, condition: str, context: TransferContext) -> TransferAttempt:
        """Resolve Outline ``condition`` to ticket parameters via dispatch dict.

        Args:
            condition: Already-stripped condition key.
            context: Current source/dest customers.

        Returns:
            Parameters for ``request_transfer_ticket``.

        Raises:
            KeyError: Unknown condition key — lists registered Outline keys.
        """
        builder = _CONDITION_BUILDERS.get(condition)
        if builder is None:
            raise KeyError(
                f"No transfer condition for {condition!r}; "
                f"known conditions: {known_transfer_conditions()}"
            )
        return builder(self, context)

    def request_transfer_ticket(
        self,
        *,
        side: ApiSide,
        user_id: str,
        amount: int | str,
        dest_cell_number: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        """POST wallets transfer ticket on the given API side.

        Returns:
            ``{status_code, body}`` envelope from Nemo.
        """
        auth_header = f"Bearer {access_token}" if access_token else None
        with ApiClient(self._settings, side, auth_header=auth_header) as client:
            return post_wallets_transfer(
                client,
                user_id=user_id,
                agent=self._vars.agent_value,
                amount=amount,
                dest_cell_number=dest_cell_number,
            )

    def read_wallet_balance(self, user_id: str) -> int:
        """Return the default wallet balance for ``user_id`` (microservice client)."""
        result = get_wallets_users_balance(self._ms, user_id, self._vars.user_wallet_name)
        assert_status_ok("Get wallet balance", result)
        body = result["body"]
        assert_isinstance("Get wallet balance response body", body, WalletBalanceBody)
        return body.balance

    def source_balance_decrease(self, context: TransferContext) -> int:
        """How much the source default wallet dropped since the initial snapshot."""
        new_balance = self.read_wallet_balance(context.source.user_id)
        return context.source_initial_balance - new_balance

    def dest_balance_increase(self, context: TransferContext) -> int:
        """How much the destination default wallet rose since the initial snapshot."""
        new_balance = self.read_wallet_balance(context.dest.user_id)
        return new_balance - context.dest_initial_balance

    def assert_ticket_rejected(self, expected_outcome: str, context: TransferContext) -> None:
        """Assert ticket HTTP 422 and optional message for Outline outcome key.

        Args:
            expected_outcome: Outline key from
                ``the transfer is rejected with {expected_outcome}``.
            context: Must already hold ``ticket_result`` from an invalid attempt.

        Raises:
            KeyError: Unknown outcome key — lists registered Outline keys.
            AssertionError: Via ``AssertionReport`` / assert helpers on mismatch.
        """
        outcome = expected_outcome.strip()
        if outcome not in self._outcome_messages:
            raise KeyError(
                f"No transfer outcome for {outcome!r}; "
                f"known outcomes: {sorted(self._outcome_messages)}"
            )

        status, result = _ticket_error_payload(context.ticket_result)
        AssertionReport("Transfer ticket rejected").equals(
            "HTTP status", actual=status, expected=422
        ).attach_json("ticket response", context.ticket_result).assert_all()

        expected_message = self._outcome_messages[outcome]
        if expected_message is None:
            return

        assert_isinstance("Transfer rejection failure result", result, dict)
        assert_equals(
            "Transfer rejection message",
            result.get("message"),
            expected_message,
        )

    def _attempt_invalid_source(self, context: TransferContext) -> TransferAttempt:
        return TransferAttempt(
            user_id=self._vars.invalid_source_user_id,
            amount=_VALID_TRANSFER_AMOUNT,
            dest_cell_number=context.dest.user_cell_number,
        )

    def _attempt_invalid_destination(self, context: TransferContext) -> TransferAttempt:
        return TransferAttempt(
            user_id=context.source.user_id,
            amount=_VALID_TRANSFER_AMOUNT,
            dest_cell_number=self._vars.invalid_dest_cellnum,
        )

    def _attempt_under_minimum(self, context: TransferContext) -> TransferAttempt:
        return TransferAttempt(
            user_id=context.source.user_id,
            amount=self._vars.under_limit_amount,
            dest_cell_number=context.dest.user_cell_number,
        )

    def _attempt_over_maximum(self, context: TransferContext) -> TransferAttempt:
        return TransferAttempt(
            user_id=context.source.user_id,
            amount=self._vars.over_limit_amount,
            dest_cell_number=context.dest.user_cell_number,
        )

    def _attempt_invalid_amount(self, context: TransferContext) -> TransferAttempt:
        return TransferAttempt(
            user_id=context.source.user_id,
            amount=self._vars.invalid_amount,
            dest_cell_number=context.dest.user_cell_number,
        )

    def _attempt_same_wallet(self, context: TransferContext) -> TransferAttempt:
        return TransferAttempt(
            user_id=context.source.user_id,
            amount=_VALID_TRANSFER_AMOUNT,
            dest_cell_number=context.source.user_cell_number,
        )

    def _attempt_non_cashoutable(self, context: TransferContext) -> TransferAttempt:
        with ApiClient(self._settings, ApiSide.MICROSERVICE) as client:
            info = get_wallets_transfer(client, context.source.user_id, self._vars.agent_value)
        assert_status_ok("Get wallets transfer info", info)
        body = info["body"]
        assert_isinstance("Wallets transfer info response body", body, WalletsTransferInfoBody)
        non_cashoutable = body.wallet_balance - body.remaining_cap
        AssertionReport("Source wallet has non-cashoutable balance").check(
            "non_cashoutable > 0",
            non_cashoutable > 0,
            detail=(
                f"needed for this example; walletBalance={body.wallet_balance} "
                f"remainingCap={body.remaining_cap}"
            ),
        ).assert_all()
        added = _secure_rand.randint(1, non_cashoutable)
        return TransferAttempt(
            user_id=context.source.user_id,
            amount=body.remaining_cap + added,
            dest_cell_number=context.dest.user_cell_number,
        )


_CONDITION_BUILDERS: dict[str, Callable[[TransferService, TransferContext], TransferAttempt]] = {
    "an invalid source": TransferService._attempt_invalid_source,
    "an invalid destination": TransferService._attempt_invalid_destination,
    "under the minimum amount": TransferService._attempt_under_minimum,
    "over the maximum amount": TransferService._attempt_over_maximum,
    "an invalid amount": TransferService._attempt_invalid_amount,
    "the same wallet as destination": TransferService._attempt_same_wallet,
    "a non-cashoutable amount": TransferService._attempt_non_cashoutable,
}

TRANSFER_CONDITION_STEP = (
    r"^the source customer attempts a transfer that is "
    r"(?P<condition>[A-Za-z0-9 -]+)$"
)
TRANSFER_REJECTED_STEP = r"^the transfer is rejected with (?P<expected_outcome>[A-Za-z0-9 -]+)$"


def known_transfer_conditions() -> list[str]:
    """Registered Outline condition keys, for the regex unit test."""
    return sorted(_CONDITION_BUILDERS)
