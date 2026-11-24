"""Typed values and live-lookup sentinels for flat Gherkin strings.

Gherkin Examples-table cells are always strings; the API/DB layer is not. This module
is the single place that converts them:

- ``coerce_gherkin_value`` — ``"null"`` -> ``None``, ``"[]"`` -> ``[]``, digits ->
  ``int``, valid JSON -> parsed, anything else -> the original string.
- ``register_db_sentinel`` / ``resolve_expected_value`` — a registered sentinel cell
  (e.g. ``FeeFromDb``) computes its expected value via a live lookup instead of a
  literal comparison, so one step validates against Gherkin data *or* the DB without
  a parallel "... from db" step.

Usage and rationale: ``docs/framework/regex-and-bdd-guide.md`` §6.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

SentinelResolver = Callable[..., Any]

_DB_SENTINELS: dict[str, SentinelResolver] = {}


def register_db_sentinel(sentinel: str) -> Callable[[SentinelResolver], SentinelResolver]:
    """Register a resolver for a Gherkin sentinel value.

    Args:
        sentinel: Exact Examples-cell text that triggers the resolver
            (e.g. ``"FeeFromDb"``).

    Returns:
        Decorator that registers the function and returns it unchanged. The resolver
        receives the keyword context passed to ``resolve_expected_value``.

    Raises:
        ValueError: If the sentinel name is already registered — duplicate sentinels
            would make the winning resolver import-order dependent.
    """

    def _register(resolver: SentinelResolver) -> SentinelResolver:
        if sentinel in _DB_SENTINELS:
            raise ValueError(f"DB sentinel {sentinel!r} is already registered")
        _DB_SENTINELS[sentinel] = resolver
        return resolver

    return _register


def coerce_gherkin_value(raw: str) -> Any:
    """Convert a flat Gherkin Examples-table string into a typed Python value.

    Digit strings with a leading zero (``"0912..."`` — phone numbers) stay strings:
    coercing them to ``int`` would silently corrupt the value.

    Args:
        raw: The Examples-cell text exactly as captured by the step.

    Returns:
        ``None`` for ``"null"``, ``[]`` for ``"[]"``, ``int`` for plain digit strings,
        the parsed value for valid JSON (``"true"``, ``"1.5"``, ``'{"a": 1}'``), and
        the original string otherwise.
    """
    if raw == "null":
        return None
    if raw == "[]":
        return []
    if raw.isdigit():
        if len(raw) > 1 and raw.startswith("0"):
            return raw
        return int(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def resolve_expected_value(raw: str, **context: Any) -> Any:
    """Resolve an expected value: registered sentinel -> live lookup, else coercion.

    Args:
        raw: The Examples-cell text.
        **context: Keyword arguments forwarded to the sentinel resolver (tracking
            codes, user ids, ... — whatever the registered resolver needs).

    Returns:
        The resolver's result when ``raw`` is a registered sentinel, otherwise
        ``coerce_gherkin_value(raw)``.
    """
    resolver = _DB_SENTINELS.get(raw)
    if resolver is not None:
        return resolver(**context)
    return coerce_gherkin_value(raw)
