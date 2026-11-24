"""Gherkin regex and register-mode dispatch for Nemo IBAN cash-out.

Step files keep the same ``r"..."`` inline on the decorator; these constants
feed ``tests/unit/test_step_regexes.py``. Pattern conventions:
``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from tests.services.debit import nemo_cash_out_asserts as nemo_assert
from tests.services.debit.nemo_cash_out import (
    NemoCashOutContext,
    NemoCashOutFlow,
    store_register_case,
)

NEMO_REGISTER_STEP = (
    r"^the customer registers "
    r"(?P<mode>(?:(?! onto | on the )[A-Za-z0-9 -])+)$"
)
NEMO_REGISTER_OUTCOME_STEP = r"^the Nemo cash-out (?P<outcome>[A-Za-z0-9 -]+)$"

_REGISTER_MODES: dict[str, str] = {
    "an IBAN cash-out": "success and detail",
    "an IBAN cash-out at the minimum amount": "min amount boundary",
    "an IBAN cash-out at the maximum amount": "max amount boundary",
    "an IBAN cash-out and waits for a terminal state": "poll to terminal",
    "an IBAN cash-out for an unknown user": "unknown user rejected",
    "a cash-out to an invalid IBAN": "invalid iban rejected",
    "a cash-out to an IBAN with spaces": "iban with spaces rejected",
    "a cash-out without an IBAN": "missing iban rejected",
    "a cash-out without a birth date": "missing birth date rejected",
    "a cash-out with an invalid birth date": "invalid birth date rejected",
    "a cash-out below the minimum amount": "amount below min rejected",
    "a cash-out above the maximum amount": "amount above max rejected",
}
_REGISTER_OUTCOMES: dict[str, str] = {
    "success and detail": "register succeeds",
    "min amount boundary": "register succeeds",
    "max amount boundary": "register succeeds",
    "poll to terminal": "register reaches a terminal state",
    "unknown user rejected": "register is rejected",
    "invalid iban rejected": "register is rejected",
    "iban with spaces rejected": "register is rejected",
    "missing iban rejected": "register is rejected",
    "missing birth date rejected": "register is rejected",
    "invalid birth date rejected": "register is rejected",
    "amount below min rejected": "register is rejected",
    "amount above max rejected": "register is rejected",
    "detail unknown tracking": "detail is rejected",
}


def known_nemo_register_modes() -> list[str]:
    """Registered register-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_REGISTER_MODES)


def known_nemo_register_outcomes() -> list[str]:
    """Registered register-outcome phrases, for the regex unit test to keep in sync."""
    return sorted(set(_REGISTER_OUTCOMES.values()))


def register_iban_cash_out(
    flow: NemoCashOutFlow,
    ctx: NemoCashOutContext,
    mode: str,
) -> None:
    """Run one register When from the captured Gherkin mode.

    Args:
        flow: Per-scenario Nemo cash-out flow.
        ctx: Per-scenario envelopes and flags.
        mode: Captured mode phrase from ``NEMO_REGISTER_STEP``.

    Raises:
        KeyError: If the mode has no registered case.
    """
    case = _REGISTER_MODES.get(mode)
    if case is None:
        raise KeyError(
            f"No Nemo register mode for {mode!r}; known modes: {known_nemo_register_modes()}"
        )
    _store_register(flow, ctx, case)


def register_unknown_cash_out_detail(
    flow: NemoCashOutFlow,
    ctx: NemoCashOutContext,
) -> None:
    """Run the unknown-tracking-code detail When.

    Args:
        flow: Per-scenario Nemo cash-out flow.
        ctx: Per-scenario envelopes and flags.
    """
    _store_register(flow, ctx, "detail unknown tracking")


def assert_cash_out_register(ctx: NemoCashOutContext, outcome: str) -> None:
    """Run one register Then; Gherkin outcome must match the When's case.

    Args:
        ctx: Per-scenario envelopes and flags.
        outcome: Captured outcome phrase from ``NEMO_REGISTER_OUTCOME_STEP``.

    Raises:
        KeyError: If no register case was stored, or the outcome does not match it.
    """
    case = ctx.flags.get("register_case")
    if not isinstance(case, str):
        raise KeyError("No Nemo register case stored on the context")
    expected = _REGISTER_OUTCOMES.get(case)
    if expected is None:
        raise KeyError(f"No Nemo register outcome registered for {case!r}")
    if outcome != expected:
        raise KeyError(f"Register case {case!r} expects outcome {expected!r}, got {outcome!r}")
    nemo_assert.assert_register_case(ctx, case)


def _store_register(flow: NemoCashOutFlow, ctx: NemoCashOutContext, case: str) -> None:
    ctx.flags["register_case"] = case
    store_register_case(flow, ctx, case)
