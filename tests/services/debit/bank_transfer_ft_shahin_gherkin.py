"""Gherkin regex and dispatch for ft shahin CASH_OUT and TREASURY.

Stems use ``ft shahin`` (space, no underscore). Distinct from Mellat / Melli.
Pattern conventions: ``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.services.debit import bank_transfer_asserts as bt_assert
from tests.services.debit import bank_transfer_direct_asserts as dr_assert
from tests.services.debit import bank_transfer_ft_shahin as fsh
from tests.services.debit import bank_transfer_ft_shahin_asserts as fsh_assert
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow
from tests.services.debit.bank_transfer_direct import DirectRouteFlow

FT_SHAHIN_REQUEST_STEP = (
    r"^the customer requests a ft shahin cash-out with (?P<mode>[A-Za-z0-9 -]+)$"
)
FT_SHAHIN_INQUIRE_STEP = r"^the customer inquires that ft shahin cash-out$"
FT_SHAHIN_ROUTE_STEP = (
    r"^the customer routes the same ft shahin cash-out twice with (?P<mode>[A-Za-z0-9 -]+)$"
)
FT_SHAHIN_DSH_WHEN_STEP = r"^DSH prepares a ft shahin cash-out with (?P<mode>[A-Za-z0-9 -]+)$"
FT_SHAHIN_OUTCOME_STEP = r"^the ft shahin cash-out (?P<outcome>[A-Za-z0-9 -]+)$"
FT_SHAHIN_TREASURY_GIVEN_STEP = r"^ft shahin treasury can pay out over (?P<rail>ACH|internal)$"
FT_SHAHIN_DIRECT_WHEN_STEP = r"^treasury requests a ft shahin payout with (?P<mode>[A-Za-z0-9 -]+)$"
FT_SHAHIN_DIRECT_OUTCOME_STEP = r"^the ft shahin payout (?P<outcome>[A-Za-z0-9 -]+)$"

_CustomerWhen = Callable[[BankTransferFlow, BankTransferContext], None]
_FtShahinThen = Callable[[BankTransferContext], None]

_CUSTOMER_REQUESTS: dict[str, _CustomerWhen] = {
    "same bank": lambda flow, ctx: fsh.store_internal(flow, ctx, "route"),
    "an invalid IBAN": lambda flow, ctx: fsh.store_internal(flow, ctx, "bad iban"),
    "hostile owner names": lambda flow, ctx: fsh.store_internal(flow, ctx, "hostile owners"),
    "a marker amount": lambda flow, ctx: fsh.store_internal(flow, ctx, "marker"),
    "a zero amount": lambda flow, ctx: fsh.store_internal(flow, ctx, "zero amount"),
    "PAYA": lambda flow, ctx: fsh.store_ach(flow, ctx, "route"),
    "a zero amount PAYA": lambda flow, ctx: fsh.store_ach(flow, ctx, "zero amount"),
    "PAYA to an invalid IBAN": lambda flow, ctx: fsh.store_ach(flow, ctx, "bad iban"),
    "batch PAYA": lambda flow, ctx: fsh.store_ach(flow, ctx, "batch"),
    "batch PAYA and inquires it": lambda flow, ctx: fsh.store_ach(flow, ctx, "batch inquiry"),
    "remainder batch PAYA": lambda flow, ctx: fsh.store_ach(flow, ctx, "remainder"),
    "triple chunk batch PAYA": lambda flow, ctx: fsh.store_ach(flow, ctx, "triple"),
    "a negative amount PAYA": lambda flow, ctx: fsh.store_ach(flow, ctx, "negative amount"),
    "PAYA without an IBAN": lambda flow, ctx: fsh.store_ach(flow, ctx, "missing iban"),
    "PAYA without a tracking code": lambda flow, ctx: fsh.store_ach(flow, ctx, "missing tracking"),
    "PAYA to a same-bank IBAN": lambda flow, ctx: fsh.store_ach(flow, ctx, "same bank"),
    "SATNA": fsh.store_rtgs,
}
_CUSTOMER_ROUTES: dict[str, _CustomerWhen] = {
    "internal": lambda flow, ctx: fsh.store_internal(flow, ctx, "duplicate"),
    "PAYA": lambda flow, ctx: fsh.store_ach(flow, ctx, "duplicate"),
}
_DSH_WHENS: dict[str, _CustomerWhen] = {
    "zero weights then PAYA": lambda flow, ctx: fsh.store_ach(flow, ctx, "zero then pin"),
    "provider statements": fsh.store_statement,
}
_OUTCOMES: dict[str, _FtShahinThen] = {
    "is routed internally": fsh_assert.assert_internal_route,
    "fee is zero": bt_assert.assert_internal_fee_zero,
    "is not routed as PAYA": fsh_assert.assert_never_paya,
    "stored amount is the marker amount": fsh_assert.assert_marker,
    "internal inquiry stays routed": fsh_assert.assert_internal_inquiry,
    "is routed as PAYA": fsh_assert.assert_ach_route,
    "PAYA inquiry stays routed": fsh_assert.assert_ach_inquiry,
    "PAYA fee matches the ledger": fsh_assert.assert_ach_fee,
    "batch PAYA route splits into the expected chunks": fsh_assert.assert_ach_batch,
    "batch PAYA inquiry lists the split transactions": fsh_assert.assert_ach_batch_inquiry,
    "remainder batch PAYA route splits correctly": fsh_assert.assert_ach_remainder,
    "triple batch PAYA route splits into three chunks": fsh_assert.assert_ach_batch,
    "is routed as SATNA": fsh_assert.assert_rtgs_route,
    "provider statement page is returned": fsh_assert.assert_statement_page,
    "reconciles across inquiry and the ledger": fsh_assert.assert_reconcile,
    "is rejected without storing a transfer": fsh_assert.assert_reject_invalid,
    "routes do not return a server error": fsh_assert.assert_xss,
    "is blocked then routes as PAYA": fsh_assert.assert_ach_zero_pin,
}
_DIRECT_MODES: dict[str, tuple[str, str]] = {
    "a zero amount ACH": ("ACH", "zero amount"),
    "a zero amount internal": ("internal", "zero amount"),
    "an invalid source ACH": ("ACH", "invalid source iban"),
    "an invalid source internal": ("internal", "invalid source iban"),
    "no source ACH": ("ACH", "missing source"),
    "no source internal": ("internal", "missing source"),
    "ACH to the same bank": ("ACH", "same bank target"),
    "duplicate ACH": ("ACH", "duplicate tracking"),
    "duplicate internal": ("internal", "duplicate tracking"),
}
_DIRECT_OUTCOMES: dict[str, str] = {
    "zero amount": "is rejected",
    "invalid source iban": "is rejected",
    "missing source": "is rejected",
    "same bank target": "stays off PAYA for a same-bank destination",
    "duplicate tracking": "keeps a single ledger row on duplicate",
}


def known_ft_shahin_request_modes() -> list[str]:
    """Return registered request When tails for the regex unit test."""
    return sorted(_CUSTOMER_REQUESTS)


def known_ft_shahin_route_modes() -> list[str]:
    """Return registered duplicate-route When tails for the regex unit test."""
    return sorted(_CUSTOMER_ROUTES)


def known_ft_shahin_dsh_modes() -> list[str]:
    """Return registered DSH When tails for the regex unit test."""
    return sorted(_DSH_WHENS)


def known_ft_shahin_outcomes() -> list[str]:
    """Return registered Then tails after ``the ft shahin cash-out ``."""
    return sorted(_OUTCOMES)


def known_ft_shahin_direct_modes() -> list[str]:
    """Return registered treasury When tails for the regex unit test."""
    return sorted(_DIRECT_MODES)


def known_ft_shahin_direct_outcomes() -> list[str]:
    """Return registered treasury Then tails after ``the ft shahin payout ``."""
    return sorted(set(_DIRECT_OUTCOMES.values()))


def _run_customer_when(
    table: dict[str, _CustomerWhen],
    mode: str,
    label: str,
    flow: BankTransferFlow,
    ctx: BankTransferContext,
) -> None:
    handler = table.get(mode)
    if handler is None:
        raise KeyError(f"No {label} for {mode!r}; known: {sorted(table)}")
    handler(flow, ctx)


def run_ft_shahin_request(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run one ft shahin CASH_OUT request When from the captured Gherkin mode.

    Args:
        flow: Per-scenario bank-transfer flow.
        ctx: Per-scenario bank-transfer context.
        mode: Captured phrase from ``FT_SHAHIN_REQUEST_STEP``.

    Raises:
        KeyError: If the mode has no registered handler.
    """
    _run_customer_when(_CUSTOMER_REQUESTS, mode, "ft shahin request mode", flow, ctx)


