"""BDD steps for native digital signature — thin orchestration only."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.services.db.mongo_client import MongoDbClient
from tests.services.kyc.digital_signature import (
    DigitalSignatureContext,
    DigitalSignatureFlow,
)
from tests.services.kyc.digital_signature_gherkin import (
    assert_digital_signature_dsp,
    assert_digital_signature_response,
    initiate_digital_signature,
    prepare_digital_signature,
    validate_digital_signature_password,
)
from tests.services.kyc.digital_signature_secrets import require_digital_signature_secrets

scenarios("../features/kyc/digital_signature.feature")

pytestmark = pytest.mark.xdist_group("kyc_digital_signature")


@pytest.fixture
def ds_flow(
    microservice_client: ApiClient,
    mongo_client: MongoDbClient,
) -> Generator[DigitalSignatureFlow, None, None]:
    """Clean shared UAT digital-signature state before and after each scenario."""
    secrets = require_digital_signature_secrets()
    flow = DigitalSignatureFlow(microservice_client, mongo_client, secrets)
    flow.prepare_clean_state()
    yield flow
    flow.prepare_clean_state_best_effort()


@pytest.fixture
def ds_ctx(ds_flow: DigitalSignatureFlow) -> DigitalSignatureContext:
    """Per-scenario tracking codes and last API result."""
    return DigitalSignatureContext(secrets=ds_flow.secrets)


@given("the customer has completed native liveness")
def _(ds_flow: DigitalSignatureFlow) -> None:
    ds_flow.complete_liveness()


@given(parsers.re(r"^the customer has (?P<liveness_prep>[A-Za-z0-9 ]+) for digital signature$"))
def _(liveness_prep: str, ds_flow: DigitalSignatureFlow) -> None:
    ds_flow.apply_incomplete_liveness_prep(liveness_prep)


@given(
    parsers.re(r"^the customer has (?P<setup>(?:initiated a basic|a generated) digital signature)$")
)
def _(setup: str, ds_flow: DigitalSignatureFlow, ds_ctx: DigitalSignatureContext) -> None:
    prepare_digital_signature(ds_flow, ds_ctx, setup)


@when(
    parsers.re(
        r"^the customer initiates (?P<mode>[A-Za-z0-9 ]+digital signature(?: without a password)?)$"
    )
)
def _(mode: str, ds_flow: DigitalSignatureFlow, ds_ctx: DigitalSignatureContext) -> None:
    initiate_digital_signature(ds_flow, ds_ctx, mode)


@when("the customer generates the digital signature certificate")
def _(ds_flow: DigitalSignatureFlow, ds_ctx: DigitalSignatureContext) -> None:
    ds_flow.store_generate(ds_ctx)


@when("the customer revokes the digital signature")
def _(ds_flow: DigitalSignatureFlow, ds_ctx: DigitalSignatureContext) -> None:
    ds_flow.store_revoke(ds_ctx)


@when(parsers.re(r"^the customer validates (?P<mode>[A-Za-z0-9 ]+digital signature password)$"))
def _(mode: str, ds_flow: DigitalSignatureFlow, ds_ctx: DigitalSignatureContext) -> None:
    validate_digital_signature_password(ds_flow, ds_ctx, mode)


@then(parsers.re(r"^the digital signature (?P<result>[A-Za-z0-9 -]+)$"))
def _(result: str, ds_ctx: DigitalSignatureContext) -> None:
    assert_digital_signature_response(ds_ctx, result)


@then(parsers.re(r"^the provider signature record is (?P<record>[A-Za-z0-9 -]+)$"))
def _(record: str, ds_flow: DigitalSignatureFlow, ds_ctx: DigitalSignatureContext) -> None:
    assert_digital_signature_dsp(ds_flow, ds_ctx, record)
