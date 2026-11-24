"""Step definitions for tests/bdd/features/payment/health_check.feature."""

from typing import Any

from pytest_bdd import scenarios, then, when

from tests.api.client import ApiClient, ApiSide
from tests.api.payment.health_check import HealthCheckBody, get_user_health_check_status
from tests.config.settings import Settings
from tests.services.assert_report import AssertionReport, assert_isinstance, assert_status_ok

scenarios("../features/payment/health_check.feature")


@when("the health check service is called with that token", target_fixture="health_check_result")
def _(settings: Settings, access_token: str) -> dict[str, Any]:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return get_user_health_check_status(client)


@then("the health check reports the service as active")
def _(health_check_result: dict[str, Any]) -> None:
    assert_status_ok("Health check request", health_check_result)
    body = health_check_result["body"]
    assert_isinstance("Health check response body", body, HealthCheckBody)
    AssertionReport("Health check service is active").equals(
        "status_info", actual=body.status_info, expected=0
    ).assert_all()
