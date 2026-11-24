"""Financial rounding — port of ``src/library/rounding.py`` (no Robot dependency).

Round-half-up / round-half-down for money math in wallet/payment/settlement tests.
"""

from __future__ import annotations

import math

Number = int | float


def round_half_up(n: Number, decimals: int = 0) -> float:
    """Round to nearest with the given precision; ties round away from zero (up)."""
    multiplier = 10**decimals
    return math.floor(n * multiplier + 0.5) / multiplier


def round_half_down(n: Number, decimals: int = 0) -> float:
    """Round to nearest with the given precision; ties round toward lesser value."""
    multiplier = 10**decimals
    return math.ceil(n * multiplier - 0.5) / multiplier
