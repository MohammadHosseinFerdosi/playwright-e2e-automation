"""Gherkin regex and dispatch for Melli / Mellat treasury direct-route.

Two When regexes (one per rail fixture) share this dispatch. Step files keep the
same ``r"..."`` inline on the decorator; these constants feed
``tests/unit/test_step_regexes.py``. Pattern conventions:
``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from tests.services.debit import bank_transfer_direct_asserts as dr_assert
from tests.services.debit.bank_transfer import BankTransferContext
from tests.services.debit.bank_transfer_direct import DirectRouteFlow

MELLI_DIRECT_WHEN_STEP = r"^treasury (?P<mode>[A-Za-z0-9 -]*Melli(?!t)[A-Za-z0-9 -]*)$"
MELLAT_DIRECT_WHEN_STEP = r"^treasury (?P<mode>[A-Za-z0-9 -]*Mellat[A-Za-z0-9 -]*)$"
MELLI_DIRECT_OUTCOME_STEP = r"^the Melli payout (?P<outcome>[A-Za-z0-9 -]+)$"
MELLAT_DIRECT_OUTCOME_STEP = r"^the Mellat payout (?P<outcome>[A-Za-z0-9 -]+)$"

_DIRECT_MODES: dict[str, str] = {
    "requests a Melli ACH direct payout": "happy path",
    "requests a zero-amount Melli ACH direct payout": "zero amount",
    "requests a Melli ACH direct payout from an invalid source": "invalid source iban",
    "requests a Melli ACH direct payout from a non-Melli source": "non home source",
    "requests a Melli ACH direct payout to the same bank": "same bank target",
    "reuses a Melli ACH tracking code": "duplicate tracking",
    "requests a Melli ACH direct payout with the client inactive": "inactive client",
    "requests a Melli payout with the wrong agenda": "wrong agenda",
    "requests a Melli ACH direct payout without a source account": "missing source",
    "waits for a Melli ACH direct payout to settle": "settle eventually",
    "requests a Mellat ACH direct payout": "happy path",
    "requests a zero-amount Mellat ACH direct payout": "zero amount",
    "requests a Mellat ACH direct payout from an invalid source": "invalid source iban",
    "requests a Mellat ACH direct payout without a source account": "missing source",
    "requests a Mellat ACH direct payout to the same bank": "same bank target",
    "requests a Mellat ACH direct payout from a non-Mellat source": "non home source",
    "reuses a Mellat ACH tracking code": "duplicate tracking",
    "requests a Mellat ACH direct payout with the wrong client ids": "wrong client ids",
    "waits for a Mellat ACH direct payout to settle": "settle eventually",
}
_MELLI_OUTCOMES: dict[str, str] = {
    "happy path": "settles on inquiry",
    "zero amount": "is rejected",
    "invalid source iban": "is rejected",
    "non home source": "does not attach from a non-Melli source",
    "same bank target": "stays off PAYA for a same-bank destination",
    "duplicate tracking": "keeps a single ledger row on duplicate",
    "inactive client": "is rejected",
    "wrong agenda": "is not the treasury path for a wrong agenda",
    "missing source": "is rejected",
    "settle eventually": "eventually settles",
}
_MELLAT_OUTCOMES: dict[str, str] = {
    "happy path": "settles on inquiry",
    "zero amount": "is rejected",
    "invalid source iban": "is rejected",
    "missing source": "is rejected",
    "same bank target": "stays off PAYA for a same-bank destination",
    "non home source": "does not attach from a non-Mellat source",
    "duplicate tracking": "keeps a single ledger row on duplicate",
    "wrong client ids": "is rejected",
    "settle eventually": "eventually settles",
}


def known_melli_direct_modes() -> list[str]:
    """Melli When phrases, for the regex unit test to keep in sync."""
    return sorted(mode for mode in _DIRECT_MODES if "Mellat" not in mode)


def known_mellat_direct_modes() -> list[str]:
    """Mellat When phrases, for the regex unit test to keep in sync."""
    return sorted(mode for mode in _DIRECT_MODES if "Mellat" in mode)


def known_melli_direct_outcomes() -> list[str]:
    """Melli Then phrases, for the regex unit test to keep in sync."""
    return sorted(set(_MELLI_OUTCOMES.values()))


def known_mellat_direct_outcomes() -> list[str]:
    """Mellat Then phrases, for the regex unit test to keep in sync."""
    return sorted(set(_MELLAT_OUTCOMES.values()))


def request_direct_payout(
    flow: DirectRouteFlow,
    ctx: BankTransferContext,
    mode: str,
) -> None:
    """Run one treasury direct-route When from the captured Gherkin mode.

    Args:
        flow: Per-scenario rail-bound direct-route flow (Melli or Mellat).
        ctx: Per-scenario bank-transfer context.
        mode: Captured mode phrase from ``MELLI_DIRECT_WHEN_STEP`` or
            ``MELLAT_DIRECT_WHEN_STEP``.

    Raises:
        KeyError: If the mode has no registered case.
    """
    case = _DIRECT_MODES.get(mode)
    if case is None:
        raise KeyError(f"No treasury direct-route mode for {mode!r}")
    ctx.flags["direct_case"] = case
    flow.store_case(ctx, case)


def assert_melli_direct_payout(
    flow: DirectRouteFlow, ctx: BankTransferContext, outcome: str
) -> None:
    """Run one Melli Then; Gherkin outcome must match the When's case.

    Args:
        flow: Melli treasury direct-route flow.
        ctx: Per-scenario bank-transfer context.
        outcome: Captured outcome phrase from ``MELLI_DIRECT_OUTCOME_STEP``.

    Raises:
        KeyError: If no case was stored, or the outcome does not match it.
    """
    _assert_direct_outcome(flow, ctx, outcome, _MELLI_OUTCOMES, "Melli")


def assert_mellat_direct_payout(
    flow: DirectRouteFlow, ctx: BankTransferContext, outcome: str
) -> None:
    """Run one Mellat Then; Gherkin outcome must match the When's case.

    Args:
        flow: Mellat treasury direct-route flow.
        ctx: Per-scenario bank-transfer context.
        outcome: Captured outcome phrase from ``MELLAT_DIRECT_OUTCOME_STEP``.

    Raises:
        KeyError: If no case was stored, or the outcome does not match it.
    """
    _assert_direct_outcome(flow, ctx, outcome, _MELLAT_OUTCOMES, "Mellat")


def _assert_direct_outcome(
    flow: DirectRouteFlow,
    ctx: BankTransferContext,
    outcome: str,
    outcomes: dict[str, str],
    rail: str,
) -> None:
    case = ctx.flags.get("direct_case")
    if not isinstance(case, str):
        raise KeyError(f"No {rail} direct-route case stored on the context")
    expected = outcomes.get(case)
    if expected is None:
        raise KeyError(f"No {rail} direct-route outcome registered for {case!r}")
    if outcome != expected:
        raise KeyError(f"{rail} case {case!r} expects outcome {expected!r}, got {outcome!r}")
    dr_assert.assert_direct_case(flow, ctx, case)
