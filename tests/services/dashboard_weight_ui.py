"""Shared dashboard provider-weight modal helpers (bill inquiry + topup/IPKG)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from tests.services.assert_report import AssertionReport
from tests.services.provider_weights import (
    assert_weights_equal,
    parse_weights,
    require_noted,
)


class WeightsModal(Protocol):
    """Minimal surface shared by bill and topup weight distribution modals."""

    def weight_values(self) -> list[int]:
        """Return current weight inputs left-to-right."""
        ...

    def set_weights(self, *weights: int) -> None:
        """Set every weight field in order."""
        ...

    def confirm_is_enabled(self) -> bool:
        """Whether Confirm is clickable (weights total 100)."""
        ...


def set_weights_from_raw(modal: WeightsModal, raw: str) -> None:
    """Set modal weights from a Gherkin list like ``50, 50``."""
    modal.set_weights(*parse_weights(raw))


def assert_weights_from_raw(modal: WeightsModal, raw: str, *, label: str) -> None:
    """Assert modal weights match a Gherkin list."""
    assert_weights_equal(label, modal.weight_values(), parse_weights(raw))


def assert_weights_match_noted(
    modal: WeightsModal,
    noted: Sequence[int] | None,
    *,
    label: str,
    what: str,
) -> None:
    """Assert modal weights match a previously noted snapshot."""
    expected = list(require_noted(noted, what=what))
    assert_weights_equal(label, modal.weight_values(), expected)


def assert_confirm_enabled(
    modal: WeightsModal,
    *,
    enabled: bool,
    label: str,
) -> None:
    """Assert Confirm is enabled or disabled."""
    check_label = "confirm enabled" if enabled else "confirm disabled"
    AssertionReport(label).check(check_label, modal.confirm_is_enabled() is enabled).assert_all()
