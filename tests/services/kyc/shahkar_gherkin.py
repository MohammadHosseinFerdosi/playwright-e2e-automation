"""Gherkin regex and identity/inquire/outcome dispatch for Shahkar inquiry.

Step files keep the same ``r"..."`` inline on the decorator; these constants
feed ``tests/unit/test_step_regexes.py``. Pattern conventions:
``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.services.kyc import shahkar_asserts as shahkar_assert
from tests.services.kyc.shahkar import ShahkarContext, ShahkarFlow

SHAHKAR_IDENTITY_STEP = (
    r"^the customer has (?P<identity>[A-Za-z0-9 ]*"
    r"(?:cell number(?: that does not belong to them)?|national identity))$"
)
SHAHKAR_INQUIRE_STEP = r"^the customer inquires (?P<mode>Shahkar(?: twice)?)$"
SHAHKAR_FAULT_STEP = r"^the customer submits a Shahkar inquiry with (?P<fault>[A-Za-z0-9 ]+)$"
SHAHKAR_INQUIRY_OUTCOME_STEP = r"^the Shahkar inquiry is (?P<outcome>verified|unverified|rejected)$"

_IdentityPrep = Callable[[ShahkarFlow, ShahkarContext], None]
_InquireMode = Callable[[ShahkarFlow, ShahkarContext], None]
_InquiryOutcome = Callable[[ShahkarContext], None]

_IDENTITIES: dict[str, _IdentityPrep] = {
    "a matching cell number": lambda flow, ctx: flow.use_matching_cell(ctx),
    "a cell number that does not belong to them": (lambda flow, ctx: flow.use_mismatch_cell(ctx)),
    "a national identity": lambda flow, ctx: flow.use_national_identity(ctx),
}
_INQUIRE_MODES: dict[str, _InquireMode] = {
    "Shahkar": lambda flow, ctx: flow.store_inquiry(ctx),
    "Shahkar twice": lambda flow, ctx: flow.store_inquiry_twice(ctx),
}
_INQUIRY_OUTCOMES: dict[str, _InquiryOutcome] = {
    "verified": shahkar_assert.assert_inquiry_verified,
    "unverified": shahkar_assert.assert_inquiry_unverified,
    "rejected": shahkar_assert.assert_inquiry_rejected,
}


def known_shahkar_identities() -> list[str]:
    """Registered identity phrases, for the regex unit test to keep in sync."""
    return sorted(_IDENTITIES)


def known_shahkar_inquire_modes() -> list[str]:
    """Registered inquire-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_INQUIRE_MODES)


def known_shahkar_inquiry_outcomes() -> list[str]:
    """Registered inquiry-outcome phrases, for the regex unit test to keep in sync."""
    return sorted(_INQUIRY_OUTCOMES)


def prepare_shahkar_identity(
    flow: ShahkarFlow,
    ctx: ShahkarContext,
    identity: str,
) -> None:
    """Run one Shahkar Given from the captured Gherkin identity.

    Args:
        flow: Per-scenario Shahkar flow.
        ctx: Per-scenario inquiry envelopes.
        identity: Captured identity phrase from ``SHAHKAR_IDENTITY_STEP``.

    Raises:
        KeyError: If the identity has no registered handler — a ``.feature`` typo
            fails loudly with the known identities listed.
    """
    handler = _IDENTITIES.get(identity)
    if handler is None:
        raise KeyError(
            f"No Shahkar identity for {identity!r}; known identities: {known_shahkar_identities()}"
        )
    handler(flow, ctx)


def inquire_shahkar(flow: ShahkarFlow, ctx: ShahkarContext, mode: str) -> None:
    """Run one Shahkar When from the captured Gherkin inquire mode.

    Args:
        flow: Per-scenario Shahkar flow.
        ctx: Per-scenario inquiry envelopes.
        mode: Captured inquire-mode phrase from ``SHAHKAR_INQUIRE_STEP``.

    Raises:
        KeyError: If the mode has no registered handler — a ``.feature`` typo
            fails loudly with the known modes listed.
    """
    handler = _INQUIRE_MODES.get(mode)
    if handler is None:
        raise KeyError(
            f"No Shahkar inquire mode for {mode!r}; known modes: {known_shahkar_inquire_modes()}"
        )
    handler(flow, ctx)


def assert_shahkar_inquiry_outcome(ctx: ShahkarContext, outcome: str) -> None:
    """Run one Shahkar inquiry Then from the captured Gherkin outcome.

    Args:
        ctx: Per-scenario inquiry envelopes.
        outcome: Captured outcome phrase from ``SHAHKAR_INQUIRY_OUTCOME_STEP``.

    Raises:
        KeyError: If the outcome has no registered handler — a ``.feature`` typo
            fails loudly with the known outcomes listed.
    """
    handler = _INQUIRY_OUTCOMES.get(outcome)
    if handler is None:
        raise KeyError(
            f"No Shahkar inquiry outcome for {outcome!r}; "
            f"known outcomes: {known_shahkar_inquiry_outcomes()}"
        )
    handler(ctx)