def run_ft_shahin_inquire(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Run the ft shahin inquiry When.

    Args:
        flow: Per-scenario bank-transfer flow.
        ctx: Per-scenario bank-transfer context.
    """
    fsh.store_inquiry(flow, ctx)


def run_ft_shahin_route(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run one ft shahin duplicate-route When from the captured Gherkin mode.

    Args:
        flow: Per-scenario bank-transfer flow.
        ctx: Per-scenario bank-transfer context.
        mode: Captured phrase from ``FT_SHAHIN_ROUTE_STEP``.

    Raises:
        KeyError: If the mode has no registered handler.
    """
    _run_customer_when(_CUSTOMER_ROUTES, mode, "ft shahin route mode", flow, ctx)


def run_ft_shahin_dsh(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run one ft shahin DSH When from the captured Gherkin mode.

    Args:
        flow: Per-scenario bank-transfer flow.
        ctx: Per-scenario bank-transfer context.
        mode: Captured phrase from ``FT_SHAHIN_DSH_WHEN_STEP``.

    Raises:
        KeyError: If the mode has no registered handler.
    """
    _run_customer_when(_DSH_WHENS, mode, "ft shahin DSH mode", flow, ctx)


def assert_ft_shahin_outcome(ctx: BankTransferContext, outcome: str) -> None:
    """Run one ft shahin CASH_OUT Then from the captured Gherkin outcome.

    Args:
        ctx: Per-scenario bank-transfer context.
        outcome: Captured tail from ``FT_SHAHIN_OUTCOME_STEP``.

    Raises:
        KeyError: If the outcome has no registered check.
    """
    check = _OUTCOMES.get(outcome)
    if check is None:
        raise KeyError(f"No ft shahin outcome for {outcome!r}; known: {known_ft_shahin_outcomes()}")
    check(ctx)


def request_ft_shahin_direct_payout(
    flow: DirectRouteFlow, ctx: BankTransferContext, mode: str
) -> None:
    """Run one ft shahin treasury When from the captured Gherkin mode.

    Args:
        flow: ft shahin TREASURY direct-route flow.
        ctx: Per-scenario bank-transfer context.
        mode: Captured phrase from ``FT_SHAHIN_DIRECT_WHEN_STEP``.

    Raises:
        KeyError: If the mode has no registered case.
    """
    pair = _DIRECT_MODES.get(mode)
    if pair is None:
        raise KeyError(
            f"No ft shahin direct mode for {mode!r}; known: {known_ft_shahin_direct_modes()}"
        )
    kind, case = pair
    ctx.flags["direct_case"] = case
    flow.store_ft_shahin_kind_case(ctx, kind, case)


def assert_ft_shahin_direct_payout(
    flow: DirectRouteFlow, ctx: BankTransferContext, outcome: str
) -> None:
    """Run one ft shahin treasury Then; Gherkin outcome must match the When's case.

    Args:
        flow: ft shahin TREASURY direct-route flow.
        ctx: Per-scenario bank-transfer context.
        outcome: Captured tail from ``FT_SHAHIN_DIRECT_OUTCOME_STEP``.

    Raises:
        KeyError: If no case was stored, or the outcome does not match it.
    """
    case = ctx.flags.get("direct_case")
    if not isinstance(case, str):
        raise KeyError("No ft shahin direct-route case stored on the context")
    expected = _DIRECT_OUTCOMES.get(case)
    if expected is None:
        raise KeyError(f"No ft shahin direct-route outcome registered for {case!r}")
    if outcome != expected:
        raise KeyError(f"ft shahin case {case!r} expects outcome {expected!r}, got {outcome!r}")
    dr_assert.assert_direct_case(flow, ctx, case)
