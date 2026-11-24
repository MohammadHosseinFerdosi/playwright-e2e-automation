"""Gherkin regex and dispatch for native digital-signature steps.

Step files keep the same ``r"..."`` inline on the decorator; these constants
feed ``tests/unit/test_step_regexes.py``. Pattern conventions:
``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.services.kyc import digital_signature_asserts as ds_assert
from tests.services.kyc.digital_signature import (
    DigitalSignatureContext,
    DigitalSignatureFlow,
)

DIGITAL_SIGNATURE_LIVENESS_PREP_STEP = (
    r"^the customer has (?P<liveness_prep>[A-Za-z0-9 ]+) for digital signature$"
)
DIGITAL_SIGNATURE_SETUP_STEP = (
    r"^the customer has (?P<setup>(?:initiated a basic|a generated) digital signature)$"
)
DIGITAL_SIGNATURE_INITIATE_STEP = (
    r"^the customer initiates (?P<mode>[A-Za-z0-9 ]+digital signature(?: without a password)?)$"
)
DIGITAL_SIGNATURE_VALIDATE_STEP = (
    r"^the customer validates (?P<mode>[A-Za-z0-9 ]+digital signature password)$"
)
DIGITAL_SIGNATURE_RESPONSE_STEP = r"^the digital signature (?P<result>[A-Za-z0-9 -]+)$"
DIGITAL_SIGNATURE_DSP_STEP = r"^the provider signature record is (?P<record>[A-Za-z0-9 -]+)$"

_Setup = Callable[[DigitalSignatureFlow, DigitalSignatureContext], None]
_Action = Callable[[DigitalSignatureFlow, DigitalSignatureContext], None]
_Response = Callable[[DigitalSignatureContext], None]
_DspRecord = Callable[[DigitalSignatureFlow, DigitalSignatureContext], None]

_SETUPS: dict[str, _Setup] = {
    "initiated a basic digital signature": (lambda flow, ctx: flow.setup_initiated(ctx)),
    "a generated digital signature": lambda flow, ctx: flow.setup_generated(ctx),
}
_INITIATE_MODES: dict[str, _Action] = {
    "a basic digital signature": lambda flow, ctx: flow.store_initiate(ctx),
    "a basic digital signature without a password": (
        lambda flow, ctx: flow.store_initiate_without_password(ctx)
    ),
}
_VALIDATE_MODES: dict[str, _Action] = {
    "the digital signature password": (lambda flow, ctx: flow.store_validate_password(ctx)),
    "a wrong digital signature password": (
        lambda flow, ctx: flow.store_validate_wrong_password(ctx)
    ),
}
_RESPONSES: dict[str, _Response] = {
    "initiate succeeds with a provider tracking code": ds_assert.assert_initiate_success,
    "generate succeeds": ds_assert.assert_generate_success,
    "revoke succeeds": lambda ctx: ds_assert.assert_result_success("revoke", ctx),
    "validate password succeeds": (
        lambda ctx: ds_assert.assert_result_success("validate-password", ctx)
    ),
    "generate reports incomplete liveness": ds_assert.assert_generate_incomplete_liveness,
    "initiate reports a bad request": ds_assert.assert_initiate_bad_request,
    "validate password reports signature not found": ds_assert.assert_validate_not_found,
    "validate password reports a password mismatch": ds_assert.assert_validate_password_mismatch,
}
_DSP_RECORDS: dict[str, _DspRecord] = {
    "pending for that provider tracking code": ds_assert.assert_dsp_pending,
    "initiated for that signature tracking code": ds_assert.assert_dsp_initiated,
    "revoked for that signature tracking code": ds_assert.assert_dsp_revoked,
}


def known_digital_signature_setups() -> list[str]:
    """Registered setup phrases, for the regex unit test to keep in sync."""
    return sorted(_SETUPS)


def known_digital_signature_initiate_modes() -> list[str]:
    """Registered initiate-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_INITIATE_MODES)


