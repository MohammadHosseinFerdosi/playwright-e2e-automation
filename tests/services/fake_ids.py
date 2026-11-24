"""Fake Iranian cell-number and national-code generators.

Reimplements ``src/library/faker_utils.py`` against ``random.SystemRandom`` —
that Robot module cannot be imported here (it depends on ``robot.api.deco``).
"""

from __future__ import annotations

import random

_secure_rand = random.SystemRandom()


def fake_national_code() -> str:
    """Generate a checksum-valid Iranian national code."""
    digits: list[int] = []
    total_sum = 0
    for weight in range(10, 1, -1):
        digit = _secure_rand.randint(0, 9)
        digits.append(digit)
        total_sum += digit * weight
    remainder = total_sum % 11
    digits.append(remainder if remainder < 2 else 11 - remainder)
    return "".join(str(d) for d in digits)


def fake_cell_number(predefined_prefix: str | None = None) -> str:
    """Generate an Iranian-format cell number, optionally under a fixed prefix."""
    if predefined_prefix is None:
        prefixes = ["0983", "0984", "0985", "0986", "0987", "0988"]
        rest_length = 7
    else:
        prefixes = [str(predefined_prefix)]
        rest_length = 11 - len(str(predefined_prefix))
    prefix = _secure_rand.choice(prefixes)
    rest = "".join(_secure_rand.choices("0123456789", k=rest_length))
    return f"{prefix}{rest}"
