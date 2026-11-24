"""BDD steps for promissory-note suites — thin orchestration only."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.config.settings import Settings
from tests.services.db.mongo_client import MongoDbClient
from tests.services.kyc import promissory_note_asserts as pn_assert
from tests.services.kyc.promissory_note import (
    PromissoryNoteContext,
    PromissoryNoteFlow,
    capture_provider_settings,
    restore_provider_settings,
)
from tests.services.kyc.promissory_note_gherkin import (
    assert_promissory_bad_request,
    assert_promissory_concurrent_result,
    assert_promissory_protected,
    assert_promissory_provider,
    assert_promissory_refund_rejected,
    assert_promissory_renew,
    assert_promissory_renewal_result,
    assert_promissory_start_outcome,
    assert_promissory_success,
    pin_promissory_routing,
    route_promissory_note,
    run_promissory_admin_action,
    run_promissory_concurrent,
    setup_kuknos_tejarat_note,
    start_promissory_note_with,
)
from tests.services.kyc.promissory_note_secrets import require_promissory_note_secrets

scenarios("../features/kyc/promissory_note.feature")
scenarios("../features/kyc/promissory_note_lifecycle.feature")
scenarios("../features/kyc/promissory_note_renew.feature")
scenarios("../features/kyc/promissory_note_negative.feature")
scenarios("../features/kyc/promissory_note_mass.feature")
scenarios("../features/kyc/promissory_note_concurrency.feature")
scenarios("../features/kyc/promissory_note_admin.feature")

pytestmark = [
    pytest.mark.xdist_group("kyc_promissory_note"),
    pytest.mark.usefixtures("pn_provider_guard"),
]


@pytest.fixture(scope="module")
def pn_provider_guard(
    microservice_client: ApiClient,
) -> Generator[dict[str, Any], None, None]:
    """Snapshot provider weights once; restore after the whole promissory module."""
    require_promissory_note_secrets()
    snapshot = capture_provider_settings(microservice_client)
    yield snapshot
    restore_provider_settings(microservice_client, snapshot)


@pytest.fixture
def pn_flow(
    microservice_client: ApiClient,
    mongo_client: MongoDbClient,
    settings: Settings,
    pn_provider_guard: dict[str, Any],
) -> Generator[PromissoryNoteFlow, None, None]:
    """Clean tracked notes; restore pin and hasRenew if this scenario changed them."""
    secrets = CHANGE_ME
    flow = PromissoryNoteFlow(
        microservice_client,
        mongo_client,
        secrets,
        settings,
        settings_snapshot=pn_provider_guard,
    )
    yield flow
    flow.cleanup_tracked_notes()
    flow.restore_pin_if_needed()
    flow.restore_has_renew_if_needed()


@pytest.fixture
def pn_ctx() -> PromissoryNoteContext:
    """Per-scenario envelopes."""
    return PromissoryNoteContext()


@given("the customer has a new promissory tracking code")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_ctx.tracking_code = pn_flow.new_tracking_code()


@given("an issued promissory note exists")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.setup_generated_via_seed(pn_ctx)


@given("an issued promissory note is marked paid without a payment")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.setup_generated_forced_paid(pn_ctx)


@given(
    parsers.re(r"^an issued promissory note is at stage (?P<stage>paid|signed|sealed|confirmed)$")
)
def _(stage: str, pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.setup_generated_forced_status(pn_ctx, stage)


@given("a promissory note has been routed successfully")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.setup_routed_note(pn_ctx)


@given(parsers.re(r"^a Kuknos Tejarat note is (?P<state>[A-Za-z0-9 -]+)$"))
def _(state: str, pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    setup_kuknos_tejarat_note(pn_flow, pn_ctx, state)


@given(parsers.re(r"^routing is set to (?P<pin>Saderat|Kuknos for Tejarat)$"))
def _(pin: str, pn_flow: PromissoryNoteFlow) -> None:
    pin_promissory_routing(pn_flow, pin)


@given("promissory provider routing is configured")
def _(pn_flow: PromissoryNoteFlow) -> None:
    pn_flow.ensure_admin_settings_readable()


@when("the customer asks for that promissory note")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_inquiry(pn_ctx)


@when(parsers.re(r"^the customer routes that note (?P<mode>[A-Za-z0-9 -]+)$"))
def _(mode: str, pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    route_promissory_note(pn_flow, pn_ctx, mode)


@when("the customer starts that promissory note")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_init_after_route(pn_ctx)


@when("an administrator cancels the promissory note")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_admin_cancel(pn_ctx)


@when("the customer requests a refund for the promissory note")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_refund(pn_ctx)


@when("the customer starts stamp payment for the note")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_payment_init(pn_ctx)


@when("the customer requests a signature without a ticket")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_sign_request(pn_ctx)


@when(parsers.re(r"^the customer starts a promissory note without (?P<detail>[A-Za-z0-9 ]+)$"))
def _(detail: str, pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_init_missing_detail(pn_ctx, detail)


@when(parsers.re(r"^the customer starts a promissory note with (?P<mode>[A-Za-z0-9 -]+)$"))
def _(mode: str, pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    start_promissory_note_with(pn_flow, pn_ctx, mode)


@when("the customer cancels that promissory note")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_user_cancel_unknown(pn_ctx)


@when("the customer seals that note without a sign reference")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_seal_without_sign_tc(pn_ctx)


@when(parsers.re(r"^concurrent (?P<kind>[A-Za-z0-9 -]+)$"))
def _(kind: str, pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    run_promissory_concurrent(pn_flow, pn_ctx, kind)


@when(parsers.re(r"^an administrator (?P<action>(?:opens|searches) promissory[A-Za-z0-9 -]+)$"))
def _(action: str, pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    run_promissory_admin_action(pn_flow, pn_ctx, action)


@when("an administrator reverts status for that unknown promissory note")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_admin_status_revert_unknown(pn_ctx)


@when("an administrator notifies a generated batch with that unknown code")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_flow.store_admin_notify_unknown(pn_ctx)


@then("the promissory note is not found")
def _(pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_promissory_not_found(pn_ctx)


@then(parsers.re(r"^the note is assigned to the (?P<provider>Saderat|Kuknos) provider$"))
def _(provider: str, pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    assert_promissory_provider(pn_flow, pn_ctx, provider)


@then(parsers.re(r"^renew is (?P<availability>available|not available) for that note$"))
def _(availability: str, pn_ctx: PromissoryNoteContext) -> None:
    assert_promissory_renew(pn_ctx, availability)


@then("the promissory note is canceled")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_note_canceled(pn_flow, pn_ctx)


@then(parsers.re(r"^the refund is rejected (?P<reason>[A-Za-z0-9 -]+)$"))
def _(reason: str, pn_ctx: PromissoryNoteContext) -> None:
    assert_promissory_refund_rejected(pn_ctx, reason)


@then("the inquiry shows the note at that stage")
def _(pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_inquiry_status(pn_ctx)


@then("the payment request is rejected")
def _(pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_rejected_unprocessable(pn_ctx)


@then(parsers.re(r"^the promissory request (?P<reason>[A-Za-z0-9 -]+) is rejected$"))
def _(reason: str, pn_ctx: PromissoryNoteContext) -> None:
    assert_promissory_bad_request(pn_ctx, reason)


@then(parsers.re(r"^starting without (?P<detail>[A-Za-z0-9 ]+) is rejected$"))
def _(detail: str, pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_init_missing_detail(pn_ctx, detail)


@then("the request is rejected as invalid")
def _(pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_invalid_parameter(pn_ctx)


@then(parsers.re(r"^the promissory action (?P<result>[A-Za-z0-9 -]+)$"))
def _(result: str, pn_ctx: PromissoryNoteContext) -> None:
    assert_promissory_success(pn_ctx, result)


@then(parsers.re(r"^the promissory start (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(outcome: str, pn_ctx: PromissoryNoteContext) -> None:
    assert_promissory_start_outcome(pn_ctx, outcome)


@then(parsers.re(r"^the promissory note was (?P<renewal>[A-Za-z0-9 -]+)$"))
def _(renewal: str, pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    assert_promissory_renewal_result(pn_flow, pn_ctx, renewal)


@then(
    parsers.re(
        r"^the note does not keep those protected attributes from "
        r"(?P<action>routing|starting)$"
    )
)
def _(action: str, pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    assert_promissory_protected(pn_flow, pn_ctx, action)


@then(
    parsers.re(r"^each concurrent response is (?P<result>a known business result|note not found)$")
)
def _(result: str, pn_ctx: PromissoryNoteContext) -> None:
    assert_promissory_concurrent_result(pn_ctx, result)


@then("the concurrent inquiries remain available")
def _(pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_concurrent_healthy(pn_ctx)


@then("at least one cancel succeeds")
def _(pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_concurrent_at_least_one_success(pn_ctx)


@then("exactly one promissory note exists for that tracking code")
def _(pn_flow: PromissoryNoteFlow, pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_exactly_one_note(pn_flow, pn_ctx)


@then("the provider settings include the current configuration")
def _(pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_settings_detail(pn_ctx)


@then("the settings search includes a recipient list")
def _(pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_settings_search_recipients(pn_ctx)


@then("the success rates are listed")
def _(pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_success_rate_list(pn_ctx)


@then("the success-rate history can be browsed page by page")
def _(pn_ctx: PromissoryNoteContext) -> None:
    pn_assert.assert_success_rate_paginated(pn_ctx)
