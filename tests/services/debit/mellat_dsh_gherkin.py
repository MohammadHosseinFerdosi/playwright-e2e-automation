"""Gherkin regex and DSH-case dispatch for Mellat dashboard cash-out.

Step files keep the same ``r"..."`` inline on the decorator; these constants
feed ``tests/unit/test_step_regexes.py``. Pattern conventions:
``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from tests.services.debit import bank_transfer_dsh as dsh
from tests.services.debit import bank_transfer_dsh_asserts as dsh_assert
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow

MELLAT_DSH_REQUEST_STEP = r"^the customer requests a Mellat cash-out (?P<mode>[A-Za-z0-9 -]+)$"
MELLAT_DSH_REQUESTS_STEP = r"^the customer requests Mellat cash-outs (?P<mode>[A-Za-z0-9 -]+)$"
MELLAT_DSH_TRACKING_STEP = (
    r"^the customer (?P<mode>(?:inquires|reuses|routes) "
    r"[A-Za-z0-9 -]*Mellat[A-Za-z0-9 -]*tracking[A-Za-z0-9 -]*)$"
)
MELLAT_DSH_ACT_STEP = (
    r"^the customer (?P<mode>(?:executes|completes) "
    r"[A-Za-z0-9 -]*Mellat cash-out[A-Za-z0-9 -]*)$"
)
MELLAT_DSH_STAFF_STEP = (
    r"^DSH (?P<mode>(?!splits |checks that |looks up |audits )"
    r"[A-Za-z0-9 -]*Mellat[A-Za-z0-9 -]*)$"
)
MELLAT_DSH_OUTCOME_STEP = r"^the Mellat cash-out (?P<outcome>[A-Za-z0-9 -]+)$"

_REQUEST_MODES: dict[str, str] = {
    "with a SQL-like description": "description sql injection",
    "with an oversized payload": "oversized payload",
    "with a decimal amount": "decimal amount",
    "with a negative amount": "negative amount",
    "to an IBAN with spaces": "iban with spaces",
    "without an IBAN": "missing iban",
    "with a string amount": "string amount",
    "at the minimum amount": "minimum amount",
    "above the client maximum": "max client amount",
}
_REQUESTS_MODES: dict[str, str] = {
    "to IBANs from other banks": "cross-bank iban matrix",
    "with hostile owner names": "owner xss payloads",
}
_TRACKING_MODES: dict[str, str] = {
    "inquires Mellat transfers with injection tracking codes": "injection tracking inquiry",
    "reuses a Mellat tracking code with a different amount": "duplicate different amount",
    "routes the same Mellat tracking code twice": "duplicate same tracking",
}
_ACT_MODES: dict[str, str] = {
    "executes a production-style Mellat cash-out": "prod route transfer settle",
    "executes the same Mellat cash-out twice": "duplicate execute",
    "executes a Mellat cash-out after routing": "transfer after route",
    "executes a live Mellat cash-out onto the provider statement": (
        "live transfer on provider statement"
    ),
    "completes a live Mellat cash-out journey": "live reconcile journey",
}
_STAFF_MODES: dict[str, str] = {
    "switches Mellat weights and the customer executes a live cash-out": (
        "weight switch live transfer"
    ),
    "requests Mellat statement APIs": "statements apis smoke",
    "reads Mellat creditor PAYA statement rows": "creditor statement rows",
    "requests Mellat account statements with invalid dates": "invalid account statement dates",
    "requests Mellat statements with invalid dates": "invalid statements dates",
    "checks configured Mellat done-transfer statement amounts": (
        "configured done statement amounts"
    ),
    "pages through Mellat statements": "statements pagination",
}
_OUTCOMES: dict[str, str] = {
    "cross-bank iban matrix": "is rejected for a cross-bank IBAN",
    "owner xss payloads": "probes do not return a server error",
    "description sql injection": "does not return a server error",
    "oversized payload": "does not return a server error",
    "injection tracking inquiry": "inquiries do not leak transfer data",
    "decimal amount": "is handled",
    "negative amount": "is rejected",
    "iban with spaces": "is handled",
    "duplicate different amount": "is rejected",
    "missing iban": "is rejected",
    "string amount": "is handled",
    "minimum amount": "is handled",
    "weight switch live transfer": "settles",
    "prod route transfer settle": "settles",
    "max client amount": "is enforced",
    "concurrent duplicate execute": "concurrent executes do not double pay",
    "duplicate execute": "is rejected",
    "transfer after route": "is in progress after transfer",
    "statements apis smoke": "statement APIs succeed",
    "creditor statement rows": "creditor PAYA statement rows have non-zero amounts",
    "invalid statements dates": "invalid statement dates are rejected",
    "invalid account statement dates": "invalid statement dates are rejected",
    "live transfer on provider statement": "appears on the provider statement",
    "configured done statement amounts": "configured done-transfer statement amounts hold",
    "statements pagination": "statement pagination is honoured",
    "live reconcile journey": "reconciles across inquiry and the ledger",
}


def known_mellat_dsh_request_modes() -> list[str]:
    """Singular request-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_REQUEST_MODES)


