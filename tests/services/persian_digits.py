"""Persian / ASCII digit helpers for Platform app UI assertions."""

from __future__ import annotations

_ASCII_TO_PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_PERSIAN_TO_ASCII = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def to_persian_digits(value: str) -> str:
    """Translate ASCII digits in ``value`` to Persian digits."""
    return value.translate(_ASCII_TO_PERSIAN)


def to_ascii_digits(value: str) -> str:
    """Translate Persian digits in ``value`` to ASCII digits."""
    return value.translate(_PERSIAN_TO_ASCII)


def phone_display_variants(inquiry_id: str) -> tuple[str, str]:
    """Return (ascii, persian) forms of a landline inquiry id."""
    ascii_id = to_ascii_digits(inquiry_id.strip())
    return ascii_id, to_persian_digits(ascii_id)
