"""Login / OTP / PIN — port of login.resource + APP Login To App Handler + pin-service."""

from __future__ import annotations

import json
import re

from playwright.sync_api import Locator, Page

from tests.services.db.mysql_client import MySQLClient
from tests.services.db.redis_client import RedisClient
from tests.services.fake_ids import fake_cell_number
from tests.ui.auth import dismiss_login_popup_if_present, skip_walkthrough_ui
from tests.ui.labels.app import AppLabels as L
from tests.ui.pages.base_page import BasePage, LocatorLike

_TIMER_RE = re.compile(r"[0-9۰-۹]{1,2}:[0-9۰-۹]{2}")


class LoginPage(BasePage):
    """Full UI login (auth e2e). Prefer ``AppUiAuth.login_via_api_inject`` for domain tests."""

    PATH = "/auth/login"

    LOCATORS = {
        "phone_input": 'css=ui-form-field[formcontrolname="phoneNumber"] input',
        "phone_input_fallback": "css=input[type='tel']",
        "accept_continue": (
            f'css=.ngx-button-full-width >> button:has-text("{L.ACCEPT_TERMS_CONTINUE}")'
        ),
        "confirm_continue": f'button:has-text("{L.CONFIRM_AND_CONTINUE}")',
        "otp_first_digit": 'css=input.digit[id^="otp-"] >> nth=0',
        "pin_password": "css=#password",
        "welcome": f"xpath=//*[normalize-space()='{L.LOGIN_WELCOME}']",
        "phone_instruction": (f"xpath=//*[normalize-space()='{L.LOGIN_PHONE_INSTRUCTION}']"),
        "phone_field_label": f"xpath=//*[normalize-space()='{L.MOBILE_NUMBER}']",
        "terms_link": f"xpath=//*[normalize-space()='{L.TERMS_OF_USE}']",
        "referral_link": f"xpath=//*[normalize-space()='{L.HAVE_REFERRAL_CODE}']",
        "referral_title": f"xpath=//*[normalize-space()='{L.REFERRAL_CODE}']",
        "referral_instruction": (f"xpath=//*[normalize-space()='{L.ENTER_REFERRAL_CODE}']"),
        "code_preview": f"xpath=//*[normalize-space()='{L.CODE_PREVIEW}']",
        "referral_back": f"xpath=//button[normalize-space()='{L.BACK}']",
        "terms_title": f"xpath=//*[normalize-space()='{L.TERMS_DOCUMENT_TITLE}']",
        "terms_back": (
            "css=ion-back-button, button.back-button, "
            "i[class*='arrow'], i[class*='back'], i[class*='chevron'], "
            "button:has(i[class*='arrow']), button:has(i[class*='back']), "
            "[class*='back-button'], [class*='header-back']"
        ),
        "activation_sent": (f"xpath=//*[normalize-space()='{L.ACTIVATION_CODE_SENT}']"),
        "edit_phone": (
            "css=i[class*='edit'], button:has(i[class*='edit']), "
            "[class*='edit-phone'], [class*='phone-edit'] button"
        ),
    }

    def __init__(
        self,
        page: Page,
        base_url: str,
        login_url: str,
        default_timeout_ms: int = 20_000,
    ) -> None:
        """Bind Playwright page and absolute login URL from settings."""
        super().__init__(page, base_url, default_timeout_ms=default_timeout_ms)
        self._login_url = login_url
        self._entered_phone = ""

    def open(self) -> None:
        """Navigate to the login URL and wait for the auth route."""
        self.page.goto(self._login_url, wait_until="domcontentloaded")
        self.should_be_on_login()

    def should_be_on_login(self) -> None:
        """Wait until the browser URL contains ``/auth/login``."""
        self.wait_until_url_contains("/auth/login")

    def _phone_locator(self) -> Locator:
        """Return the visible phone input (primary, then tel fallback)."""
        phone = self.LOCATORS["phone_input"]
        if not self.is_visible(phone, timeout_ms=3_000):
            phone = self.LOCATORS["phone_input_fallback"]
        return self.resolve(phone).first

    def enter_cell_number(self, cell_number: str) -> None:
        """Type the customer cell number into the phone field."""
        self.type_when_visible(self._phone_locator(), cell_number)

    def enter_phone_and_blur(self, cell_number: str) -> None:
        """Type a phone number and tab away so the form can re-validate."""
        self.enter_cell_number(cell_number)
        self._phone_locator().press("Tab")

    def enter_valid_phone(self) -> None:
        """Type a valid-format Iranian cell number and remember it for this page."""
        cell = fake_cell_number()
        self._entered_phone = cell
        self.enter_phone_and_blur(cell)

    def _visible(self, locator_key: str, *, timeout_ms: int | None = None) -> bool:
        """Return whether ``LOCATORS[locator_key]`` is visible."""
        wait = timeout_ms if timeout_ms is not None else self.default_timeout_ms
        return self.is_visible(self.LOCATORS[locator_key], timeout_ms=wait)

    def welcome_is_shown(self) -> bool:
        """Return whether the login welcome copy is visible."""
        return self._visible("welcome")

    def phone_instruction_is_shown(self) -> bool:
        """Return whether the phone-entry instruction is visible."""
        return self._visible("phone_instruction")

    def mobile_number_hint_is_shown(self) -> bool:
        """Return whether the mobile-number field hint is visible."""
        return self._visible("phone_field_label")

    def accept_continue_is_shown(self) -> bool:
        """Return whether Accept terms and continue is visible."""
        return self._visible("accept_continue")

    def referral_title_is_shown(self) -> bool:
        """Return whether the referral-code title is visible."""
        return self._visible("referral_title")

    def referral_instruction_is_shown(self) -> bool:
        """Return whether the referral-code instruction is visible."""
        return self._visible("referral_instruction")

    def referral_preview_is_shown(self) -> bool:
        """Return whether the referral code preview is visible."""
        return self._visible("code_preview")

    def activation_sent_is_shown(self) -> bool:
        """Return whether the activation-code-sent copy is visible."""
        return self._visible("activation_sent")

    def activation_boxes_are_shown(self) -> bool:
        """Return whether the first activation code box is visible."""
        return self._visible("otp_first_digit")

    def referral_link_is_shown(self) -> bool:
        """Return whether Have a referral code is visible (short wait)."""
        return self._visible("referral_link", timeout_ms=1_500)

    def entered_phone_is_shown(self) -> bool:
        """Return whether the phone field still holds the number typed here."""
        typed = re.sub(r"\D", "", self._entered_phone)
        shown = re.sub(r"\D", "", self._phone_locator().input_value())
        if not typed or not shown:
            return False
        return shown == typed or shown.endswith(typed[-10:]) or typed.endswith(shown[-10:])

    def phone_input_is_empty(self) -> bool:
        """Return whether the phone field currently has no value."""
        return not self._phone_locator().input_value().strip()

    def is_control_enabled(self, target: LocatorLike) -> bool:
        """Return whether ``target`` is visible and not disabled."""
        loc = self.resolve(target).first
        if not loc.is_visible():
            return False
        if loc.get_attribute("aria-disabled") == "true":
            return False
        if loc.get_attribute("disabled") is not None:
            return False
        class_name = loc.get_attribute("class") or ""
        if "is-disabled" in class_name:
            return False
        return loc.is_enabled()

    def is_accept_continue_clickable(self) -> bool:
        """Return whether Accept terms and continue can be clicked."""
        self.expect_visible(self.LOCATORS["accept_continue"])
        return self.is_control_enabled(self.LOCATORS["accept_continue"])

    def is_confirm_continue_clickable(self) -> bool:
        """Return whether Confirm and continue can be clicked."""
        return self.is_control_enabled(self.LOCATORS["confirm_continue"])

    def is_terms_clickable(self) -> bool:
        """Return whether the Platform terms link is visible and enabled."""
        return self.is_control_enabled(self.LOCATORS["terms_link"])

    def is_referral_link_clickable(self) -> bool:
        """Return whether Have a referral code is visible and enabled."""
        return self.is_control_enabled(self.LOCATORS["referral_link"])

    def is_resend_timer_shown(self) -> bool:
        """Return whether a mm:ss resend timer is visible on activation code."""
        loc = self.page.get_by_text(_TIMER_RE)
        return loc.first.is_visible()

    def is_edit_phone_visible(self) -> bool:
        """Return whether the edit-phone control is on activation code."""
        return self.is_visible(self.LOCATORS["edit_phone"], timeout_ms=3_000)

    def open_referral(self) -> None:
        """Open referral code from login code."""
        self.click_when_visible(self.LOCATORS["referral_link"])
        self.expect_visible(self.LOCATORS["referral_title"])

    def return_from_referral(self) -> None:
        """Tap Back on referral code and wait for login code."""
        self.click_when_visible(self.LOCATORS["referral_back"])
        self.expect_visible(self.LOCATORS["welcome"])

    def open_terms(self) -> None:
        """Open Platform terms of use from login and wait for that screen."""
        self.click_when_visible(self.LOCATORS["terms_link"])
        self.expect_visible(self.LOCATORS["terms_title"])

    def return_from_terms(self) -> None:
        """Tap the terms back arrow and wait until the login form is back."""
        self.click_when_visible(self.LOCATORS["terms_back"])
        self.expect_visible(self.LOCATORS["welcome"])

    def edit_phone_number(self) -> None:
        """Tap the edit-phone control on activation code."""
        self.click_when_visible(self.LOCATORS["edit_phone"])
        self.expect_visible(self.LOCATORS["welcome"])

    def submit_phone_and_accept_terms(self) -> None:
        """Accept terms and continue after entering the phone number."""
        self.click_when_visible(self.LOCATORS["accept_continue"])

    def enter_otp(self, otp: str) -> None:
        """Type the OTP starting at the first digit input."""
        self.click_when_visible(self.LOCATORS["otp_first_digit"])
        self.type_when_visible(self.LOCATORS["otp_first_digit"], otp, delay_ms=80)

    def enter_pin(self, pin_code: str) -> None:
        """Port of ``Enter Pin - UI``."""
        self.fill_when_visible(self.LOCATORS["pin_password"], pin_code)

    def login_with_otp_from_redis(
        self,
        cell_number: str,
        mysql_client: MySQLClient,
        redis_client: RedisClient,
        *,
        pin_code: str = "",
        otp_overwrite: str | None = None,
        skip_walkthrough: bool = True,
        skip_login_popup: bool = True,
    ) -> str:
        """Port of ``APP Login To App Handler``. Returns resolved OTP (for debugging only)."""
        if "/auth/login" not in self.page.url:
            raise RuntimeError(f"Expected login URL containing /auth/login, got {self.page.url!r}")

        self.enter_cell_number(cell_number)
        self.submit_phone_and_accept_terms()

        user_id = self._user_id_from_cell(mysql_client, cell_number)
        otp = otp_overwrite if otp_overwrite else self._otp_from_redis(redis_client, user_id)
        self.enter_otp(otp)

        if pin_code:
            self.enter_pin(pin_code)
        if skip_walkthrough:
            skip_walkthrough_ui(self.page)
        if skip_login_popup:
            dismiss_login_popup_if_present(self.page)
        return otp

    @staticmethod
    def _user_id_from_cell(mysql_client: MySQLClient, cell_number: str) -> str:
        result = mysql_client.fetch_all(
            "uaa_db",
            "SELECT * FROM uaa_db.users WHERE cell_number=%s AND zone_id=%s",
            (cell_number, "app"),
        )
        if result["status_code"] != 0 or not result["body"]:
            raise RuntimeError(
                f"Could not resolve user_id for cell after send-sms: {result['body']}"
            )
        return result["body"][0]["user_id"]

    @staticmethod
    def _otp_from_redis(redis_client: RedisClient, user_id: str) -> str:
        key = f"auth_otp_{user_id}"
        get_otp = redis_client.get_key(key)
        if get_otp["status_code"] != 0:
            raise RuntimeError(f"Get OTP failed: {get_otp['body']}")
        raw = get_otp["body"].get("value")
        if raw is None:
            raise RuntimeError(f"OTP key empty: {key!r}")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        otp_json = json.loads(raw)
        values: list[str] = []
        for group in otp_json.get("otpCodes") or []:
            if isinstance(group, list):
                for item in group:
                    if isinstance(item, dict) and "value" in item:
                        values.append(str(item["value"]))
            elif isinstance(group, dict) and "value" in group:
                values.append(str(group["value"]))
        if not values:
            raise RuntimeError(f"No otpCodes in Redis key {key!r}")
        return values[-1]
