"""Gherkin regex and dispatch for manual portal cash-out.

``DSH splits cash-out weights evenly between Manual and Mellat`` stays a
literal here. Nemo app prediction uses a distinct sentence (``… splits Nemo
cash-out weights …``) because the two bodies bind different fixtures.
Pattern conventions: ``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from tests.services.debit import bank_transfer_manual as manual
from tests.services.debit import bank_transfer_manual_asserts as manual_assert
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow

MANUAL_REQUEST_STEP = r"^the customer requests (?P<mode>[A-Za-z0-9 -]*manual[A-Za-z0-9 -]*)$"
MANUAL_EXECUTE_STEP = r"^the customer executes (?P<mode>[A-Za-z0-9 -]*manual[A-Za-z0-9 -]*)$"
MANUAL_INQUIRE_STEP = r"^the customer inquires (?P<mode>[A-Za-z0-9 -]*manual[A-Za-z0-9 -]*)$"
MANUAL_ACT_STEP = (
    r"^the customer (?P<mode>(?:completes|routes) "
    r"[A-Za-z0-9 -]*manual[A-Za-z0-9 -]*)$"
)
MANUAL_STAFF_STEP = (
    r"^DSH (?P<mode>(?!splits |settles the manual cash-out and)"
    r"[A-Za-z0-9 -]*manual[A-Za-z0-9 -]*)$"
)
MANUAL_OUTCOME_STEP = r"^the manual cash-out (?P<outcome>[A-Za-z0-9 -]+)$"

_REQUEST_MODES: dict[str, str] = {
    "a manual portal cash-out": "ach route pinned",
    "a manual portal cash-out that must stay PAYA": "never internal type",
    "a manual portal cash-out for ledger fields": "mongo row fields",
    "a manual portal cash-out for the fee": "ach fee zero",
    "a manual portal cash-out for the route journal": "route journal",
    "manual cash-outs to IBANs from every bank": "accepts every bank iban",
    "a manual cash-out under that split": "mellat split fifty fifty",
    "a cross-bank cash-out toward the manual portal": "cross bank blocked mellat only",
}
_EXECUTE_MODES: dict[str, str] = {
    "a manual portal cash-out that stays in progress": "route transfer in progress",
    "a manual portal cash-out for the transfer journal": "transfer journal",
    "a manual portal cash-out for transaction status": "tx accepted after transfer",
    "the same manual cash-out twice": "duplicate transfer rejected",
}
_INQUIRE_MODES: dict[str, str] = {
    "an in-progress manual cash-out": "inquiry preserves in progress",
    "a manual cash-out after transfer": "inquiry matches mongo",
}
_ACT_MODES: dict[str, str] = {
    "completes a manual cash-out for reconcile": "reconcile without statement",
    "routes the same manual tracking code twice": "duplicate route single row",
}
_STAFF_MODES: dict[str, str] = {
    "runs the ACH scheduler against an in-progress manual cash-out": (
        "scheduler preserves in progress"
    ),
    "checks manual portal routing weights": "routing consistency",
    "checks the manual SATNA service": "rtgs inactive",
    "runs the manual production crisis checklist": "production crisis checklist",
    "settles a done manual cash-out and inquires it": manual.DSH_SETTLE_DONE,
    "inspects a done manual cash-out row": manual.DSH_DONE_SCHEMA,
    "checks Nemo settlement on a reference manual row": "nemo settlement reference",
}
_OUTCOMES: dict[str, str] = {
    "ach route pinned": "is routed through the portal",
    "never internal type": "is PAYA not internal",
    "mongo row fields": "has the expected fields",
    "route transfer in progress": "stays in progress",
    "inquiry preserves in progress": "stays in progress after inquiry",
    "scheduler preserves in progress": "stays in progress after the scheduler",
    "routing consistency": "has consistent routing weights",
    "mellat split fifty fifty": "still routes through the portal on a split",
    "cross bank blocked mellat only": "is rejected as blocked",
    "rtgs inactive": "SATNA service stays inactive",
    "ach fee zero": "fee is zero",
    "accepts every bank iban": "accepts IBANs from every bank",
    "route journal": "has a route journal",
    "transfer journal": "has a transfer journal",
    "inquiry matches mongo": "inquiry matches the ledger",
    "tx accepted after transfer": "is accepted after transfer",
    "reconcile without statement": "reconciles without a provider statement",
    "duplicate transfer rejected": "duplicate execute is rejected",
    "concurrent transfer race": "concurrent executes do not double settle",
    "production crisis checklist": "production crisis checklist holds",
    manual.DSH_SETTLE_DONE: "settle-done inquiry contract holds",
    manual.DSH_DONE_SCHEMA: "done-row schema holds",
    "nemo settlement reference": "Nemo settlement holds on the reference row",
}


def known_manual_request_modes() -> list[str]:
    """Request-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_REQUEST_MODES)


