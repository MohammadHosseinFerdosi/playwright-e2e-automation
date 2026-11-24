"""Shared random identifiers for wallet/payment tracking codes."""

from __future__ import annotations

import secrets
import string

_DEFAULT_ALPHABET = string.ascii_letters + string.digits


def random_tracking_code(
    length: int = 16,
    alphabet: str = _DEFAULT_ALPHABET,
) -> str:
    """Cryptographically strong random code for payout / spend tracking fields."""
    if length < 1:
        raise ValueError(f"length must be >= 1, got {length}")
    return "".join(secrets.choice(alphabet) for _ in range(length))
