"""BDD steps for postal-code address inquiry — thin orchestration only."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.services.db.mongo_client import MongoDbClient
from tests.services.kyc import postal_code_asserts as postal_assert
from tests.services.kyc.postal_code import PostalCodeContext, PostalCodeFlow
from tests.services.kyc.postal_code_gherkin import (
    assert_postal_inquiry_outcome,
    inquire_postal_code,
)
from tests.services.kyc.postal_code_secrets import require_postal_code_secrets

scenarios("../features/kyc/postal_code.feature")

pytestmark = pytest.mark.xdist_group("kyc_postal_code")


@pytest.fixture
def postal_code_flow(
    microservice_client: ApiClient,
    mongo_client: MongoDbClient,
) -> Generator[PostalCodeFlow, None, None]:
    """Snapshot weights, clear journals, restore settings after the scenario."""
    secrets = CHANGE_ME
    flow = PostalCodeFlow(microservice_client, mongo_client, secrets)
    flow.prepare()
    yield flow
    flow.teardown()


@pytest.fixture
def postal_code_ctx(postal_code_flow: PostalCodeFlow) -> PostalCodeContext:
    """Per-scenario inquiry and journal envelopes."""
    return PostalCodeContext(secrets=postal_code_flow.secrets)


@given("the live address provider weights are recorded")
def _(postal_code_flow: PostalCodeFlow) -> None:
    postal_code_flow.record_live_weights()


@given(parsers.re(r"^the address provider is (?P<provider>jibit|sitaad)$"))
def _(provider: str, postal_code_flow: PostalCodeFlow, postal_code_ctx: PostalCodeContext) -> None:
    postal_code_flow.pin_provider(postal_code_ctx, provider)


@when(parsers.re(r"^the customer inquires (?P<mode>[A-Za-z0-9 ]+postal code(?: twice)?)$"))
def _(
    mode: str,
    postal_code_flow: PostalCodeFlow,
    postal_code_ctx: PostalCodeContext,
) -> None:
    inquire_postal_code(postal_code_flow, postal_code_ctx, mode)


@when(parsers.re(r"^staff submit invalid address provider weights for (?P<rule>[A-Za-z0-9 ]+)$"))
def _(rule: str, postal_code_flow: PostalCodeFlow, postal_code_ctx: PostalCodeContext) -> None:
    postal_code_flow.submit_invalid_weights(postal_code_ctx, rule)


@then(parsers.re(r"^the postal-code inquiry (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, postal_code_ctx: PostalCodeContext) -> None:
    assert_postal_inquiry_outcome(postal_code_ctx, outcome)


@then("the live journal matches the provider address")
def _(postal_code_ctx: PostalCodeContext) -> None:
    postal_assert.assert_live_success_journal(postal_code_ctx)


@then("the live journal is a not-found failure")
def _(postal_code_ctx: PostalCodeContext) -> None:
    postal_assert.assert_live_not_found_journal(postal_code_ctx)


@then("the first postal-code journal was live and the latest was cached")
def _(postal_code_ctx: PostalCodeContext) -> None:
    postal_assert.assert_cache_miss_then_hit(postal_code_ctx)


@then(parsers.re(r"^the address provider settings are rejected as (?P<title>[A-Za-z0-9_]+)$"))
def _(
    title: str,
    postal_code_ctx: PostalCodeContext,
    postal_code_flow: PostalCodeFlow,
) -> None:
    postal_assert.assert_settings_rejected(postal_code_ctx, title, postal_code_flow)
