"""Shared provider-weight helpers for dashboard admin configs.

Works for both weight-distribution shapes in the API layer —
``tests/api/top_ups/admin/operator_settings.ProviderDistribution`` and
``tests/api/bill_mng/admin/configs.InquiryDistribution`` — via the structural
``WeightedDistribution`` protocol (``provider`` + ``weight``).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar

from tests.services.assert_report import AssertionReport

T = TypeVar("T")


class WeightedDistribution(Protocol):
    """Any distribution item exposing a provider id and its weight."""

    provider: int
    weight: float


class EnabledDistribution(WeightedDistribution, Protocol):
    """Weighted distribution that also carries an ``enabled`` flag."""

    enabled: bool


def parse_weights(raw: str) -> list[int]:
    """Parse a Gherkin weight list like ``50, 50`` or ``50 and 50``."""
    parts = [p.strip() for p in raw.replace(" and ", ",").split(",") if p.strip()]
    return [int(p) for p in parts]


def require_noted(value: T | None, *, what: str) -> T:
    """Return a previously noted value, or raise when the When step was skipped.

    Args:
        value: Snapshot captured by an earlier step.
        what: Human label used in the error (e.g. ``inquiry weights``).
    """
    if value is None:
        raise RuntimeError(f"No noted {what}")
    return value


def weights_in_order(
    distributions: Sequence[WeightedDistribution],
    *,
    providers: Sequence[int],
) -> list[int]:
    """Return integer weights for ``providers`` in order.

    Raises:
        LookupError: When a requested provider is missing from ``distributions``.
    """
    by_provider = {d.provider: d.weight for d in distributions}
    out: list[int] = []
    for provider in providers:
        if provider not in by_provider:
            raise LookupError(f"Provider {provider} missing in {list(by_provider)}")
        out.append(int(by_provider[provider]))
    return out


def assert_weights_equal(
    label: str,
    actual: Sequence[int],
    expected: Sequence[int],
) -> None:
    """Assert two weight sequences match (Allure-attached)."""
    AssertionReport(label).equals(
        "weights", actual=list(actual), expected=list(expected)
    ).assert_all()


def assert_enabled_matches_weights(distributions: Sequence[EnabledDistribution]) -> None:
    """Assert ``enabled`` is false iff ``weight`` is 0, for every distribution."""
    report = AssertionReport("Provider enabled flags match weights")
    for dist in distributions:
        weight = float(dist.weight)
        report.equals(
            f"provider={dist.provider} (weight={weight}) enabled",
            actual=dist.enabled,
            expected=weight != 0.0,
        )
    report.assert_all()
