"""Wallet-transfer YAML loading (no UAT)."""

from tests.services.transfer_service import load_transfer_variables


def test_invalid_amount_is_a_string() -> None:
    """YAML ``-562`` must load as a string, not fail pydantic as an int."""
    loaded = load_transfer_variables()
    assert loaded.invalid_amount == "-562"
