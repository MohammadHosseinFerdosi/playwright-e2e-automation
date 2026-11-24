"""Shared dashboard admin helpers (username gate for bill + topup configs)."""

from __future__ import annotations

from tests.config.settings import Settings


def require_dashboard_username(settings: Settings) -> str:
    """Return ``DASHBOARD_USERNAME`` or raise when unset.

    Args:
        settings: Loaded stage settings.

    Returns:
        Non-empty dashboard admin user id.

    Raises:
        RuntimeError: When the dashboard username secret is missing.
    """
    user_id = settings.dashboard_username
    if not user_id:
        raise RuntimeError("DASHBOARD_USERNAME required for dashboard admin APIs")
    return user_id
