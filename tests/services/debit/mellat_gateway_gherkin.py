"""Gherkin regex and dispatch for Mellat INTERNAL gateway customer actions.

Invalid-input routes stay on ``MELLAT_INVALID_ROUTE_STEP``. DSH preflight /
scheduler stay literal. Pattern conventions: ``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.services.debit import bank_transfer_asserts as bt_assert
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow

MELLAT_GATEWAY_WHEN_STEP = (
    r"^a customer (?P<mode>(?:routes (?!a Mellat transfer with )|"
    r"executes |inquires |reuses )[A-Za-z0-9 -]*Mellat[A-Za-z0-9 -]*)$"
)
MELLAT_INTERNAL_ROUTE_STEP = r"^the Mellat internal route (?P<outcome>[A-Za-z0-9 -]+)$"

_GwWhen = Callable[[BankTransferFlow, BankTransferContext], None]

_GATEWAY_WHENS: dict[str, _GwWhen] = {
    "routes a safe-amount Mellat transfer": lambda flow, ctx: flow.store_safe_route_contract(ctx),
    "routes the same Mellat tracking code twice": (
        lambda flow, ctx: flow.store_duplicate_route_same_payload(ctx)
    ),
    "routes a marker-amount Mellat transfer only": lambda flow, ctx: flow.store_marker_route_only(
        ctx
    ),
    "executes a Mellat transfer without routing first": (
        lambda flow, ctx: flow.store_execute_without_route(ctx)
    ),
    "inquires an unknown Mellat tracking code": lambda flow, ctx: flow.store_inquiry_unknown(ctx),
    "routes several Mellat transfers": lambda flow, ctx: flow.store_never_ach_under_pin(ctx),
    "reuses a Mellat tracking code with a different IBAN": (
        lambda flow, ctx: flow.store_duplicate_tracking_different_iban(ctx)
    ),
    "routes a same-bank Mellat transfer": lambda flow, ctx: flow.store_same_bank_internal_route(
        ctx
    ),
}


def known_mellat_gateway_modes() -> list[str]:
    """Mellat gateway When phrases, for the regex unit test to keep in sync."""
    return sorted(_GATEWAY_WHENS)


def run_mellat_gateway(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run one Mellat internal-gateway When from the captured Gherkin mode.

    Args:
        flow: Per-scenario bank-transfer flow.
        ctx: Per-scenario bank-transfer context.
        mode: Captured mode phrase from ``MELLAT_GATEWAY_WHEN_STEP``.

    Raises:
        KeyError: If the mode has no registered handler.
    """
    handler = _GATEWAY_WHENS.get(mode)
    if handler is None:
        raise KeyError(
            f"No Mellat gateway mode for {mode!r}; known: {known_mellat_gateway_modes()}"
        )
    handler(flow, ctx)


_GwThen = Callable[[BankTransferContext], None]

_INTERNAL_ROUTE_THENS: dict[str, _GwThen] = {
    "matches mongo": bt_assert.assert_route_on_pinned_gateway,
    "fee is zero": bt_assert.assert_internal_fee_zero,
}


def known_mellat_internal_route_outcomes() -> list[str]:
    """Mellat internal-route Then tails, for the regex unit test to keep in sync."""
    return sorted(_INTERNAL_ROUTE_THENS)


def assert_mellat_internal_route(ctx: BankTransferContext, outcome: str) -> None:
    """Run one Mellat internal-route Then from the captured Gherkin tail.

    Args:
        ctx: Per-scenario bank-transfer context.
        outcome: Captured tail from ``MELLAT_INTERNAL_ROUTE_STEP``.

    Raises:
        KeyError: If the outcome has no registered check.
    """
    check = _INTERNAL_ROUTE_THENS.get(outcome)
    if check is None:
        raise KeyError(
            f"No Mellat internal route outcome for {outcome!r}; "
            f"known: {known_mellat_internal_route_outcomes()}"
        )
    check(ctx)
