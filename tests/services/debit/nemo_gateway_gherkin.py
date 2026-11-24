"""Gherkin regex and dispatch for Nemo app cash-out route prediction.

The Nemo split-weights When is ``DSH splits Nemo cash-out weights evenly
between Manual and Mellat`` — distinct from the manual-portal sentence so
pytest-bdd and the Gherkin plugin do not see two definitions. Pattern
conventions: ``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from tests.services.debit import nemo_gateway as gw
from tests.services.debit import nemo_gateway_asserts as gw_assert

NEMO_GATEWAY_ASK_STEP = r"^the customer asks which cash-out route (?P<mode>[A-Za-z0-9 -]+)$"
NEMO_GATEWAY_APP_STEP = r"^the customer asks the app (?P<mode>[A-Za-z0-9 -]+)$"
NEMO_GATEWAY_PREDICTED_STEP = r"^the predicted cash-out route (?P<outcome>[A-Za-z0-9 -]+)$"
NEMO_GATEWAY_APP_OUTCOME_STEP = r"^the app cash-out (?P<outcome>[A-Za-z0-9 -]+)$"

_ASK_MODES: dict[str, str] = {
    "Mellat will use": "mellat pin prediction",
    "Shahin will use": "shahin pin prediction",
    "the manual portal will use": "manual pin prediction",
    "the split will use": "manual mellat split prediction",
}
_APP_MODES: dict[str, str] = {
    "which cash-out route will be used": "transfer route prediction",
    "for the cash-out fee": "transfer fee",
}
_PREDICTED_OUTCOMES: dict[str, str] = {
    "mellat pin prediction": "is Mellat internal",
    "shahin pin prediction": "is Shahin internal",
    "manual pin prediction": "is the manual portal",
    "manual mellat split prediction": "prefers the manual portal on a split",
}
_APP_OUTCOMES: dict[str, str] = {
    "transfer route prediction": "route prediction succeeds",
    "transfer fee": "fee succeeds",
}


def known_nemo_gateway_ask_modes() -> list[str]:
    """Ask-which-route phrases, for the regex unit test to keep in sync."""
    return sorted(_ASK_MODES)


def known_nemo_gateway_app_modes() -> list[str]:
    """Asks-the-app phrases, for the regex unit test to keep in sync."""
    return sorted(_APP_MODES)


def known_nemo_gateway_predicted_outcomes() -> list[str]:
    """Predicted-route Then phrases, for the regex unit test to keep in sync."""
    return sorted(set(_PREDICTED_OUTCOMES.values()))


def known_nemo_gateway_app_outcomes() -> list[str]:
    """App Then phrases, for the regex unit test to keep in sync."""
    return sorted(set(_APP_OUTCOMES.values()))


def ask_cash_out_route(flow: gw.NemoGatewayFlow, ctx: gw.NemoGatewayContext, mode: str) -> None:
    """Run a 'which cash-out route … will use' When."""
    _store(flow, ctx, mode, _ASK_MODES, "ask")


def ask_app_cash_out(flow: gw.NemoGatewayFlow, ctx: gw.NemoGatewayContext, mode: str) -> None:
    """Run an 'asks the app' When."""
    _store(flow, ctx, mode, _APP_MODES, "app")


def assert_predicted_cash_out_route(ctx: gw.NemoGatewayContext, outcome: str) -> None:
    """Run a predicted-route Then; outcome must match the When's case.

    Args:
        ctx: Per-scenario Nemo gateway context.
        outcome: Captured phrase from ``NEMO_GATEWAY_PREDICTED_STEP``.

    Raises:
        KeyError: If no gateway case was stored, or the outcome does not match it.
    """
    _assert_gateway(ctx, outcome, _PREDICTED_OUTCOMES, "predicted")


def assert_app_cash_out(ctx: gw.NemoGatewayContext, outcome: str) -> None:
    """Run an app cash-out Then; outcome must match the When's case.

    Args:
        ctx: Per-scenario Nemo gateway context.
        outcome: Captured phrase from ``NEMO_GATEWAY_APP_OUTCOME_STEP``.

    Raises:
        KeyError: If no gateway case was stored, or the outcome does not match it.
    """
    _assert_gateway(ctx, outcome, _APP_OUTCOMES, "app")


def _store(
    flow: gw.NemoGatewayFlow,
    ctx: gw.NemoGatewayContext,
    mode: str,
    mapping: dict[str, str],
    label: str,
) -> None:
    case = mapping.get(mode)
    if case is None:
        raise KeyError(f"No Nemo gateway {label} mode for {mode!r}")
    gw.store_gateway_case(flow, ctx, case)
    ctx.flags["gateway_case"] = case


def _assert_gateway(
    ctx: gw.NemoGatewayContext,
    outcome: str,
    outcomes: dict[str, str],
    label: str,
) -> None:
    case = ctx.flags.get("gateway_case")
    if not isinstance(case, str):
        raise KeyError(f"No Nemo gateway {label} case stored on the context")
    expected = outcomes.get(case)
    if expected is None:
        raise KeyError(f"No Nemo gateway {label} outcome for {case!r}")
    if outcome != expected:
        raise KeyError(f"Gateway case {case!r} expects {expected!r}, got {outcome!r}")
    gw_assert.assert_gateway_case(ctx, case)
