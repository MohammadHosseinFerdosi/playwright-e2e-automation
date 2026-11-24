"""Unit tests for financial rounding (no UAT)."""

from tests.services.rounding import round_half_down, round_half_up


def test_round_half_up_examples_from_legacy_docs() -> None:
    assert round_half_up(13.825, 0) == 14.0
    assert round_half_up(13.825, 1) == 13.8
    assert round_half_up(13.825, 2) == 13.83


def test_round_half_down_examples_from_legacy_docs() -> None:
    assert round_half_down(13.825, 0) == 14.0
    assert round_half_down(13.825, 1) == 13.8
    assert round_half_down(13.825, 2) == 13.82