def known_mellat_dsh_requests_modes() -> list[str]:
    """Plural request-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_REQUESTS_MODES)


def known_mellat_dsh_tracking_modes() -> list[str]:
    """Tracking-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_TRACKING_MODES)


def known_mellat_dsh_act_modes() -> list[str]:
    """Customer act-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_ACT_MODES)


def known_mellat_dsh_staff_modes() -> list[str]:
    """DSH staff-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_STAFF_MODES)


def known_mellat_dsh_outcomes() -> list[str]:
    """Outcome phrases used by Gherkin (excludes duplicate-route Then)."""
    return sorted(set(_OUTCOMES.values()))


def run_mellat_dsh_request(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a singular Mellat cash-out request When."""
    _run_dsh(flow, ctx, mode, _REQUEST_MODES, "request")


def run_mellat_dsh_requests(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a plural Mellat cash-out request When."""
    _run_dsh(flow, ctx, mode, _REQUESTS_MODES, "requests")


def run_mellat_dsh_tracking(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a Mellat inquire/reuse/duplicate-route When."""
    _run_dsh(flow, ctx, mode, _TRACKING_MODES, "tracking")


def run_mellat_dsh_act(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a Mellat execute/complete When."""
    _run_dsh(flow, ctx, mode, _ACT_MODES, "act")


def run_mellat_dsh_staff(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a DSH Mellat When."""
    _run_dsh(flow, ctx, mode, _STAFF_MODES, "staff")


def run_mellat_dsh_concurrent(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Run the concurrent Mellat execute When."""
    _store_dsh(flow, ctx, "concurrent duplicate execute")


def assert_mellat_dsh_outcome(ctx: BankTransferContext, outcome: str) -> None:
    """Run one Mellat DSH Then; Gherkin outcome must match the When's case.

    Args:
        ctx: Per-scenario bank-transfer context.
        outcome: Captured tail from ``MELLAT_DSH_OUTCOME_STEP`` (after
            ``the Mellat cash-out ``).

    Raises:
        KeyError: If no DSH case was stored, or the outcome does not match it.
    """
    case = ctx.flags.get("dsh_case")
    if not isinstance(case, str):
        raise KeyError("No Mellat DSH case stored on the context")
    expected = _OUTCOMES.get(case)
    if expected is None:
        raise KeyError(f"No Mellat DSH outcome registered for {case!r}")
    if outcome != expected:
        raise KeyError(f"DSH case {case!r} expects outcome {expected!r}, got {outcome!r}")
    dsh_assert.assert_dsh_case(ctx, case)


def _run_dsh(
    flow: BankTransferFlow,
    ctx: BankTransferContext,
    mode: str,
    mapping: dict[str, str],
    label: str,
) -> None:
    case = mapping.get(mode)
    if case is None:
        raise KeyError(f"No Mellat DSH {label} mode for {mode!r}")
    _store_dsh(flow, ctx, case)


def _store_dsh(flow: BankTransferFlow, ctx: BankTransferContext, case: str) -> None:
    ctx.flags["dsh_case"] = case
    dsh.store_dsh_case(flow, ctx, case)
