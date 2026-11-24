"""Gherkin regex and dispatch for Nemo live cash-out journeys."""

from __future__ import annotations

from tests.services.debit import nemo_e2e as e2e
from tests.services.debit.bank_transfer import BankTransferFlow
from tests.services.debit.bank_transfer_routing import BankTransferRoutingDb
from tests.services.debit.nemo_cash_out import NemoCashOutContext, NemoCashOutFlow

NEMO_E2E_REGISTER_STEP = (
    r"^the customer registers "
    r"(?P<mode>[A-Za-z0-9 -]*(?: onto | on the )[A-Za-z0-9 -]*)$"
)
NEMO_E2E_OUTCOME_STEP = r"^the registered cash-out (?P<outcome>[A-Za-z0-9 -]+)$"

_REGISTER_MODES: dict[str, str] = {
    "an IBAN cash-out onto the manual portal": "manual bt row",
    "a crisis-path cash-out on the manual portal": "manual crisis in progress",
    "an IBAN cash-out onto Mellat": "mellat bt row",
    "an IBAN cash-out onto Mellat and waits": "mellat poll terminal",
}
_OUTCOMES: dict[str, str] = {
    "manual bt row": "is a bank-transfer row on the manual portal",
    "manual crisis in progress": "stays in progress on the crisis path",
    "mellat bt row": "is a bank-transfer row on Mellat",
    "mellat poll terminal": "reaches a terminal Mellat state",
}


def known_nemo_e2e_register_modes() -> list[str]:
    """E2E register-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_REGISTER_MODES)


def known_nemo_e2e_outcomes() -> list[str]:
    """E2E Then phrases for the register family (DSH audits stay literal)."""
    return sorted(set(_OUTCOMES.values()))


def register_e2e_cash_out(
    nemo_flow: NemoCashOutFlow,
    bt_flow: BankTransferFlow,
    bt_routing: BankTransferRoutingDb,
    ctx: NemoCashOutContext,
    mode: str,
) -> None:
    """Run one Nemo e2e register When from the captured Gherkin mode.

    Args:
        nemo_flow: Per-scenario Nemo cash-out flow.
        bt_flow: Bank-transfer flow sharing routing.
        bt_routing: Routing Mongo session.
        ctx: Per-scenario Nemo context.
        mode: Captured mode phrase from ``NEMO_E2E_REGISTER_STEP``.

    Raises:
        KeyError: If the mode has no registered case.
    """
    case = _REGISTER_MODES.get(mode)
    if case is None:
        raise KeyError(
            f"No Nemo e2e register mode for {mode!r}; known: {known_nemo_e2e_register_modes()}"
        )
    e2e.store_e2e_case(nemo_flow, bt_flow, bt_routing, ctx, case)
    ctx.flags["e2e_case"] = case


def assert_e2e_register_outcome(ctx: NemoCashOutContext, outcome: str) -> None:
    """Run one e2e register Then; outcome must match the When's case.

    Args:
        ctx: Per-scenario Nemo context.
        outcome: Captured tail from ``NEMO_E2E_OUTCOME_STEP`` (after
            ``the registered cash-out ``).

    Raises:
        KeyError: If no e2e case was stored, or the outcome does not match it.
    """
    case = ctx.flags.get("e2e_case")
    if not isinstance(case, str):
        raise KeyError("No Nemo e2e case stored on the context")
    expected = _OUTCOMES.get(case)
    if expected is None:
        raise KeyError(f"No Nemo e2e outcome registered for {case!r}")
    if outcome != expected:
        raise KeyError(f"E2E case {case!r} expects outcome {expected!r}, got {outcome!r}")
    e2e.assert_e2e_case(ctx, case)
