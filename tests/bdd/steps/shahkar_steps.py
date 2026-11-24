"""BDD steps for basic Shahkar cell-number inquiry — thin orchestration only."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.services.db.mongo_client import MongoDbClient
from tests.services.kyc import shahkar_asserts as shahkar_assert
from tests.services.kyc.shahkar import ShahkarContext, ShahkarFlow
from tests.services.kyc.shahkar_gherkin import (
    assert_shahkar_inquiry_outcome,
    inquire_shahkar,
    prepare_shahkar_identity,
)
from tests.services.kyc.shahkar_secrets import require_shahkar_secrets

scenarios("../features/kyc/shahkar_inquiry.feature")

pytestmark = pytest.mark.xdist_group("kyc_shahkar")


@pytest.fixture
def shahkar_flow(
    microservice_client: ApiClient,
    mongo_client: MongoDbClient,
) -> Generator[ShahkarFlow, None, None]:
    """Clear journals; pin and restore provider weights only when a cell is selected."""
    secrets = CHANGE_ME
    flow = ShahkarFlow(microservice_client, mongo_client, secrets)
    flow.prepare()
    yield flow
    flow.teardown()


@pytest.fixture
def shahkar_ctx(shahkar_flow: ShahkarFlow) -> ShahkarContext:
    """Per-scenario inquiry and journal envelopes."""
    return ShahkarContext(secrets=shahkar_flow.secrets)


@given(
    parsers.re(
        r"^the customer has (?P<identity>[A-Za-z0-9 ]*"
        r"(?:cell number(?: that does not belong to them)?|national identity))$"
    )
)
def _(identity: str, shahkar_flow: ShahkarFlow, shahkar_ctx: ShahkarContext) -> None:
    prepare_shahkar_identity(shahkar_flow, shahkar_ctx, identity)


@when(parsers.re(r"^the customer inquires (?P<mode>Shahkar(?: twice)?)$"))
def _(mode: str, shahkar_flow: ShahkarFlow, shahkar_ctx: ShahkarContext) -> None:
    inquire_shahkar(shahkar_flow, shahkar_ctx, mode)


@when(parsers.re(r"^the customer submits a Shahkar inquiry with (?P<fault>[A-Za-z0-9 ]+)$"))
def _(fault: str, shahkar_flow: ShahkarFlow, shahkar_ctx: ShahkarContext) -> None:
    shahkar_flow.store_fault_inquiry(shahkar_ctx, fault)


@then(parsers.re(r"^the Shahkar inquiry is (?P<outcome>verified|unverified|rejected)$"))
def _(outcome: str, shahkar_ctx: ShahkarContext) -> None:
    assert_shahkar_inquiry_outcome(shahkar_ctx, outcome)


@then("the first Shahkar journal was live and the latest was cached")
def _(shahkar_ctx: ShahkarContext) -> None:
    shahkar_assert.assert_cache_miss_then_hit(shahkar_ctx)
