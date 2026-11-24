"""BDD steps for identity registration inquiry — thin orchestration only."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.services.db.mongo_client import MongoDbClient
from tests.services.kyc import registration_inquiry_asserts as registration_assert
from tests.services.kyc.registration_inquiry import (
    RegistrationInquiryContext,
    RegistrationInquiryFlow,
)
from tests.services.kyc.registration_inquiry_gherkin import submit_registration_inquiry
from tests.services.kyc.registration_inquiry_secrets import (
    require_registration_inquiry_secrets,
)

scenarios("../features/kyc/registration_inquiry.feature")

pytestmark = pytest.mark.xdist_group("kyc_registration_inquiry")


@pytest.fixture
def registration_flow(
    microservice_client: ApiClient,
    mongo_client: MongoDbClient,
) -> Generator[RegistrationInquiryFlow, None, None]:
    """Snapshot weights, clear journals, restore settings after the scenario."""
    secrets = CHANGE_ME
    flow = RegistrationInquiryFlow(microservice_client, mongo_client, secrets)
    flow.prepare()
    yield flow
    flow.teardown()


@pytest.fixture
def registration_ctx(registration_flow: RegistrationInquiryFlow) -> RegistrationInquiryContext:
    """Per-scenario inquiry and journal envelopes."""
    return RegistrationInquiryContext(secrets=registration_flow.secrets)


@given("the live registration provider weights are recorded")
def _(registration_flow: RegistrationInquiryFlow) -> None:
    registration_flow.record_live_weights()


@given(
    parsers.re(
        r"^the registration provider is (?P<provider>hafezsaman|jibit) "
        r"for a (?P<kind>basic|full) inquiry$"
    )
)
def _(
    provider: str,
    kind: str,
    registration_flow: RegistrationInquiryFlow,
    registration_ctx: RegistrationInquiryContext,
) -> None:
    registration_flow.pin_provider(registration_ctx, provider, kind)


@when(
    parsers.re(
        r"^the customer submits a (?P<kind>basic|full) inquiry "
        r"(?P<mode>(?!using )[A-Za-z0-9 ]+)$"
    )
)
def _(
    kind: str,
    mode: str,
    registration_flow: RegistrationInquiryFlow,
    registration_ctx: RegistrationInquiryContext,
) -> None:
    submit_registration_inquiry(registration_flow, registration_ctx, kind, mode)


@when(
    parsers.re(
        r"^the customer submits a (?P<kind>basic|full) inquiry using "
        r"(?P<fault>[A-Za-z0-9 ]+)$"
    )
)
def _(
    kind: str,
    fault: str,
    registration_flow: RegistrationInquiryFlow,
    registration_ctx: RegistrationInquiryContext,
) -> None:
    registration_flow.inquire_fault(registration_ctx, kind, fault)


@when(parsers.re(r"^staff submit invalid registration weights for (?P<rule>[A-Za-z0-9 ]+)$"))
def _(
    rule: str,
    registration_flow: RegistrationInquiryFlow,
    registration_ctx: RegistrationInquiryContext,
) -> None:
    registration_flow.submit_invalid_weights(registration_ctx, rule)


@then("the registration inquiry returns the person")
def _(registration_ctx: RegistrationInquiryContext) -> None:
    registration_assert.assert_person_returned(registration_ctx)


@then("the live journal matches the person")
def _(registration_ctx: RegistrationInquiryContext) -> None:
    registration_assert.assert_success_journal(registration_ctx)


@then("the first registration journal was live and the latest was cached")
def _(registration_ctx: RegistrationInquiryContext) -> None:
    registration_assert.assert_cache_miss_then_hit(registration_ctx)


@then(parsers.re(r"^the registration inquiry is rejected as (?P<title>[A-Za-z0-9_]+)$"))
def _(title: str, registration_ctx: RegistrationInquiryContext) -> None:
    registration_assert.assert_inquiry_rejected(registration_ctx, title)


@then(parsers.re(r"^the registration provider settings are rejected as (?P<title>[A-Za-z0-9_]+)$"))
def _(
    title: str,
    registration_ctx: RegistrationInquiryContext,
    registration_flow: RegistrationInquiryFlow,
) -> None:
    registration_assert.assert_settings_rejected(registration_ctx, title, registration_flow)
