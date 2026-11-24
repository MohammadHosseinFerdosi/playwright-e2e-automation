"""UI-action dispatch for customer login onboarding.

One regex When step (``LOGIN_PANEL_ACTION_STEP`` in ``app_login_onboarding_steps.py``)
replaces the per-panel open/return steps; the captured ``(action, panel)`` pair
dispatches here to a ``LoginPage`` method.

Pattern conventions: ``.cursor/rules/step-patterns.mdc`` (shape 1 — UI action).
Regex unit tests: ``tests/unit/test_step_regexes.py``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.ui.pages.app.login_page import LoginPage

LOGIN_PANEL_ACTION_STEP = (
    r"^the customer (?P<action>opens|returns from) (?P<panel>referral code|terms of use)$"
)

_LOGIN_PANEL_ACTIONS: dict[tuple[str, str], Callable[[LoginPage], None]] = {
    ("opens", "referral code"): LoginPage.open_referral,
    ("opens", "terms of use"): LoginPage.open_terms,
    ("returns from", "referral code"): LoginPage.return_from_referral,
    ("returns from", "terms of use"): LoginPage.return_from_terms,
}


def known_login_panel_actions() -> list[tuple[str, str]]:
    """Registered (action, panel) pairs, for the regex unit test to keep in sync."""
    return sorted(_LOGIN_PANEL_ACTIONS)


def perform_login_panel_action(login_page: LoginPage, action: str, panel: str) -> None:
    """Perform one login-onboarding panel action.

    Args:
        login_page: The login page object.
        action: Captured action phrase (``"opens"`` or ``"returns from"``).
        panel: Captured panel phrase (``"referral code"`` or ``"terms of use"``).

    Raises:
        KeyError: If the (action, panel) pair has no registered handler — a
            ``.feature`` typo fails loudly with the known actions listed.
    """
    handler = _LOGIN_PANEL_ACTIONS.get((action, panel))
    if handler is None:
        raise KeyError(
            f"No login panel action for ({action!r}, {panel!r}); "
            f"known actions: {known_login_panel_actions()}"
        )
    handler(login_page)