def known_manual_execute_modes() -> list[str]:
    """Execute-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_EXECUTE_MODES)


def known_manual_inquire_modes() -> list[str]:
    """Inquire-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_INQUIRE_MODES)


def known_manual_act_modes() -> list[str]:
    """Complete/duplicate-route phrases, for the regex unit test to keep in sync."""
    return sorted(_ACT_MODES)


def known_manual_staff_modes() -> list[str]:
    """DSH manual phrases, for the regex unit test to keep in sync."""
    return sorted(_STAFF_MODES)


def known_manual_outcomes() -> list[str]:
    """Manual Then tails after ``the manual cash-out `` (excludes duplicate-route)."""
    return sorted(set(_OUTCOMES.values()))


def run_manual_request(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a manual portal request When."""
    _run(flow, ctx, mode, _REQUEST_MODES, "request")


def run_manual_execute(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a manual portal execute When."""
    _run(flow, ctx, mode, _EXECUTE_MODES, "execute")


def run_manual_inquire(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a manual portal inquire When."""
    _run(flow, ctx, mode, _INQUIRE_MODES, "inquire")


def run_manual_act(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a manual complete or duplicate-route When."""
    _run(flow, ctx, mode, _ACT_MODES, "act")


def run_manual_staff(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a DSH manual When."""
    _run(flow, ctx, mode, _STAFF_MODES, "staff")


def run_manual_concurrent(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Run the concurrent manual execute When."""
    _store(flow, ctx, "concurrent transfer race")


def assert_manual_outcome(ctx: BankTransferContext, outcome: str) -> None:
    """Run one manual Then; Gherkin outcome must match the When's case.

    Args:
        ctx: Per-scenario bank-transfer context.
        outcome: Captured tail from ``MANUAL_OUTCOME_STEP`` (after
            ``the manual cash-out ``).

    Raises:
        KeyError: If no manual case was stored, or the outcome does not match it.
    """
    case = ctx.flags.get("manual_case")
    if not isinstance(case, str):
        raise KeyError("No manual cash-out case stored on the context")
    expected = _OUTCOMES.get(case)
    if expected is None:
        raise KeyError(f"No manual outcome registered for {case!r}")
    if outcome != expected:
        raise KeyError(f"Manual case {case!r} expects outcome {expected!r}, got {outcome!r}")
    manual_assert.assert_manual_case(ctx, case)


def _run(
    flow: BankTransferFlow,
    ctx: BankTransferContext,
    mode: str,
    mapping: dict[str, str],
    label: str,
) -> None:
    case = mapping.get(mode)
    if case is None:
        raise KeyError(f"No manual {label} mode for {mode!r}")
    _store(flow, ctx, case)


def _store(flow: BankTransferFlow, ctx: BankTransferContext, case: str) -> None:
    ctx.flags["manual_case"] = case
    manual.store_manual_case(flow, ctx, case)
