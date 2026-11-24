"""Thin steps for customer login onboarding."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from tests.services.login_onboarding_actions import perform_login_panel_action
from tests.services.login_onboarding_asserts import assert_login_ui_state
from tests.ui.pages.app.login_page import LoginPage

scenarios("../features/app/login_onboarding.feature")


@given("the customer is on the app login page")
def _(login_page: LoginPage) -> None:
    login_page.open()


@when(
    parsers.re(
        r"^the customer (?P<action>opens|returns from) "
        r"(?P<panel>referral code|terms of use)$"
    )
)
def _login_panel_action(action: str, panel: str, login_page: LoginPage) -> None:
    perform_login_panel_action(login_page, action, panel)


@when("the customer enters a valid phone number")
def _(login_page: LoginPage) -> None:
    login_page.enter_valid_phone()


@when("the customer accepts terms and continues")
def _(login_page: LoginPage) -> None:
    login_page.submit_phone_and_accept_terms()


@when("the customer edits the phone number")
def _(login_page: LoginPage) -> None:
    login_page.edit_phone_number()


@then(
    parsers.re(
        r"^(?:the )?(?P<element>[A-Za-z0-9 ]+?) (?P<verb>is|are) "
        r"(?P<state>(?:not |still )?shown|(?:not )?clickable|empty|available)$"
    )
)
def _login_ui_element_state(element: str, verb: str, state: str, login_page: LoginPage) -> None:
    assert_login_ui_state(login_page, element, verb, state)
