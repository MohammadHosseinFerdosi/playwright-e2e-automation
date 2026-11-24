"""Gherkin regex and inquire-mode dispatch for registration inquiry.

Step files keep the same ``r"..."`` inline on the decorator; these constants
feed ``tests/unit/test_step_regexes.py``. Pattern conventions:
``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.services.kyc.registration_inquiry import (
    RegistrationInquiryContext,
    RegistrationInquiryFlow,
)

REGISTRATION_PROVIDER_PIN_STEP = (
    r"^the registration provider is (?P<provider>hafezsaman|jibit) "
    r"for a (?P<kind>basic|full) inquiry$"
)
REGISTRATION_INQUIRE_MODE_STEP = (
    r"^the customer submits a (?P<kind>basic|full) inquiry "
    r"(?P<mode>(?!using )[A-Za-z0-9 ]+)$"
)
REGISTRATION_INQUIRE_FAULT_STEP = (
    r"^the customer submits a (?P<kind>basic|full) inquiry using "
    r"(?P<fault>[A-Za-z0-9 ]+)$"
)
REGISTRATION_INVALID_WEIGHTS_STEP = (
    r"^staff submit invalid registration weights for (?P<rule>[A-Za-z0-9 ]+)$"
)
REGISTRATION_INQUIRY_REJECTED_STEP = (
    r"^the registration inquiry is rejected as (?P<title>[A-Za-z0-9_]+)$"
)
REGISTRATION_SETTINGS_REJECTED_STEP = (
    r"^the registration provider settings are rejected as (?P<title>[A-Za-z0-9_]+)$"
)

_InquireMode = Callable[
    [RegistrationInquiryFlow, RegistrationInquiryContext, str],
    None,
]

_INQUIRE_MODES: dict[str, _InquireMode] = {
    "forcing a live lookup with strong validation": (
        lambda flow, ctx, kind: flow.inquire_live(ctx, kind, "true", "true")
    ),
    "with strong validation": (
        lambda flow, ctx, kind: flow.inquire_live(ctx, kind, "false", "true")
    ),
    "twice": lambda flow, ctx, kind: flow.inquire_live_twice(ctx, kind, "false", "false"),
    "for a deceased person": lambda flow, ctx, kind: flow.inquire_dead(ctx, kind),
    "for the alternate live person": (
        lambda flow, ctx, kind: flow.inquire_alternate(ctx, kind, "false", "true")
    ),
}


def known_registration_inquire_modes() -> list[str]:
    """Registered inquire-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_INQUIRE_MODES)


def submit_registration_inquiry(
    flow: RegistrationInquiryFlow,
    ctx: RegistrationInquiryContext,
    kind: str,
    mode: str,
) -> None:
    """Run one registration-inquiry When from the captured Gherkin mode.

    Args:
        flow: Per-scenario registration inquiry flow.
        ctx: Per-scenario inquiry envelopes.
        kind: Captured inquiry kind (``"basic"`` or ``"full"``).
        mode: Captured submit-mode phrase from ``REGISTRATION_INQUIRE_MODE_STEP``.

    Raises:
        KeyError: If the mode has no registered handler — a ``.feature`` typo
            fails loudly with the known modes listed.
    """
    handler = _INQUIRE_MODES.get(mode)
    if handler is None:
        raise KeyError(
            f"No registration inquire mode for {mode!r}; "
            f"known modes: {known_registration_inquire_modes()}"
        )
    handler(flow, ctx, kind)
