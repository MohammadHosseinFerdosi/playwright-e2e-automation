"""Gherkin regex and dispatch for Mellat ACH PAYA.

Ordinary/batch Whens are reused across scenarios with different Thens, so
Then dispatch is by outcome phrase — not coupled to the When case.
Pattern conventions: ``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.services.debit import bank_transfer_ach_asserts as ach_assert
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow

ACH_BATCH_CHUNKS = 2
ACH_TRIPLE_CHUNKS = 3

MELLAT_ACH_WHEN_STEP = (
    r"^a customer (?P<mode>(?:routes|executes|inquires) "
    r"[A-Za-z0-9 -]*(?:PAYA|ACH)[A-Za-z0-9 -]*)$"
)
MELLAT_ACH_OUTCOME_STEP = r"^the PAYA cash-out (?P<outcome>[A-Za-z0-9 -]+)$"

_AchWhen = Callable[[BankTransferFlow, BankTransferContext], None]
_AchThen = Callable[[BankTransferContext], None]

_ACH_WHENS: dict[str, _AchWhen] = {
    "routes an ordinary cross-bank PAYA transfer": lambda flow, ctx: flow.store_ach_route(
        ctx, tag="ACHPAYA"
    ),
    "routes an ordinary PAYA transfer and inquires it": (
        lambda flow, ctx: flow.store_ach_route_then_inquiry(ctx)
    ),
    "executes an ordinary PAYA live transfer": lambda flow, ctx: flow.store_ach_live_settle(ctx),
    "routes a batch cross-bank PAYA transfer": lambda flow, ctx: flow.store_ach_split(
        ctx, chunks=ACH_BATCH_CHUNKS, tag="ACHBAT"
    ),
    "routes a batch PAYA transfer and inquires it": (
        lambda flow, ctx: flow.store_ach_split_then_inquiry(ctx, chunks=ACH_BATCH_CHUNKS)
    ),
    "executes a batch PAYA live transfer": lambda flow, ctx: flow.store_ach_split_live_settle(
        ctx, chunks=ACH_BATCH_CHUNKS
    ),
    "routes a remainder batch PAYA transfer": lambda flow, ctx: flow.store_ach_remainder(ctx),
    "routes the same ACH tracking code twice": lambda flow, ctx: flow.store_ach_duplicate_route(
        ctx
    ),
    "routes a zero-amount PAYA transfer": lambda flow, ctx: flow.store_ach_zero_amount(ctx),
    "routes a same-bank IBAN on PAYA": lambda flow, ctx: flow.store_ach_same_bank(ctx),
    "routes a triple-chunk batch PAYA transfer": lambda flow, ctx: flow.store_ach_split(
        ctx, chunks=ACH_TRIPLE_CHUNKS, tag="ACH3"
    ),
    "inquires a recently settled PAYA transfer": (
        lambda flow, ctx: flow.store_recent_done_ach_inquiry(ctx)
    ),
}
_ACH_THENS: dict[str, _AchThen] = {
    "is a single ACH chunk": ach_assert.assert_ach_single_chunk_route,
    "inquiry stays routed": ach_assert.assert_ach_inquiry_routed,
    "inquiry lists the split transactions": ach_assert.assert_ach_batch_inquiry_lists_splits,
    "live transfer has settled": ach_assert.assert_ach_live_settled,
    "splits into the expected chunks": ach_assert.assert_ach_batch_route,
    "fee is zero": ach_assert.assert_ach_fee_zero,
    "same-bank route is not ACH": ach_assert.assert_same_bank_not_ach,
    "settled inquiry succeeds": ach_assert.assert_done_ach_inquiry_succeeds,
}


def known_mellat_ach_modes() -> list[str]:
    """ACH When phrases, for the regex unit test to keep in sync."""
    return sorted(_ACH_WHENS)


def known_mellat_ach_outcomes() -> list[str]:
    """ACH Then phrases (excludes shared invalid-input and duplicate-route)."""
    return sorted(_ACH_THENS)


def run_mellat_ach(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run one Mellat ACH When from the captured Gherkin mode.

    Args:
        flow: Per-scenario bank-transfer flow.
        ctx: Per-scenario bank-transfer context.
        mode: Captured mode phrase from ``MELLAT_ACH_WHEN_STEP``.

    Raises:
        KeyError: If the mode has no registered handler.
    """
    handler = _ACH_WHENS.get(mode)
    if handler is None:
        raise KeyError(f"No Mellat ACH mode for {mode!r}; known: {known_mellat_ach_modes()}")
    handler(flow, ctx)


def assert_mellat_ach_outcome(ctx: BankTransferContext, outcome: str) -> None:
    """Run one Mellat ACH Then from the captured Gherkin outcome.

    Args:
        ctx: Per-scenario bank-transfer context.
        outcome: Captured tail from ``MELLAT_ACH_OUTCOME_STEP`` (after
            ``the PAYA cash-out ``).

    Raises:
        KeyError: If the outcome has no registered handler.
    """
    handler = _ACH_THENS.get(outcome)
    if handler is None:
        raise KeyError(
            f"No Mellat ACH outcome for {outcome!r}; known: {known_mellat_ach_outcomes()}"
        )
    handler(ctx)
