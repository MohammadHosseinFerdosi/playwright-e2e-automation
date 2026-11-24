"""Random cell numbers for internet-bundle tests, backed by the live operator prefix list.

Mirrors the real purchase flow: call ``GET /top-ups/operators`` first, then build a cell
number under one of the returned prefixes, instead of hardcoding a single test number.
Each prefix also declares which SIM card types it supports (``prefixes[].types``) — the
returned ``cell_number_type`` is always read from that live data, never a hardcoded default.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from tests.api.client import ApiClient
from tests.api.super_app.internet.bundles import CellNumberType
from tests.api.super_app.internet.operators import TopUpOperator, get_top_up_operators
from tests.services.api_assert import ensure_ok
from tests.services.fake_ids import fake_cell_number

_secure_rand = random.SystemRandom()


@dataclass(frozen=True)
class RandomCellNumber:
    """A live-prefix-backed cell number, plus the SIM type its own prefix data supports."""

    operator_id: str
    cell_number: str
    cell_number_type: CellNumberType


def _fetch_operators(client: ApiClient) -> list[TopUpOperator]:
    result = ensure_ok(get_top_up_operators(client), context="Fetch top-up operators")
    return result["body"].operators


def random_cell_number_for_operator(
    client: ApiClient, operator_id: str, cell_number_type: CellNumberType | None = None
) -> RandomCellNumber:
    """Build a random number for ``operator_id``, deriving its SIM type from live prefix data.

    ``client`` must be ``ApiSide.GENERAL`` with a valid Bearer auth header — same
    requirement as ``get_top_up_operators``. When ``cell_number_type`` is given, only a
    prefix that actually declares support for it is eligible — raises ``RuntimeError`` if
    ``operator_id`` has none. When omitted, the type is chosen from whatever types the
    randomly picked prefix itself declares, never a hardcoded default.
    """
    operator = next((o for o in _fetch_operators(client) if o.operator_id == operator_id), None)
    if operator is None:
        raise RuntimeError(f"No such operator_id={operator_id!r}")
    candidates = [p for p in operator.prefixes if p.types]
    if cell_number_type is not None:
        candidates = [p for p in candidates if cell_number_type.value in p.types]
    if not candidates:
        raise RuntimeError(
            f"No prefix supports SIM type "
            f"{cell_number_type.name if cell_number_type else 'any'} for operator_id={operator_id!r}"
        )
    prefix = _secure_rand.choice(candidates)
    resolved_type = cell_number_type or CellNumberType(_secure_rand.choice(prefix.types))
    return RandomCellNumber(
        operator_id=operator_id,
        cell_number=fake_cell_number(predefined_prefix=str(prefix.value)),
        cell_number_type=resolved_type,
    )


def random_cell_number_any_operator(
    client: ApiClient, exclude_operator_ids: frozenset[str] = frozenset()
) -> RandomCellNumber:
    """Build a random number under any live prefix.

    Operator id and SIM type are both derived from that prefix's own data, never
    hardcoded to a specific operator. ``exclude_operator_ids`` drops specific operators
    from the pool — e.g. one verified live to behave differently for a freshly generated,
    non-provisioned number.
    """
    candidates = [
        (operator, prefix)
        for operator in _fetch_operators(client)
        if operator.operator_id not in exclude_operator_ids
        for prefix in operator.prefixes
        if prefix.types
    ]
    if not candidates:
        raise RuntimeError("No operator/prefix data available to build a random cell number")
    operator, prefix = _secure_rand.choice(candidates)
    return RandomCellNumber(
        operator_id=operator.operator_id,
        cell_number=fake_cell_number(predefined_prefix=str(prefix.value)),
        cell_number_type=CellNumberType(_secure_rand.choice(prefix.types)),
    )


def random_cell_number_for_type(
    client: ApiClient, cell_number_type: CellNumberType
) -> RandomCellNumber:
    """Build a random number for any live operator whose prefix data supports ``cell_number_type``.

    Used when the scenario cares about the SIM type, not which operator carries it — the
    operator is picked from live data too, instead of being hardcoded.
    """
    candidates = [
        (operator, prefix)
        for operator in _fetch_operators(client)
        for prefix in operator.prefixes
        if cell_number_type.value in prefix.types
    ]
    if not candidates:
        raise RuntimeError(f"No operator/prefix supports SIM type {cell_number_type.name}")
    operator, prefix = _secure_rand.choice(candidates)
    return RandomCellNumber(
        operator_id=operator.operator_id,
        cell_number=fake_cell_number(predefined_prefix=str(prefix.value)),
        cell_number_type=cell_number_type,
    )
