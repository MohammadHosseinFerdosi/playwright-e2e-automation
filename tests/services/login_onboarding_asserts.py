"""UI-state assertion dispatch for customer login onboarding.

One regex Then step (``LOGIN_UI_STATE_STEP`` in ``app_login_onboarding_steps.py``)
replaces the per-element assert helpers; the captured ``(element, state)`` pair
dispatches here to a ``LoginPage`` probe. One Gherkin Then/And line still equals
exactly one logged check.

Pattern conventions: ``.cursor/rules/step-patterns.mdc`` (shape 2 — UI validation).
Regex unit tests: ``tests/unit/test_step_regexes.py``.
"""

from __future__ import annotations

from collections.abc import Callable

from tests.services.assert_report import assert_truthy
from tests.ui.pages.app.login_page import LoginPage

LOGIN_UI_STATE_STEP = (
    r"^(?:the )?(?P<element>[A-Za-z0-9 ]+?) (?P<verb>is|are) "
    r"(?P<state>(?:not |still )?shown|(?:not )?clickable|empty|available)$"
)


def _accept_continue_not_clickable(page: LoginPage) -> bool:
    return not page.is_accept_continue_clickable()


def _confirm_continue_not_clickable(page: LoginPage) -> bool:
    return not page.is_confirm_continue_clickable()


def _referral_link_not_shown(page: LoginPage) -> bool:
    return not page.referral_link_is_shown()


_LOGIN_UI_STATE_PROBES: dict[tuple[str, str], Callable[[LoginPage], bool]] = {
    ("welcome copy", "shown"): LoginPage.welcome_is_shown,
    ("phone instruction", "shown"): LoginPage.phone_instruction_is_shown,
    ("mobile number hint", "shown"): LoginPage.mobile_number_hint_is_shown,
    ("phone number", "empty"): LoginPage.phone_input_is_empty,
    ("accept and continue", "shown"): LoginPage.accept_continue_is_shown,
    ("accept and continue", "clickable"): LoginPage.is_accept_continue_clickable,
    ("accept and continue", "not clickable"): _accept_continue_not_clickable,
    ("terms of use", "available"): LoginPage.is_terms_clickable,
    ("referral code link", "available"): LoginPage.is_referral_link_clickable,
    ("referral code link", "not shown"): _referral_link_not_shown,
    ("referral title", "shown"): LoginPage.referral_title_is_shown,
    ("referral instruction", "shown"): LoginPage.referral_instruction_is_shown,
    ("referral code preview", "shown"): LoginPage.referral_preview_is_shown,
    ("entered phone number", "still shown"): LoginPage.entered_phone_is_shown,
    ("activation code sent copy", "shown"): LoginPage.activation_sent_is_shown,
    ("activation code boxes", "shown"): LoginPage.activation_boxes_are_shown,
    ("confirm and continue", "not clickable"): _confirm_continue_not_clickable,
    ("resend timer", "shown"): LoginPage.is_resend_timer_shown,
    ("edit phone", "available"): LoginPage.is_edit_phone_visible,
}


def known_login_ui_checks() -> list[tuple[str, str]]:
    """Registered (element, state) pairs, for the regex unit test to keep in sync."""
    return sorted(_LOGIN_UI_STATE_PROBES)


def assert_login_ui_state(login_page: LoginPage, element: str, verb: str, state: str) -> None:
    """Assert one login-onboarding UI element is in the expected state.

    Args:
        login_page: The login page object.
        element: Captured element phrase (e.g. ``"accept and continue"``).
        verb: Captured ``is``/``are`` — used only to keep the logged check text
            identical to the Gherkin line.
        state: Captured state phrase (e.g. ``"not clickable"``).

    Raises:
        KeyError: If the (element, state) pair has no registered probe — a
            ``.feature`` typo fails loudly with the known checks listed.
    """
    probe = _LOGIN_UI_STATE_PROBES.get((element, state))
    if probe is None:
        raise KeyError(
            f"No login UI check for ({element!r}, {state!r}); "
            f"known checks: {known_login_ui_checks()}"
        )
    assert_truthy(f"{element} {verb} {state}", probe(login_page))
