"""Gherkin regex and inquire/outcome dispatch for postal-code inquiry.

Step files keep the same ``r"..."`` inline on the decorator; these constants
feed ``tests/unit/test_step_regexes.py``. Pattern conventions:
``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.services.kyc import postal_code_asserts as postal_assert
from tests.services.kyc.postal_code import PostalCodeContext, PostalCodeFlow

POSTAL_PROVIDER_PIN_STEP = r"^the address provider is (?P<provider>jibit|sitaad)$"
POSTAL_INQUIRE_STEP = r"^the customer inquires (?P<mode>[A-Za-z0-9 ]+postal code(?: twice)?)$"
POSTAL_INQUIRY_OUTCOME_STEP = r"^the postal-code inquiry (?P<outcome>[A-Za-z0-9 -]+)$"
POSTAL_INVALID_WEIGHTS_STEP = (
    r"^staff submit invalid address provider weights for (?P<rule>[A-Za-z0-9 ]+)$"
)
POSTAL_SETTINGS_REJECTED_STEP = (
    r"^the address provider settings are rejected as (?P<title>[A-Za-z0-9_]+)$"
)

_InquireMode = Callable[[PostalCodeFlow, PostalCodeContext], None]
_InquiryOutcome = Callable[[PostalCodeContext], None]

_INQUIRE_MODES: dict[str, _InquireMode] = {
    "a valid postal code": lambda flow, ctx: flow.inquire_valid(ctx),
    "an unknown postal code": lambda flow, ctx: flow.inquire_unknown(ctx),
    "an invalid postal code": lambda flow, ctx: flow.inquire_invalid(ctx),
    "a valid postal code twice": lambda flow, ctx: flow.inquire_valid_twice(ctx),
}
_INQUIRY_OUTCOMES: dict[str, _InquiryOutcome] = {
    "succeeds": postal_assert.assert_inquiry_succeeded,
    "is not found": postal_assert.assert_inquiry_not_found,
    "is rejected": postal_assert.assert_inquiry_rejected,
}


def known_postal_inquire_modes() -> list[str]:
    """Registered inquire-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_INQUIRE_MODES)


def known_postal_inquiry_outcomes() -> list[str]:
    """Registered inquiry-outcome phrases, for the regex unit test to keep in sync."""
    return sorted(_INQUIRY_OUTCOMES)


def inquire_postal_code(
    flow: PostalCodeFlow,
    ctx: PostalCodeContext,
    mode: str,
) -> None:
    """Run one postal-code When from the captured Gherkin mode.

    Args:
        flow: Per-scenario postal-code flow.
        ctx: Per-scenario inquiry envelopes.
        mode: Captured inquire-mode phrase from ``POSTAL_INQUIRE_STEP``.

    Raises:
        KeyError: If the mode has no registered handler — a ``.feature`` typo
            fails loudly with the known modes listed.
    """
    handler = _INQUIRE_MODES.get(mode)
    if handler is None:
        raise KeyError(
            f"No postal inquire mode for {mode!r}; known modes: {known_postal_inquire_modes()}"
        )
    handler(flow, ctx)


def assert_postal_inquiry_outcome(ctx: PostalCodeContext, outcome: str) -> None:
    """Run one postal-code inquiry Then from the captured Gherkin outcome.

    Args:
        ctx: Per-scenario inquiry envelopes.
        outcome: Captured outcome phrase from ``POSTAL_INQUIRY_OUTCOME_STEP``.

    Raises:
        KeyError: If the outcome has no registered handler — a ``.feature`` typo
            fails loudly with the known outcomes listed.
    """
    handler = _INQUIRY_OUTCOMES.get(outcome)
    if handler is None:
        raise KeyError(
            f"No postal inquiry outcome for {outcome!r}; "
            f"known outcomes: {known_postal_inquiry_outcomes()}"
        )
    handler(ctx)
