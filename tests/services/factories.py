"""Test data factories for fresh UAT businesses and app users.

Port of fresh-business-initializer-service.resource (BusinessFactory) and
fresh-user-initializer-service.resource (UserFactory).

Classes wired via pytest fixtures, never module-level singletons — see
``.cursor/rules/pytest-architecture.mdc``.

Fake Iranian cell / national-code generators live in ``tests.services.fake_ids``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from faker import Faker
from pydantic import BaseModel

from tests.api.client import ApiClient, ApiSide
from tests.api.uaa.businesses import business_id_from_create_body, post_admin_businesses
from tests.services.api_assert import ensure_status
from tests.services.auth import complete_login_with_otp, send_otp_sms_and_resolve_user
from tests.services.db.mysql_client import MySQLClient
from tests.services.db.redis_client import RedisClient
from tests.services.fake_ids import fake_cell_number, fake_national_code

logger = logging.getLogger(__name__)


class Business(BaseModel):
    """UAT business created by ``BusinessFactory``."""

    business_id: str
    business_name: str
    user_name: str
    password: CHANGE_ME


class User(BaseModel):
    """App user created or resolved by ``UserFactory``."""

    user_id: str
    user_cell_number: str
    user_national_code: str
    access_token: str = ""
    refresh_token: str = ""
    device_id: str = ""


_EMPTY_AUTH: dict[str, str] = {
    "access_token": "",
    "refresh_token": "",
    "device_id": "",
}


class BusinessFactory:
    """Port of fresh-business-initializer-service.resource.

    Always creates businesses on the microservice side, matching the Robot
    keyword — the Robot code hardcodes ``${MICROSERVICE_SIDE}`` regardless of
    caller context.
    """

    DEFAULT_ROLES = ["BUSINESS_ADMIN"]

    def __init__(self, client: ApiClient) -> None:
        if client.side is not ApiSide.MICROSERVICE:
            raise ValueError("BusinessFactory requires an ApiClient on the microservice side")
        self._client = client
        self._faker = Faker()

    def create(
        self,
        roles: list[str] | None = None,
        zone: str | None = None,
        max_retry: int = 60,
    ) -> Business:
        """Port of Generate A Fresh Business — retries with fresh fake data.

        Retries until creation succeeds or ``max_retry`` attempts are exhausted.
        """
        roles = roles or self.DEFAULT_ROLES
        last_result: dict[str, Any] = {}
        for _ in range(max_retry):
            username, password = self._fake_business()
            last_result = post_admin_businesses(
                self._client, username, username, password, roles, zone
            )
            if last_result["status_code"] == 200:
                return Business(
                    business_id=business_id_from_create_body(last_result["body"]),
                    business_name=username,
                    user_name=username,
                    password=CHANGE_ME
                )
        raise RuntimeError(
            f"Business creation failed after {max_retry} tries; "
            f"last status_code={last_result.get('status_code')}"
        )

    def _fake_business(self) -> tuple[str, str]:
        """Port of Generate A Fake Business.

        Username and business name are the same generated string, matching Robot.
        """
        username = (
            f"Test-{self._faker.color_name()}-{self._faker.first_name()}-"
            f"{self._faker.country()}-{self._faker.email()}"
        )
        return username, self._faker.password()


class UserFactory:
    """Port of fresh-user-initializer-service.resource.

    - ``create`` → Generate A Fresh User
    - ``create_predefined`` → Generate A Predefined User

    Requires an APP-side ``ApiClient`` with ``APP_BASIC_AUTH``, plus
    ``RedisClient`` (OTP) and ``MySQLClient`` (uniqueness + national-code update).
    """

    def __init__(
        self,
        app_client: ApiClient,
        redis_client: RedisClient,
        mysql_client: MySQLClient,
    ) -> None:
        if app_client.side is not ApiSide.APP:
            raise ValueError("UserFactory requires an ApiClient on the app side")
        self._app_client = app_client
        self._redis_client = redis_client
        self._mysql_client = mysql_client

    def create(
        self,
        cell_number_prefix: str | None = None,
        max_retry: int = 60,
        login_timeout_seconds: float = 60.0,
        login_poll_seconds: float = 1.0,
    ) -> User:
        """Port of Generate A Fresh User.

        Generates unused cell/national identifiers, logs in, then persists the
        national code when the user row still lacks one.
        """
        if cell_number_prefix is not None and len(str(cell_number_prefix)) > 11:
            raise ValueError(
                f"Cell number prefix length must be <= 11 but found: {cell_number_prefix!r}"
            )

        cell_number = self._generate_fresh_cell_number(
            max_retry=max_retry,
            predefined_prefix=cell_number_prefix,
        )
        national_code = self._generate_fresh_national_code(max_retry=max_retry)
        auth = self._login_to_app_with_retry(
            cell_number,
            timeout_seconds=login_timeout_seconds,
            poll_seconds=login_poll_seconds,
        )
        user_id = self._retrieve_user_id_from_cell_number(cell_number)
        return self._finalize_user(cell_number, national_code, user_id, auth)

    def create_predefined(
        self,
        cell_number: str,
        national_code: str,
        *,
        login_timeout_seconds: float = 60.0,
        login_poll_seconds: float = 1.0,
        ensure_login: bool = False,
    ) -> User:
        """Port of Generate A Predefined User.

        Validates cell/national consistency across ``user_db`` / ``switch_credit_db``,
        logs in only when the cell is new (Robot behavior). Set ``ensure_login=True``
        to always obtain tokens (improvement for API tests that need Bearer auth).
        """
        cell_exists = self._cell_number_exists(cell_number)
        if not cell_exists and self._national_code_exists(national_code):
            raise RuntimeError(
                f"cell number was not found, but a matching national code "
                f"{national_code} was found in either switch_credit_db or users_db. "
                f"Make sure your cell number is correct or use a different national code"
            )

        auth = dict(_EMPTY_AUTH)
        if not cell_exists:
            auth = self._login_to_app_with_retry(
                cell_number,
                timeout_seconds=login_timeout_seconds,
                poll_seconds=login_poll_seconds,
            )
        user_id = self._retrieve_user_id_from_cell_number(cell_number)

        if ensure_login and not auth.get("access_token"):
            auth = self._login_to_app_with_retry(
                cell_number,
                timeout_seconds=login_timeout_seconds,
                poll_seconds=login_poll_seconds,
            )
        return self._finalize_user(cell_number, national_code, user_id, auth)

    def _finalize_user(
        self,
        cell_number: str,
        national_code: str,
        user_id: str,
        auth: dict[str, str],
    ) -> User:
        self._update_user_database_by_national_code(cell_number, national_code)
        return User(
            user_id=user_id,
            user_cell_number=cell_number,
            user_national_code=national_code,
            access_token=auth.get("access_token", ""),
            refresh_token=auth.get("refresh_token", ""),
            device_id=auth.get("device_id", ""),
        )

    def _cell_number_exists(self, cell_number: str) -> bool:
        """Port of Check If Cell Number Does exist."""
        return self._column_value_exists_in_user_dbs("cell_number", cell_number)

    def _national_code_exists(self, national_code: str) -> bool:
        """Port of Check If National Code Does exist."""
        return self._column_value_exists_in_user_dbs("national_code", national_code)

    def _column_value_exists_in_user_dbs(self, column: str, value: str) -> bool:
        """Shared uniqueness check across ``user_db`` / ``switch_credit_db``."""
        for db_name in ("switch_credit_db", "user_db"):
            query = f"SELECT * FROM {db_name}.users WHERE {column} = %s"
            result = ensure_status(
                self._mysql_client.fetch_all(db_name, query, (value,)),
                0,
                context=f"MySQL uniqueness check on {db_name}.users.{column}",
            )
            if result["body"]:
                return True
        return False

    def _generate_fresh_cell_number(
        self,
        max_retry: int,
        predefined_prefix: str | None,
    ) -> str:
        """Port of Generate A Fresh Cell Number."""
        for _ in range(max_retry):
            cell_number = fake_cell_number(predefined_prefix)
            if not self._cell_number_exists(cell_number):
                return cell_number
        raise RuntimeError(f"cell number generation FAILED after {max_retry} tries")

    def _generate_fresh_national_code(self, max_retry: int) -> str:
        """Port of Generate A Fresh National Code."""
        for _ in range(max_retry):
            national_code = fake_national_code()
            if not self._national_code_exists(national_code):
                return national_code
        raise RuntimeError(f"national code generation FAILED after {max_retry} tries")

    def _login_to_app_with_retry(
        self,
        cell_number: str,
        timeout_seconds: float,
        poll_seconds: float,
    ) -> dict[str, str]:
        """Port of Wait Until Keyword Succeeds … Login To App.

        Sends the OTP SMS exactly ONCE, then retries only the OTP-read +
        activate step (``complete_login_with_otp``) until it succeeds or
        ``timeout_seconds`` elapses. The original port called ``login_to_app``
        (send-sms included) on every retry, which re-sent a fresh SMS each
        second — that reliably tripped Platform's ``USER_SEND_SMS_MAX_EXCEEDED``
        throttle within ~15s and masked whatever the real per-attempt error
        was (only the last exception, the rate-limit one, ever surfaced).

        Returns the auth dict from ``complete_login_with_otp`` so callers can
        reuse tokens instead of logging in a second time.
        """
        user_id, device_info, device_id = send_otp_sms_and_resolve_user(
            self._app_client, self._mysql_client, cell_number
        )
        deadline = time.monotonic() + timeout_seconds
        last_error: BaseException | None = None
        attempt = 0
        while time.monotonic() < deadline:
            attempt += 1
            try:
                return complete_login_with_otp(
                    self._app_client,
                    self._redis_client,
                    user_id,
                    device_info,
                    device_id,
                    pin_code="",
                )
            except RuntimeError as exc:
                last_error = exc
                logger.debug(
                    "complete_login_with_otp attempt %d for user_id=%s failed: %s",
                    attempt,
                    user_id,
                    exc,
                )
                time.sleep(poll_seconds)
        raise RuntimeError(
            f"Login To App did not succeed within {timeout_seconds}s "
            f"({attempt} OTP-read attempts, no new SMS sent after the first); "
            f"last error: {last_error}"
        ) from last_error

    def _retrieve_user_id_from_cell_number(self, cell_number: str) -> str:
        """Port of Retrieve User Id From Cell Number (reads ``user_db``)."""
        result = self._mysql_client.fetch_all(
            "user_db",
            "SELECT * FROM user_db.users WHERE cell_number = %s",
            (cell_number,),
        )
        if result["status_code"] != 0 or not result["body"]:
            raise RuntimeError(
                f"Could not retrieve user_id for cell_number after login: {result['body']}"
            )
        return result["body"][0]["user_id"]

    def _update_user_database_by_national_code(
        self,
        cell_number: str,
        national_code: str,
    ) -> None:
        """Port of Update User Database by National Code."""
        result = self._mysql_client.fetch_all(
            "user_db",
            "SELECT * FROM user_db.users WHERE cell_number = %s",
            (cell_number,),
        )
        if result["status_code"] != 0 or not result["body"]:
            raise RuntimeError(
                "Expected the user to have logged in at least once; "
                "no user_db row found for the cell number"
            )
        row = result["body"][0]
        found = row.get("national_code")
        if found is None or found == "None" or found == "":
            ensure_status(
                self._mysql_client.execute_query(
                    "user_db",
                    "UPDATE user_db.users SET national_code = %s WHERE cell_number = %s",
                    (national_code, cell_number),
                ),
                0,
                context=f"Set national_code for cell_number={cell_number}",
            )
        elif str(found) != str(national_code):
            raise RuntimeError(
                f"Invalid national_code: expected unset or {national_code!r}, found {found!r}"
            )
