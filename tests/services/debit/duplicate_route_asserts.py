"""Dispatch for the shared duplicate-route Then step (all debit gateways).

One regex step in ``tests/bdd/steps/conftest.py`` replaces the per-gateway
``duplicate <kind> routes keep a single transfer row`` definitions; the captured
route kind dispatches here to the same assert each original called.

Pattern conventions: ``.cursor/rules/step-patterns.mdc``. Regex unit tests:
``tests/unit/test_step_regexes.py``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.services.debit import bank_transfer_asserts as bt_assert
from tests.services.debit import bank_transfer_dsh_asserts as dsh_assert
from tests.services.debit import bank_transfer_ft_shahin_asserts as fsh_assert
from tests.services.debit import bank_transfer_manual_asserts as manual_assert
from tests.services.debit.bank_transfer import BankTransferContext

DUPLICATE_ROUTE_STEP = (
    r"^(?:the )?duplicate (?P<route_kind>[A-Za-z0-9 ]+?) routes? keeps? a single transfer row$"
)


def _manual_duplicate(ctx: BankTransferContext) -> None:
    manual_assert.assert_manual_case(ctx, "duplicate route single row")


def _dsh_duplicate(ctx: BankTransferContext) -> None:
    dsh_assert.assert_dsh_case(ctx, "duplicate same tracking")


_DUPLICATE_ROUTE_CHECKS: dict[str, Callable[[BankTransferContext], None]] = {
    "ft shahin": fsh_assert.assert_duplicate,
    "manual": _manual_duplicate,
    "Mellat": bt_assert.assert_duplicate_route_single_mongo_row,
    "Mellat dashboard": _dsh_duplicate,
    "IBAN Mellat": bt_assert.assert_duplicate_iban_second_handled,
}


def known_route_kinds() -> list[str]:
    """Registered route kinds, for the regex unit test to keep in sync."""
    return sorted(_DUPLICATE_ROUTE_CHECKS)


def assert_duplicate_route_single_row(ctx: BankTransferContext, route_kind: str) -> None:
    """Assert a duplicate route kept a single transfer row, per route kind.

    Args:
        ctx: Per-scenario bank-transfer context holding envelopes/tracking codes.
        route_kind: Captured phrase from the Gherkin sentence (e.g. ``"ft shahin"``,
            ``"Mellat dashboard"``).

    Raises:
        KeyError: If the route kind has no registered check — a ``.feature`` typo
            fails loudly with the known kinds listed.
    """
    check = _DUPLICATE_ROUTE_CHECKS.get(route_kind)
    if check is None:
        raise KeyError(
            f"No duplicate-route check for {route_kind!r}; known kinds: {known_route_kinds()}"
        )
    check(ctx)
