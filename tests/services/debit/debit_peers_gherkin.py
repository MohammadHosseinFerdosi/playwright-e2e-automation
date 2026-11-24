"""Gherkin regex and dispatch for Parsian / Mellat SATNA cash-out.

Inquiry and live-execute stems are shared; request stems stay rail-specific.
Pattern conventions: ``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.services.debit import bank_transfer_peers as peers
from tests.services.debit import bank_transfer_peers_asserts as peers_assert
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow

PARSIAN_REQUEST_STEP = r"^the customer requests (?P<mode>[A-Za-z0-9 -]*Parsian[A-Za-z0-9 -]*)$"
PEER_INQUIRE_STEP = r"^the customer inquires that (?P<peer>Parsian|SATNA) cash-out$"
PEER_LIVE_STEP = r"^the customer executes a live (?P<rail>Parsian PAYA|Mellat SATNA) cash-out$"
PEER_ROUTED_STEP = r"^the cash-out is routed (?P<route>[A-Za-z0-9 -]+)$"
PEER_REJECTED_STEP = r"^the cash-out is rejected (?P<reason>[A-Za-z0-9 -]+)$"

_PeerWhen = Callable[[BankTransferFlow, BankTransferContext], None]

_PARSIAN_REQUESTS: dict[str, str] = {
    "a Parsian PAYA cash-out": "ordinary paya route",
    "a zero-amount Parsian PAYA cash-out": "zero amount rejected",
    "a Parsian PAYA cash-out to an invalid IBAN": "bad iban rejected",
}
_LIVE_DISPATCH: dict[str, _PeerWhen] = {
    "Parsian PAYA": lambda flow, ctx: peers.store_parsian_case(flow, ctx, "live transfer journey"),
    "Mellat SATNA": lambda flow, ctx: peers.store_rtgs_case(flow, ctx, "satna live transfer"),
}
_PEER_ROUTED: dict[str, Callable[[BankTransferContext], None]] = {
    "through Parsian PAYA": peers_assert.assert_parsian_route,
    "through Mellat SATNA": peers_assert.assert_rtgs_route,
}
_PEER_REJECTED: dict[str, Callable[[BankTransferContext], None]] = {
    "without storing a transfer": peers_assert.assert_reject_invalid,
    "as a blocked destination": peers_assert.assert_blocked,
}


def known_parsian_request_modes() -> list[str]:
    """Parsian request phrases, for the regex unit test to keep in sync."""
    return sorted(_PARSIAN_REQUESTS)


def known_peer_inquire_peers() -> list[str]:
    """Inquiry peer names, for the regex unit test to keep in sync."""
    return ["Parsian", "SATNA"]


def known_peer_live_rails() -> list[str]:
    """Live-execute rail phrases, for the regex unit test to keep in sync."""
    return sorted(_LIVE_DISPATCH)


def known_peer_routed_tails() -> list[str]:
    """Peer routed-Then tails, for the regex unit test to keep in sync."""
    return sorted(_PEER_ROUTED)


def known_peer_rejected_tails() -> list[str]:
    """Peer rejected-Then tails, for the regex unit test to keep in sync."""
    return sorted(_PEER_REJECTED)


def run_parsian_request(flow: BankTransferFlow, ctx: BankTransferContext, mode: str) -> None:
    """Run a Parsian PAYA request When."""
    case = _PARSIAN_REQUESTS.get(mode)
    if case is None:
        raise KeyError(f"No Parsian request mode for {mode!r}")
    peers.store_parsian_case(flow, ctx, case)


def inquire_peer_cash_out(flow: BankTransferFlow, ctx: BankTransferContext, peer: str) -> None:
    """Run the shared peer-inquiry When.

    Args:
        flow: Per-scenario bank-transfer flow.
        ctx: Per-scenario bank-transfer context.
        peer: Captured peer name from ``PEER_INQUIRE_STEP``.

    Raises:
        KeyError: If the peer is not Parsian or SATNA.
    """
    if peer not in known_peer_inquire_peers():
        raise KeyError(f"No peer inquiry for {peer!r}")
    peers.store_peer_inquiry(flow, ctx)


def execute_live_peer_cash_out(flow: BankTransferFlow, ctx: BankTransferContext, rail: str) -> None:
    """Run a live cash-out When for Parsian PAYA or Mellat SATNA.

    Args:
        flow: Per-scenario bank-transfer flow.
        ctx: Per-scenario bank-transfer context.
        rail: Captured rail phrase from ``PEER_LIVE_STEP``.

    Raises:
        KeyError: If the rail has no registered handler.
    """
    handler = _LIVE_DISPATCH.get(rail)
    if handler is None:
        raise KeyError(f"No live peer rail for {rail!r}; known: {known_peer_live_rails()}")
    handler(flow, ctx)


def assert_peer_routed(ctx: BankTransferContext, route: str) -> None:
    """Run one peer routed Then from the captured Gherkin tail.

    Args:
        ctx: Per-scenario bank-transfer context.
        route: Captured tail from ``PEER_ROUTED_STEP`` (after ``is routed ``).

    Raises:
        KeyError: If the route has no registered check.
    """
    check = _PEER_ROUTED.get(route)
    if check is None:
        raise KeyError(f"No peer routed outcome for {route!r}; known: {known_peer_routed_tails()}")
    check(ctx)


def assert_peer_rejected(ctx: BankTransferContext, reason: str) -> None:
    """Run one peer rejected Then from the captured Gherkin tail.

    Args:
        ctx: Per-scenario bank-transfer context.
        reason: Captured tail from ``PEER_REJECTED_STEP`` (after ``is rejected ``).

    Raises:
        KeyError: If the reason has no registered check.
    """
    check = _PEER_REJECTED.get(reason)
    if check is None:
        raise KeyError(
            f"No peer rejected outcome for {reason!r}; known: {known_peer_rejected_tails()}"
        )
    check(ctx)
