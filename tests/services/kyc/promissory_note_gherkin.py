"""Gherkin regex and dispatch for promissory-note wording families.

Step files keep the same ``r"..."`` inline on the decorator; these constants
feed ``tests/unit/test_step_regexes.py``. Pattern conventions:
``.cursor/rules/step-patterns.mdc``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tests.services.kyc import promissory_note_asserts as pn_assert
from tests.services.kyc.promissory_note import PromissoryNoteContext, PromissoryNoteFlow

PROMISSORY_STAGE_STEP = (
    r"^an issued promissory note is at stage (?P<stage>paid|signed|sealed|confirmed)$"
)
PROMISSORY_PIN_STEP = r"^routing is set to (?P<pin>Saderat|Kuknos for Tejarat)$"
PROMISSORY_ROUTE_STEP = r"^the customer routes that note (?P<mode>[A-Za-z0-9 -]+)$"
PROMISSORY_INIT_MISSING_STEP = (
    r"^the customer starts a promissory note without (?P<detail>[A-Za-z0-9 ]+)$"
)
PROMISSORY_INIT_WITH_STEP = r"^the customer starts a promissory note with (?P<mode>[A-Za-z0-9 -]+)$"
PROMISSORY_INIT_MISSING_REJECTED_STEP = r"^starting without (?P<detail>[A-Za-z0-9 ]+) is rejected$"
PROMISSORY_ADMIN_STEP = (
    r"^an administrator (?P<action>(?:opens|searches) promissory[A-Za-z0-9 -]+)$"
)
PROMISSORY_CONCURRENT_STEP = r"^concurrent (?P<kind>[A-Za-z0-9 -]+)$"
PROMISSORY_RENEW_STEP = r"^renew is (?P<availability>available|not available) for that note$"
PROMISSORY_PROVIDER_STEP = r"^the note is assigned to the (?P<provider>Saderat|Kuknos) provider$"
PROMISSORY_BAD_REQUEST_STEP = r"^the promissory request (?P<reason>[A-Za-z0-9 -]+) is rejected$"
PROMISSORY_SUCCESS_STEP = r"^the promissory action (?P<result>[A-Za-z0-9 -]+)$"
PROMISSORY_REFUND_REJECTED_STEP = r"^the refund is rejected (?P<reason>[A-Za-z0-9 -]+)$"
PROMISSORY_PROTECTED_STEP = (
    r"^the note does not keep those protected attributes from "
    r"(?P<action>routing|starting)$"
)
PROMISSORY_CONCURRENT_RESULT_STEP = (
    r"^each concurrent response is (?P<result>a known business result|note not found)$"
)
PROMISSORY_KUKNOS_NOTE_STEP = r"^a Kuknos Tejarat note is (?P<state>[A-Za-z0-9 -]+)$"
PROMISSORY_START_OUTCOME_STEP = r"^the promissory start (?P<outcome>[A-Za-z0-9 -]+)$"
PROMISSORY_RENEWAL_RESULT_STEP = r"^the promissory note was (?P<renewal>[A-Za-z0-9 -]+)$"

_T = TypeVar("_T")
_FlowAction = Callable[[PromissoryNoteFlow, PromissoryNoteContext], None]
_CtxAction = Callable[[PromissoryNoteContext], None]
_FlowOnly = Callable[[PromissoryNoteFlow], None]


def _require(table: dict[str, _T], key: str, label: str) -> _T:
    handler = table.get(key)
    if handler is None:
        raise KeyError(f"No {label} for {key!r}; known: {sorted(table)}")
    return handler


_PINS: dict[str, _FlowOnly] = {
    "Saderat": lambda flow: flow.pin_routing("Saderat"),
    "Kuknos for Tejarat": lambda flow: flow.pin_routing("Kuknos for Tejarat"),
}
_ROUTE_MODES: dict[str, _FlowAction] = {
    "to Saderat": lambda flow, ctx: flow.store_route_for_bank(ctx, "Saderat"),
    "to Tejarat": lambda flow, ctx: flow.store_route_for_bank(ctx, "Tejarat"),
    "without a requesting business": lambda flow, ctx: flow.store_route_without_requester(ctx),
    "to an unsupported recipient": lambda flow, ctx: flow.store_route_bad_recipient(ctx),
    "with protected attributes set by the client": (
        lambda flow, ctx: flow.store_route_with_injected(ctx)
    ),
}
_INIT_WITH_MODES: dict[str, _FlowAction] = {
    "a non-numeric amount": lambda flow, ctx: flow.store_init_non_numeric_amount(ctx),
    "an oversized description": lambda flow, ctx: flow.store_init_long_description(ctx),
    "protected attributes set by the client": (
        lambda flow, ctx: flow.store_init_with_injected(ctx)
    ),
}
_ADMIN_ACTIONS: dict[str, _FlowAction] = {
    "opens promissory provider settings": (lambda flow, ctx: flow.store_admin_settings_get(ctx)),
    "searches promissory settings recipients": (
        lambda flow, ctx: flow.store_admin_settings_search(ctx)
    ),
    "opens promissory success rates": lambda flow, ctx: flow.store_admin_success_rate(ctx),
    "searches promissory success-rate history": (
        lambda flow, ctx: flow.store_admin_success_rate_search(ctx)
    ),
}
_CONCURRENT_KINDS: dict[str, _FlowAction] = {
    "route requests are issued for that code": (
        lambda flow, ctx: flow.store_concurrent_routes(ctx)
    ),
    "admin cancel requests are issued": (
        lambda flow, ctx: flow.store_concurrent_admin_cancels(ctx)
    ),
    "inquiry requests are issued": lambda flow, ctx: flow.store_concurrent_inquiries(ctx),
}
_RENEW: dict[str, _CtxAction] = {
    "available": lambda ctx: pn_assert.assert_route_renew(ctx, offered=True),
    "not available": lambda ctx: pn_assert.assert_route_renew(ctx, offered=False),
}
_PROVIDERS: dict[str, _FlowAction] = {
    "Saderat": pn_assert.assert_saderat_routed,
    "Kuknos": pn_assert.assert_kuknos_routed,
}
_BAD_REQUESTS: dict[str, _CtxAction] = {
    "routing without a requesting business": pn_assert.assert_rejected_bad_request,
    "routing to an unsupported recipient": pn_assert.assert_rejected_bad_request,
    "starting with a non-numeric amount": pn_assert.assert_rejected_bad_request,
    "signature without a ticket": pn_assert.assert_rejected_bad_request,
}
_SUCCESSES: dict[str, _CtxAction] = {
    "start succeeds": pn_assert.assert_success,
    "cancel completes successfully": pn_assert.assert_success,
    "start with an oversized description succeeds": pn_assert.assert_success,
    "notify request succeeds": pn_assert.assert_success,
}
_REFUND_REASONS: dict[str, _CtxAction] = {
    "for the note status": pn_assert.assert_refund_invalid_status,
    "because payment was not found": pn_assert.assert_refund_payment_not_found,
}
_PROTECTED: dict[str, _FlowAction] = {
    "routing": pn_assert.assert_injected_route_ignored,
    "starting": pn_assert.assert_injected_init_ignored,
}
_CONCURRENT_RESULTS: dict[str, _CtxAction] = {
    "a known business result": pn_assert.assert_concurrent_business_results,
    "note not found": pn_assert.assert_concurrent_not_found,
}
_KUKNOS_NOTE_STATES: dict[str, _FlowAction] = {
    "rejected": lambda flow, ctx: flow.setup_kuknos_rejected(ctx),
    "paid with renew turned off": lambda flow, ctx: flow.setup_kuknos_paid_renew_disabled(ctx),
}
_START_OUTCOMES: dict[str, _CtxAction] = {
    "is rejected for the note status": pn_assert.assert_start_invalid_note_status,
}
_RENEWAL_RESULTS: dict[str, _FlowAction] = {
    "not renewed": pn_assert.assert_note_not_renewed,
}


def known_promissory_pins() -> list[str]:
    """Registered routing-pin phrases, for the regex unit test to keep in sync."""
    return sorted(_PINS)


def known_promissory_route_modes() -> list[str]:
    """Registered route-mode phrases, for the regex unit test to keep in sync."""
    return sorted(_ROUTE_MODES)


def known_promissory_init_with_modes() -> list[str]:
    """Registered start-with phrases, for the regex unit test to keep in sync."""
    return sorted(_INIT_WITH_MODES)


def known_promissory_admin_actions() -> list[str]:
    """Registered admin-action phrases, for the regex unit test to keep in sync."""
    return sorted(_ADMIN_ACTIONS)


def known_promissory_concurrent_kinds() -> list[str]:
    """Registered concurrent-kind phrases, for the regex unit test to keep in sync."""
    return sorted(_CONCURRENT_KINDS)


def known_promissory_renew_states() -> list[str]:
    """Registered renew phrases, for the regex unit test to keep in sync."""
    return sorted(_RENEW)


def known_promissory_providers() -> list[str]:
    """Registered provider phrases, for the regex unit test to keep in sync."""
    return sorted(_PROVIDERS)


def known_promissory_bad_requests() -> list[str]:
    """Registered bad-request phrases, for the regex unit test to keep in sync."""
    return sorted(_BAD_REQUESTS)


def known_promissory_successes() -> list[str]:
    """Registered success phrases, for the regex unit test to keep in sync."""
    return sorted(_SUCCESSES)


def known_promissory_refund_reasons() -> list[str]:
    """Registered refund-reject phrases, for the regex unit test to keep in sync."""
    return sorted(_REFUND_REASONS)


def known_promissory_protected_actions() -> list[str]:
    """Registered protected-attribute phrases, for the regex unit test to keep in sync."""
    return sorted(_PROTECTED)


def known_promissory_concurrent_results() -> list[str]:
    """Registered concurrent-result phrases, for the regex unit test to keep in sync."""
    return sorted(_CONCURRENT_RESULTS)


def known_promissory_kuknos_note_states() -> list[str]:
    """Registered Kuknos-note setup phrases, for the regex unit test."""
    return sorted(_KUKNOS_NOTE_STATES)


def known_promissory_start_outcomes() -> list[str]:
    """Registered re-init outcome phrases, for the regex unit test."""
    return sorted(_START_OUTCOMES)


def known_promissory_renewal_results() -> list[str]:
    """Registered renew Mongo-result phrases, for the regex unit test."""
    return sorted(_RENEWAL_RESULTS)


def pin_promissory_routing(flow: PromissoryNoteFlow, pin: str) -> None:
    """Pin provider routing from the captured Gherkin pin phrase."""
    _require(_PINS, pin, "promissory routing pin")(flow)


def route_promissory_note(flow: PromissoryNoteFlow, ctx: PromissoryNoteContext, mode: str) -> None:
    """Run one route When from the captured Gherkin mode."""
    _require(_ROUTE_MODES, mode, "promissory route mode")(flow, ctx)


def start_promissory_note_with(
    flow: PromissoryNoteFlow, ctx: PromissoryNoteContext, mode: str
) -> None:
    """Run one start-with When from the captured Gherkin mode."""
    _require(_INIT_WITH_MODES, mode, "promissory start-with mode")(flow, ctx)


def run_promissory_admin_action(
    flow: PromissoryNoteFlow, ctx: PromissoryNoteContext, action: str
) -> None:
    """Run one administrator When from the captured Gherkin action."""
    _require(_ADMIN_ACTIONS, action, "promissory admin action")(flow, ctx)


def run_promissory_concurrent(
    flow: PromissoryNoteFlow, ctx: PromissoryNoteContext, kind: str
) -> None:
    """Run one concurrent When from the captured Gherkin kind."""
    _require(_CONCURRENT_KINDS, kind, "promissory concurrent kind")(flow, ctx)


def assert_promissory_renew(ctx: PromissoryNoteContext, availability: str) -> None:
    """Assert renew availability from the captured Gherkin phrase."""
    _require(_RENEW, availability, "promissory renew state")(ctx)


def assert_promissory_provider(
    flow: PromissoryNoteFlow, ctx: PromissoryNoteContext, provider: str
) -> None:
    """Assert the assigned provider from the captured Gherkin phrase."""
    _require(_PROVIDERS, provider, "promissory provider")(flow, ctx)


def assert_promissory_bad_request(ctx: PromissoryNoteContext, reason: str) -> None:
    """Assert a bad-request rejection from the captured Gherkin reason."""
    _require(_BAD_REQUESTS, reason, "promissory bad-request reason")(ctx)


def assert_promissory_success(ctx: PromissoryNoteContext, result: str) -> None:
    """Assert HTTP success from the captured Gherkin result phrase."""
    _require(_SUCCESSES, result, "promissory success result")(ctx)


def assert_promissory_refund_rejected(ctx: PromissoryNoteContext, reason: str) -> None:
    """Assert a refund rejection from the captured Gherkin reason."""
    _require(_REFUND_REASONS, reason, "promissory refund reason")(ctx)


def assert_promissory_protected(
    flow: PromissoryNoteFlow, ctx: PromissoryNoteContext, action: str
) -> None:
    """Assert injected attributes were ignored for routing or starting."""
    _require(_PROTECTED, action, "promissory protected action")(flow, ctx)


def assert_promissory_concurrent_result(ctx: PromissoryNoteContext, result: str) -> None:
    """Assert a concurrent-batch outcome from the captured Gherkin result."""
    _require(_CONCURRENT_RESULTS, result, "promissory concurrent result")(ctx)


def setup_kuknos_tejarat_note(
    flow: PromissoryNoteFlow, ctx: PromissoryNoteContext, state: str
) -> None:
    """Build a Kuknos Tejarat note from the captured Gherkin state."""
    _require(_KUKNOS_NOTE_STATES, state, "kuknos tejarat note state")(flow, ctx)


def assert_promissory_start_outcome(ctx: PromissoryNoteContext, outcome: str) -> None:
    """Assert a re-init HTTP outcome from the captured Gherkin phrase."""
    _require(_START_OUTCOMES, outcome, "promissory start outcome")(ctx)


def assert_promissory_renewal_result(
    flow: PromissoryNoteFlow, ctx: PromissoryNoteContext, renewal: str
) -> None:
    """Assert Mongo renew fields from the captured Gherkin phrase."""
    _require(_RENEWAL_RESULTS, renewal, "promissory renewal result")(flow, ctx)
