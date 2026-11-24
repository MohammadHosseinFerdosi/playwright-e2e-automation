"""Gherkin regex and predict-mode dispatch for Nemo cash-out fee prediction.

Step files keep the same ``r"..."`` inline on the decorator; these constants
feed ``tests/unit/test_step_regexes.py``. Pattern conventions:
``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from tests.services.debit import nemo_cash_out_asserts as nemo_assert
from tests.services.debit.nemo_cash_out import (
    NemoCashOutContext,
    NemoCashOutFlow,
    store_predict_case,
)

NEMO_PREDICT_FEE_STEP = r"^the customer predicts a cash-out fee (?P<mode>[A-Za-z0-9 -]+)$"
NEMO_PREDICT_OUTCOME_STEP = r"^the cash-out fee prediction (?P<outcome>[A-Za-z0-9 -]+)$"

_PREDICT_MODES: dict[str, str] = {
    "for the configured card": "configured card fee",
    "at the marker amount": "marker amount fee",
    "at the minimum amount": "min boundary fee",
    "at the maximum amount": "max boundary fee",
    "for an unknown user": "unknown user rejected",
    "without a destination card": "missing target pan rejected",
    "of zero": "zero amount rejected",
    "with a negative amount": "negative amount rejected",
    "with an empty card number": "empty pan value rejected",
    "with the card-number field omitted": "missing pan value field rejected",
    "with an invalid card type": "invalid pan type rejected",
    "with a huge amount": "huge amount not amount range",
}
_PREDICT_OUTCOMES: dict[str, str] = {
    "configured card fee": "succeeds",
    "marker amount fee": "succeeds",
    "min boundary fee": "succeeds",
    "max boundary fee": "succeeds",
    "unknown user rejected": "is rejected",
    "missing target pan rejected": "is rejected",
    "zero amount rejected": "is rejected",
    "negative amount rejected": "is rejected",
    "empty pan value rejected": "is rejected",
    "missing pan value field rejected": "is rejected",
    "invalid pan type rejected": "is rejected",
    "huge amount not amount range": "is not an amount-range error",
}


def known_nemo_predict_modes() -> list[str]:
    """Registered predict-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_PREDICT_MODES)


def known_nemo_predict_outcomes() -> list[str]:
    """Registered predict-outcome phrases, for the regex unit test to keep in sync."""
    return sorted(set(_PREDICT_OUTCOMES.values()))


def predict_cash_out_fee(
    flow: NemoCashOutFlow,
    ctx: NemoCashOutContext,
    mode: str,
) -> None:
    """Run one predict When from the captured Gherkin mode.

    Args:
        flow: Per-scenario Nemo cash-out flow.
        ctx: Per-scenario envelopes and flags.
        mode: Captured mode phrase from ``NEMO_PREDICT_FEE_STEP``.

    Raises:
        KeyError: If the mode has no registered case.
    """
    case = _PREDICT_MODES.get(mode)
    if case is None:
        raise KeyError(
            f"No Nemo predict mode for {mode!r}; known modes: {known_nemo_predict_modes()}"
        )
    ctx.flags["predict_case"] = case
    store_predict_case(flow, ctx, case)


def assert_cash_out_fee_prediction(ctx: NemoCashOutContext, outcome: str) -> None:
    """Run one predict Then; Gherkin outcome must match the When's case.

    Args:
        ctx: Per-scenario envelopes and flags.
        outcome: Captured outcome phrase from ``NEMO_PREDICT_OUTCOME_STEP``.

    Raises:
        KeyError: If no predict case was stored, or the outcome does not match it.
    """
    case = ctx.flags.get("predict_case")
    if not isinstance(case, str):
        raise KeyError("No Nemo predict case stored on the context")
    expected = _PREDICT_OUTCOMES.get(case)
    if expected is None:
        raise KeyError(f"No Nemo predict outcome registered for {case!r}")
    if outcome != expected:
        raise KeyError(f"Predict case {case!r} expects outcome {expected!r}, got {outcome!r}")
    nemo_assert.assert_predict_case(ctx, case)
