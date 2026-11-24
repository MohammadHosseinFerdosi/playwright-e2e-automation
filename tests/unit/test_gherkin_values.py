"""Unit tests for Gherkin value coercion and DB-sentinel resolution (no UAT)."""

from __future__ import annotations

from typing import Any

import pytest

from tests.services.gherkin_values import (
    coerce_gherkin_value,
    register_db_sentinel,
    resolve_expected_value,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("null", None),
        ("[]", []),
        ("42", 42),
        ("0", 0),
        ("true", True),
        ("false", False),
        ("1.5", 1.5),
        ('{"a": 1}', {"a": 1}),
        ('["x", "y"]', ["x", "y"]),
        ("plain text", "plain text"),
        ("INVALID_PARAMETER", "INVALID_PARAMETER"),
    ],
)
def test_coerce_gherkin_value(raw: str, expected: Any) -> None:
    assert coerce_gherkin_value(raw) == expected


def test_leading_zero_digits_stay_strings() -> None:
    """Phone-number-like cells must never be corrupted into ints."""
    assert coerce_gherkin_value("09121234567") == "09121234567"
    assert coerce_gherkin_value("007") == "007"


def test_resolve_expected_value_falls_back_to_coercion() -> None:
    assert resolve_expected_value("42") == 42
    assert resolve_expected_value("plain") == "plain"


def test_registered_sentinel_resolves_with_context() -> None:
    @register_db_sentinel("UnitTestFee")
    def _fee(*, tracking_code: str, **_: Any) -> int:
        return len(tracking_code)

    assert resolve_expected_value("UnitTestFee", tracking_code="QA-123") == 6


def test_duplicate_sentinel_registration_rejected() -> None:
    @register_db_sentinel("UnitTestDupSentinel")
    def _first(**_: Any) -> int:
        return 1

    with pytest.raises(ValueError, match="already registered"):

        @register_db_sentinel("UnitTestDupSentinel")
        def _second(**_: Any) -> int:
            return 2