def known_digital_signature_validate_modes() -> list[str]:
    """Registered validate-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_VALIDATE_MODES)


def known_digital_signature_responses() -> list[str]:
    """Registered response phrases, for the regex unit test to keep in sync."""
    return sorted(_RESPONSES)


def known_digital_signature_dsp_records() -> list[str]:
    """Registered DSP-record phrases, for the regex unit test to keep in sync."""
    return sorted(_DSP_RECORDS)


def prepare_digital_signature(
    flow: DigitalSignatureFlow,
    ctx: DigitalSignatureContext,
    setup: str,
) -> None:
    """Run one digital-signature Given from the captured setup phrase.

    Args:
        flow: Per-scenario digital-signature flow.
        ctx: Per-scenario tracking codes and last API result.
        setup: Captured setup phrase from ``DIGITAL_SIGNATURE_SETUP_STEP``.

    Raises:
        KeyError: If the setup has no registered handler — a ``.feature`` typo
            fails loudly with the known setups listed.
    """
    handler = _SETUPS.get(setup)
    if handler is None:
        raise KeyError(
            f"No digital-signature setup for {setup!r}; "
            f"known setups: {known_digital_signature_setups()}"
        )
    handler(flow, ctx)


def initiate_digital_signature(
    flow: DigitalSignatureFlow,
    ctx: DigitalSignatureContext,
    mode: str,
) -> None:
    """Run one initiate When from the captured Gherkin mode.

    Args:
        flow: Per-scenario digital-signature flow.
        ctx: Per-scenario tracking codes and last API result.
        mode: Captured initiate-mode phrase from ``DIGITAL_SIGNATURE_INITIATE_STEP``.

    Raises:
        KeyError: If the mode has no registered handler — a ``.feature`` typo
            fails loudly with the known modes listed.
    """
    handler = _INITIATE_MODES.get(mode)
    if handler is None:
        raise KeyError(
            f"No digital-signature initiate mode for {mode!r}; "
            f"known modes: {known_digital_signature_initiate_modes()}"
        )
    handler(flow, ctx)


def validate_digital_signature_password(
    flow: DigitalSignatureFlow,
    ctx: DigitalSignatureContext,
    mode: str,
) -> None:
    """Run one validate-password When from the captured Gherkin mode.

    Args:
        flow: Per-scenario digital-signature flow.
        ctx: Per-scenario tracking codes and last API result.
        mode: Captured validate-mode phrase from ``DIGITAL_SIGNATURE_VALIDATE_STEP``.

    Raises:
        KeyError: If the mode has no registered handler — a ``.feature`` typo
            fails loudly with the known modes listed.
    """
    handler = _VALIDATE_MODES.get(mode)
    if handler is None:
        raise KeyError(
            f"No digital-signature validate mode for {mode!r}; "
            f"known modes: {known_digital_signature_validate_modes()}"
        )
    handler(flow, ctx)


def assert_digital_signature_response(ctx: DigitalSignatureContext, result: str) -> None:
    """Run one HTTP-response Then from the captured Gherkin result.

    Args:
        ctx: Per-scenario tracking codes and last API result.
        result: Captured result phrase from ``DIGITAL_SIGNATURE_RESPONSE_STEP``.

    Raises:
        KeyError: If the result has no registered handler — a ``.feature`` typo
            fails loudly with the known results listed.
    """
    handler = _RESPONSES.get(result)
    if handler is None:
        raise KeyError(
            f"No digital-signature response for {result!r}; "
            f"known responses: {known_digital_signature_responses()}"
        )
    handler(ctx)


def assert_digital_signature_dsp(
    flow: DigitalSignatureFlow,
    ctx: DigitalSignatureContext,
    record: str,
) -> None:
    """Run one DSP-record Then from the captured Gherkin record phrase.

    Args:
        flow: Per-scenario digital-signature flow.
        ctx: Per-scenario tracking codes and last API result.
        record: Captured record phrase from ``DIGITAL_SIGNATURE_DSP_STEP``.

    Raises:
        KeyError: If the record has no registered handler — a ``.feature`` typo
            fails loudly with the known records listed.
    """
    handler = _DSP_RECORDS.get(record)
    if handler is None:
        raise KeyError(
            f"No digital-signature DSP record for {record!r}; "
            f"known records: {known_digital_signature_dsp_records()}"
        )
    handler(flow, ctx)
