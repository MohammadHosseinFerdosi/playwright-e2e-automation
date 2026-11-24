"""Unit tests for ``parsers.re`` step patterns (no UAT).

Template required by ``.cursor/rules/step-patterns.mdc``: every ``parsers.re`` pattern
with an alternation or 2+ named groups is tested here — every wording variant used in
``.feature`` files, the captured group values, and at least one must-NOT-match
sentence. Editing a step regex then breaks a fast unit test, not a full BDD run.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tests.services.bill_inquiry_cases import (
    BILL_INIT_CASE_STEP,
    BILL_INQUIRY_CASE_STEP,
    known_bill_init_cases,
    known_bill_inquiry_cases,
)
from tests.services.dashboard_bill_ui import (
    ADMIN_SET_ELECTRICITY_WEIGHTS_STEP,
    BILL_DISTRIBUTION_OPEN_STEP,
    ELECTRICITY_ADMIN_WEIGHTS_STEP,
    INQUIRY_CONFIRM_STATE_STEP,
    INQUIRY_DISTRIBUTION_SHOWN_STEP,
    INQUIRY_PROVIDER_WEIGHT_IS_STEP,
    INQUIRY_PROVIDERS_SHOWN_STEP,
    INQUIRY_WEIGHTS_ARE_STEP,
    SET_FIRST_PROVIDER_WEIGHT_STEP,
    SET_INQUIRY_WEIGHTS_STEP,
    SET_PROVIDER_WEIGHT_STEP,
    known_bill_distribution_types,
)
from tests.services.dashboard_topup_ui import (
    MCI_ADMIN_WEIGHTS_STEP,
    OPEN_FROM_DASHBOARD_STEP,
    OPEN_OPERATOR_DISTRIBUTION_STEP,
    OPERATOR_CONFIRM_STATE_STEP,
    OPERATOR_DISTRIBUTION_SHOWN_STEP,
    OPERATOR_PICKER_LISTS_STEP,
    OPERATOR_PICKER_SHOWN_STEP,
    OPERATOR_PROVIDERS_SHOWN_STEP,
    OPERATOR_WEIGHTS_ARE_STEP,
    SET_OPERATOR_WEIGHTS_STEP,
    known_dashboard_tiles,
)
from tests.services.debit.bank_transfer import MELLAT_INVALID_ROUTE_STEP
from tests.services.debit.bank_transfer_ft_shahin_gherkin import (
    FT_SHAHIN_DIRECT_OUTCOME_STEP,
    FT_SHAHIN_DIRECT_WHEN_STEP,
    FT_SHAHIN_DSH_WHEN_STEP,
    FT_SHAHIN_INQUIRE_STEP,
    FT_SHAHIN_OUTCOME_STEP,
    FT_SHAHIN_REQUEST_STEP,
    FT_SHAHIN_ROUTE_STEP,
    FT_SHAHIN_TREASURY_GIVEN_STEP,
    known_ft_shahin_direct_modes,
    known_ft_shahin_direct_outcomes,
    known_ft_shahin_dsh_modes,
    known_ft_shahin_outcomes,
    known_ft_shahin_request_modes,
    known_ft_shahin_route_modes,
)
from tests.services.debit.debit_peers_gherkin import (
    PARSIAN_REQUEST_STEP,
    PEER_INQUIRE_STEP,
    PEER_LIVE_STEP,
    PEER_REJECTED_STEP,
    PEER_ROUTED_STEP,
    known_parsian_request_modes,
    known_peer_inquire_peers,
    known_peer_live_rails,
    known_peer_rejected_tails,
    known_peer_routed_tails,
)
from tests.services.debit.direct_route_gherkin import (
    MELLAT_DIRECT_OUTCOME_STEP,
    MELLAT_DIRECT_WHEN_STEP,
    MELLI_DIRECT_OUTCOME_STEP,
    MELLI_DIRECT_WHEN_STEP,
    known_mellat_direct_modes,
    known_mellat_direct_outcomes,
    known_melli_direct_modes,
    known_melli_direct_outcomes,
)
from tests.services.debit.duplicate_route_asserts import (
    DUPLICATE_ROUTE_STEP,
    known_route_kinds,
)
from tests.services.debit.manual_gherkin import (
    MANUAL_ACT_STEP,
    MANUAL_EXECUTE_STEP,
    MANUAL_INQUIRE_STEP,
    MANUAL_OUTCOME_STEP,
    MANUAL_REQUEST_STEP,
    MANUAL_STAFF_STEP,
    known_manual_act_modes,
    known_manual_execute_modes,
    known_manual_inquire_modes,
    known_manual_outcomes,
    known_manual_request_modes,
    known_manual_staff_modes,
)
from tests.services.debit.mellat_ach_gherkin import (
    MELLAT_ACH_OUTCOME_STEP,
    MELLAT_ACH_WHEN_STEP,
    known_mellat_ach_modes,
    known_mellat_ach_outcomes,
)
from tests.services.debit.mellat_dsh_gherkin import (
    MELLAT_DSH_ACT_STEP,
    MELLAT_DSH_OUTCOME_STEP,
    MELLAT_DSH_REQUEST_STEP,
    MELLAT_DSH_REQUESTS_STEP,
    MELLAT_DSH_STAFF_STEP,
    MELLAT_DSH_TRACKING_STEP,
    known_mellat_dsh_act_modes,
    known_mellat_dsh_outcomes,
    known_mellat_dsh_request_modes,
    known_mellat_dsh_requests_modes,
    known_mellat_dsh_staff_modes,
    known_mellat_dsh_tracking_modes,
)
from tests.services.debit.mellat_gateway_gherkin import (
    MELLAT_GATEWAY_WHEN_STEP,
    MELLAT_INTERNAL_ROUTE_STEP,
    known_mellat_gateway_modes,
    known_mellat_internal_route_outcomes,
)
from tests.services.debit.nemo_e2e_gherkin import (
    NEMO_E2E_OUTCOME_STEP,
    NEMO_E2E_REGISTER_STEP,
    known_nemo_e2e_outcomes,
    known_nemo_e2e_register_modes,
)
from tests.services.debit.nemo_gateway import NEMO_CASH_OUT_THROUGH_STEP
from tests.services.debit.nemo_gateway_gherkin import (
    NEMO_GATEWAY_APP_OUTCOME_STEP,
    NEMO_GATEWAY_APP_STEP,
    NEMO_GATEWAY_ASK_STEP,
    NEMO_GATEWAY_PREDICTED_STEP,
    known_nemo_gateway_app_modes,
    known_nemo_gateway_app_outcomes,
    known_nemo_gateway_ask_modes,
    known_nemo_gateway_predicted_outcomes,
)
from tests.services.debit.nemo_predict_gherkin import (
    NEMO_PREDICT_FEE_STEP,
    NEMO_PREDICT_OUTCOME_STEP,
    known_nemo_predict_modes,
    known_nemo_predict_outcomes,
)
from tests.services.debit.nemo_register_gherkin import (
    NEMO_REGISTER_OUTCOME_STEP,
    NEMO_REGISTER_STEP,
    known_nemo_register_modes,
    known_nemo_register_outcomes,
)
from tests.services.gl_incoming_transactions import (
    CREATE_TRANSACTION_STEP,
    LEDGER_TABLE_STEP,
    known_ledger_tables,
    known_transaction_types,
)
from tests.services.gl_merchants import (
    FILTER_WITH_RAHKARAN_STEP,
    FILTER_WITHOUT_RAHKARAN_STEP,
    FILTERED_CONTAIN_WITH_STEP,
    FILTERED_CONTAIN_WITHOUT_STEP,
    known_filter_fields,
    known_without_rahkaran_filter_fields,
)
from tests.services.kyc.digital_signature_gherkin import (
    DIGITAL_SIGNATURE_DSP_STEP,
    DIGITAL_SIGNATURE_INITIATE_STEP,
    DIGITAL_SIGNATURE_LIVENESS_PREP_STEP,
    DIGITAL_SIGNATURE_RESPONSE_STEP,
    DIGITAL_SIGNATURE_SETUP_STEP,
    DIGITAL_SIGNATURE_VALIDATE_STEP,
    known_digital_signature_dsp_records,
    known_digital_signature_initiate_modes,
    known_digital_signature_responses,
    known_digital_signature_setups,
    known_digital_signature_validate_modes,
)
from tests.services.kyc.postal_code_gherkin import (
    POSTAL_INQUIRE_STEP,
    POSTAL_INQUIRY_OUTCOME_STEP,
    POSTAL_INVALID_WEIGHTS_STEP,
    POSTAL_PROVIDER_PIN_STEP,
    POSTAL_SETTINGS_REJECTED_STEP,
    known_postal_inquire_modes,
    known_postal_inquiry_outcomes,
)
from tests.services.kyc.promissory_note import (
    known_promissory_init_details,
    known_promissory_stages,
)
from tests.services.kyc.promissory_note_gherkin import (
    PROMISSORY_ADMIN_STEP,
    PROMISSORY_BAD_REQUEST_STEP,
    PROMISSORY_CONCURRENT_RESULT_STEP,
    PROMISSORY_CONCURRENT_STEP,
    PROMISSORY_INIT_MISSING_REJECTED_STEP,
    PROMISSORY_INIT_MISSING_STEP,
    PROMISSORY_INIT_WITH_STEP,
    PROMISSORY_KUKNOS_NOTE_STEP,
    PROMISSORY_PIN_STEP,
    PROMISSORY_PROTECTED_STEP,
    PROMISSORY_PROVIDER_STEP,
    PROMISSORY_REFUND_REJECTED_STEP,
    PROMISSORY_RENEW_STEP,
    PROMISSORY_RENEWAL_RESULT_STEP,
    PROMISSORY_ROUTE_STEP,
    PROMISSORY_STAGE_STEP,
    PROMISSORY_START_OUTCOME_STEP,
    PROMISSORY_SUCCESS_STEP,
    known_promissory_admin_actions,
    known_promissory_bad_requests,
    known_promissory_concurrent_kinds,
    known_promissory_concurrent_results,
    known_promissory_init_with_modes,
    known_promissory_kuknos_note_states,
    known_promissory_pins,
    known_promissory_protected_actions,
    known_promissory_providers,
    known_promissory_refund_reasons,
    known_promissory_renew_states,
    known_promissory_renewal_results,
    known_promissory_route_modes,
    known_promissory_start_outcomes,
    known_promissory_successes,
)
from tests.services.kyc.registration_inquiry_gherkin import (
    REGISTRATION_INQUIRE_FAULT_STEP,
    REGISTRATION_INQUIRE_MODE_STEP,
    REGISTRATION_INQUIRY_REJECTED_STEP,
    REGISTRATION_INVALID_WEIGHTS_STEP,
    REGISTRATION_PROVIDER_PIN_STEP,
    REGISTRATION_SETTINGS_REJECTED_STEP,
    known_registration_inquire_modes,
)
from tests.services.kyc.shahkar_gherkin import (
    SHAHKAR_FAULT_STEP,
    SHAHKAR_IDENTITY_STEP,
    SHAHKAR_INQUIRE_STEP,
    SHAHKAR_INQUIRY_OUTCOME_STEP,
    known_shahkar_identities,
    known_shahkar_inquire_modes,
    known_shahkar_inquiry_outcomes,
)
from tests.services.landline_ui_asserts import (
    LANDLINE_OPEN_PERIOD_STEP,
    LANDLINE_PERIOD_STATE_STEP,
    OPEN_FROM_HUB_STEP,
    known_hub_features,
)
from tests.services.landline_validate import (
    LANDLINE_VALIDATE_CASE_STEP,
    TCI_REQUEST_STEP,
    TCI_TEL_STATUS_STEP,
    known_landline_validate_cases,
    known_tci_request_modes,
)
from tests.services.landline_validate_asserts import (
    LANDLINE_VALIDATE_THEN_STEP,
    TCI_INQUIRY_OUTCOME_STEP,
    known_landline_validate_outcomes,
    known_tci_inquiry_outcomes,
)
from tests.services.login_onboarding_actions import (
    LOGIN_PANEL_ACTION_STEP,
    known_login_panel_actions,
)
from tests.services.login_onboarding_asserts import (
    LOGIN_UI_STATE_STEP,
    known_login_ui_checks,
)
from tests.services.refund_inquiry_asserts import (
    REFUND_DESTINATION_TYPE_STEP,
    REFUND_LOOKUP_STEP,
    REFUND_RETURNED_ID_STEP,
    known_refund_destinations,
)
from tests.services.shared_step_patterns import (
    ADMIN_BILLS_CONFIG_REJECTED_STEP,
    BILL_INQUIRY_REJECTED_STEP,
    BILL_PAYMENT_INIT_REJECTED_STEP,
    CASH_OUT_GATEWAY_STEP,
    NEMO_CUSTOMER_CAPABILITY_STEP,
    TELEPHONE_POOL_CASE_STEP,
)
from tests.services.super_app.internet.internet_bundles_gherkin import (
    BUNDLE_CATALOG_OPERATOR_CELL_STEP,
)
from tests.services.transfer_service import (
    TRANSFER_CONDITION_STEP,
    TRANSFER_REJECTED_STEP,
    known_transfer_conditions,
)
from tests.services.wallet_balance import WALLET_MIX_STEP, known_wallet_mixes

# Every wording currently present in tests/bdd/features/debit/*.feature.
_DUPLICATE_ROUTE_WORDINGS = [
    ("duplicate ft shahin routes keep a single transfer row", "ft shahin"),
    ("duplicate manual routes keep a single transfer row", "manual"),
    ("duplicate Mellat routes keep a single transfer row", "Mellat"),
    ("duplicate Mellat dashboard routes keep a single transfer row", "Mellat dashboard"),
    ("the duplicate IBAN Mellat route keeps a single transfer row", "IBAN Mellat"),
]


@pytest.mark.parametrize(("text", "route_kind"), _DUPLICATE_ROUTE_WORDINGS)
def test_duplicate_route_step_matches(text: str, route_kind: str) -> None:
    match = re.fullmatch(DUPLICATE_ROUTE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("route_kind") == route_kind


@pytest.mark.parametrize(
    "text",
    [
        # no route kind at all — must not match with an empty capture
        "duplicate routes keep a single transfer row",
        # different behavior entirely
        "duplicate Mellat routes create two transfer rows",
        # missing the 'duplicate' family marker
        "Mellat routes keep a single transfer row",
    ],
)
def test_duplicate_route_step_rejects(text: str) -> None:
    assert re.fullmatch(DUPLICATE_ROUTE_STEP, text) is None


def test_every_dispatch_key_has_a_wording_test() -> None:
    """The dispatch table and the wording list can't drift apart."""
    tested_kinds = sorted({kind for _, kind in _DUPLICATE_ROUTE_WORDINGS})
    assert tested_kinds == known_route_kinds()


# Every wording currently present in tests/bdd/features/app/login_onboarding.feature.
_LOGIN_UI_WORDINGS = [
    ("the welcome copy is shown", "welcome copy", "shown"),
    ("the phone instruction is shown", "phone instruction", "shown"),
    ("the mobile number hint is shown", "mobile number hint", "shown"),
    ("the phone number is empty", "phone number", "empty"),
    ("accept and continue is shown", "accept and continue", "shown"),
    ("accept and continue is not clickable", "accept and continue", "not clickable"),
    ("accept and continue is clickable", "accept and continue", "clickable"),
    ("terms of use is available", "terms of use", "available"),
    ("the referral code link is available", "referral code link", "available"),
    ("the referral code link is not shown", "referral code link", "not shown"),
    ("the referral title is shown", "referral title", "shown"),
    ("the referral instruction is shown", "referral instruction", "shown"),
    ("the referral code preview is shown", "referral code preview", "shown"),
    ("the entered phone number is still shown", "entered phone number", "still shown"),
    ("the activation code sent copy is shown", "activation code sent copy", "shown"),
    ("the activation code boxes are shown", "activation code boxes", "shown"),
    ("confirm and continue is not clickable", "confirm and continue", "not clickable"),
    ("the resend timer is shown", "resend timer", "shown"),
    ("edit phone is available", "edit phone", "available"),
]


@pytest.mark.parametrize(("text", "element", "state"), _LOGIN_UI_WORDINGS)
def test_login_ui_state_step_matches(text: str, element: str, state: str) -> None:
    match = re.fullmatch(LOGIN_UI_STATE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("element") == element
    assert match.group("state") == state


@pytest.mark.parametrize(
    "text",
    [
        # a When action, not a state check
        "the customer enters a valid phone number",
        # unknown state word — must not silently bind
        "accept and continue is disabled",
        # missing is/are verb
        "the welcome copy shown",
    ],
)
def test_login_ui_state_step_rejects(text: str) -> None:
    assert re.fullmatch(LOGIN_UI_STATE_STEP, text) is None


def test_login_ui_state_step_binds_unknown_element() -> None:
    """Open element + known state binds; dispatch KeyErrors until the probe is added."""
    match = re.fullmatch(LOGIN_UI_STATE_STEP, "the toaster copy is shown")
    assert match is not None
    assert match.group("element") == "toaster copy"
    assert match.group("state") == "shown"


def test_login_ui_state_step_rejects_underscore_in_element() -> None:
    assert re.fullmatch(LOGIN_UI_STATE_STEP, "the welcome_copy is shown") is None


def test_every_login_ui_probe_has_a_wording_test() -> None:
    """The probe registry and the wording list can't drift apart."""
    tested_checks = sorted({(element, state) for _, element, state in _LOGIN_UI_WORDINGS})
    assert tested_checks == known_login_ui_checks()


# Every wording currently present in tests/bdd/features/app/login_onboarding.feature.
_LOGIN_PANEL_ACTION_WORDINGS = [
    ("the customer opens referral code", "opens", "referral code"),
    ("the customer opens terms of use", "opens", "terms of use"),
    ("the customer returns from referral code", "returns from", "referral code"),
    ("the customer returns from terms of use", "returns from", "terms of use"),
]


@pytest.mark.parametrize(("text", "action", "panel"), _LOGIN_PANEL_ACTION_WORDINGS)
def test_login_panel_action_step_matches(text: str, action: str, panel: str) -> None:
    match = re.fullmatch(LOGIN_PANEL_ACTION_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("action") == action
    assert match.group("panel") == panel


@pytest.mark.parametrize(
    "text",
    [
        # unknown panel — must not silently bind
        "the customer opens settings",
        # a Then state check, not an action
        "terms of use is available",
        # different actor
        "the staff opens referral code",
    ],
)
def test_login_panel_action_step_rejects(text: str) -> None:
    assert re.fullmatch(LOGIN_PANEL_ACTION_STEP, text) is None


def test_every_login_panel_action_has_a_wording_test() -> None:
    """The action registry and the wording list can't drift apart."""
    tested_actions = sorted({(action, panel) for _, action, panel in _LOGIN_PANEL_ACTION_WORDINGS})
    assert tested_actions == known_login_panel_actions()


# Every wording currently present in tests/bdd/features/dashboard/*.feature.
_BILL_DISTRIBUTION_WORDINGS = [
    ("the staff opens electricity inquiry distribution", "electricity"),
    ("the staff opens landline inquiry distribution", "landline"),
]


@pytest.mark.parametrize(("text", "bill_type"), _BILL_DISTRIBUTION_WORDINGS)
def test_bill_distribution_open_step_matches(text: str, bill_type: str) -> None:
    match = re.fullmatch(BILL_DISTRIBUTION_OPEN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("bill_type") == bill_type


@pytest.mark.parametrize(
    "text",
    [
        # unregistered bill type — must not silently bind
        "the staff opens gas inquiry distribution",
        # different surface entirely
        "the staff opens bill inquiry from the dashboard",
        # admin API step, not the UI action
        "the staff notes the current electricity admin inquiry distributions",
    ],
)
def test_bill_distribution_open_step_rejects(text: str) -> None:
    assert re.fullmatch(BILL_DISTRIBUTION_OPEN_STEP, text) is None


def test_every_bill_distribution_type_has_a_wording_test() -> None:
    """The opener registry and the wording list can't drift apart."""
    tested_types = sorted({bill_type for _, bill_type in _BILL_DISTRIBUTION_WORDINGS})
    assert tested_types == known_bill_distribution_types()


@pytest.mark.parametrize(
    ("text", "state"),
    [
        ("inquiry distribution confirm is enabled", "enabled"),
        ("inquiry distribution confirm is disabled", "disabled"),
    ],
)
def test_inquiry_confirm_state_step_matches(text: str, state: str) -> None:
    match = re.fullmatch(INQUIRY_CONFIRM_STATE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("state") == state


@pytest.mark.parametrize(
    "text",
    [
        # topup file's step — owned by dashboard_topup_steps, must not be stolen
        "operator distribution confirm is disabled",
        # unknown state word
        "inquiry distribution confirm is hidden",
    ],
)
def test_inquiry_confirm_state_step_rejects(text: str) -> None:
    assert re.fullmatch(INQUIRY_CONFIRM_STATE_STEP, text) is None


@pytest.mark.parametrize(
    ("text", "raw"),
    [
        ("the admin sets electricity inquiry weights to 20 and 80 via the admin API", "20 and 80"),
        ("the admin sets electricity inquiry weights to 0 and 100 via the admin API", "0 and 100"),
        (
            "the admin sets electricity inquiry weights to -100 and 200 via the admin API",
            "-100 and 200",
        ),
        (
            "the admin sets electricity inquiry weights to 101 and -1 via the admin API",
            "101 and -1",
        ),
    ],
)
def test_admin_set_electricity_weights_step_matches(text: str, raw: str) -> None:
    match = re.fullmatch(ADMIN_SET_ELECTRICITY_WEIGHTS_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("raw") == raw


def test_admin_set_electricity_weights_step_rejects() -> None:
    assert (
        re.fullmatch(
            ADMIN_SET_ELECTRICITY_WEIGHTS_STEP,
            "the staff sets inquiry weights to 10, 10 and 10",
        )
        is None
    )


def test_set_first_provider_weight_step_matches() -> None:
    match = re.fullmatch(
        SET_FIRST_PROVIDER_WEIGHT_STEP, "the staff sets the first provider weight to 0"
    )
    assert match is not None
    assert match.group("value") == "0"


def test_set_inquiry_weights_step_matches() -> None:
    match = re.fullmatch(
        SET_INQUIRY_WEIGHTS_STEP, "the staff sets inquiry weights to 10, 10 and 10"
    )
    assert match is not None
    assert match.group("raw") == "10, 10 and 10"


@pytest.mark.parametrize(
    ("text", "provider", "value"),
    [
        ("the staff sets the inquiry weight for finnotech to 30", "finnotech", "30"),
        ("the staff sets the inquiry weight for ghabzino to 70", "ghabzino", "70"),
    ],
)
def test_set_provider_weight_step_matches(text: str, provider: str, value: str) -> None:
    match = re.fullmatch(SET_PROVIDER_WEIGHT_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("provider") == provider
    assert match.group("value") == value


def test_set_provider_weight_does_not_steal_assert() -> None:
    assert re.fullmatch(SET_PROVIDER_WEIGHT_STEP, "the inquiry weight for finnotech is 25") is None
    assert (
        re.fullmatch(
            INQUIRY_PROVIDER_WEIGHT_IS_STEP,
            "the staff sets the inquiry weight for finnotech to 30",
        )
        is None
    )


def test_inquiry_distribution_shown_and_providers_match() -> None:
    shown = re.fullmatch(
        INQUIRY_DISTRIBUTION_SHOWN_STEP,
        "the inquiry distribution is shown for electricity inquiry",
    )
    providers = re.fullmatch(
        INQUIRY_PROVIDERS_SHOWN_STEP,
        "the inquiry distribution shows providers finnotech and ghabzino",
    )
    assert shown is not None and shown.group("bill_type") == "electricity inquiry"
    assert providers is not None
    assert providers.group("first", "second") == ("finnotech", "ghabzino")


def test_inquiry_weights_are_step_matches() -> None:
    match = re.fullmatch(INQUIRY_WEIGHTS_ARE_STEP, "the inquiry weights are 0 and 100")
    assert match is not None
    assert match.group("raw") == "0 and 100"


@pytest.mark.parametrize(
    ("text", "provider", "value"),
    [
        ("the inquiry weight for finnotech is 25", "finnotech", "25"),
        ("the inquiry weight for ghabzino is 75", "ghabzino", "75"),
        ("the inquiry weight for finnotech is 30", "finnotech", "30"),
    ],
)
def test_inquiry_provider_weight_is_step_matches(text: str, provider: str, value: str) -> None:
    match = re.fullmatch(INQUIRY_PROVIDER_WEIGHT_IS_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("provider") == provider
    assert match.group("value") == value


@pytest.mark.parametrize(
    ("text", "raw"),
    [
        ("the electricity admin inquiry weights are 30 and 70", "30 and 70"),
        ("the electricity admin inquiry weights are 25 and 75", "25 and 75"),
        ("the electricity admin inquiry weights are 20 and 80", "20 and 80"),
    ],
)
def test_electricity_admin_weights_step_matches(text: str, raw: str) -> None:
    match = re.fullmatch(ELECTRICITY_ADMIN_WEIGHTS_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("raw") == raw


def test_electricity_admin_weights_does_not_steal_ui_weights() -> None:
    assert re.fullmatch(ELECTRICITY_ADMIN_WEIGHTS_STEP, "the inquiry weights are 0 and 100") is None
    assert (
        re.fullmatch(
            INQUIRY_WEIGHTS_ARE_STEP,
            "the electricity admin inquiry weights are 30 and 70",
        )
        is None
    )


_REGISTRATION_PIN_WORDINGS = [
    ("the registration provider is hafezsaman for a full inquiry", "hafezsaman", "full"),
    ("the registration provider is jibit for a basic inquiry", "jibit", "basic"),
    ("the registration provider is jibit for a full inquiry", "jibit", "full"),
]


@pytest.mark.parametrize(("text", "provider", "kind"), _REGISTRATION_PIN_WORDINGS)
def test_registration_provider_pin_step_matches(text: str, provider: str, kind: str) -> None:
    match = re.fullmatch(REGISTRATION_PROVIDER_PIN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("provider") == provider
    assert match.group("kind") == kind


def test_registration_provider_pin_step_rejects() -> None:
    assert (
        re.fullmatch(
            REGISTRATION_PROVIDER_PIN_STEP,
            "the live registration provider weights are recorded",
        )
        is None
    )


_REGISTRATION_INQUIRE_MODE_WORDINGS = [
    (
        "the customer submits a full inquiry forcing a live lookup with strong validation",
        "full",
        "forcing a live lookup with strong validation",
    ),
    (
        "the customer submits a full inquiry with strong validation",
        "full",
        "with strong validation",
    ),
    ("the customer submits a full inquiry twice", "full", "twice"),
    (
        "the customer submits a full inquiry for a deceased person",
        "full",
        "for a deceased person",
    ),
    (
        "the customer submits a full inquiry for the alternate live person",
        "full",
        "for the alternate live person",
    ),
]


@pytest.mark.parametrize(("text", "kind", "mode"), _REGISTRATION_INQUIRE_MODE_WORDINGS)
def test_registration_inquire_mode_step_matches(text: str, kind: str, mode: str) -> None:
    match = re.fullmatch(REGISTRATION_INQUIRE_MODE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("kind") == kind
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "the customer submits a full inquiry using a malformed national code",
        "the customer submits a Shahkar inquiry with a missing national code",
        "the customer submits a basic inquiry",
    ],
)
def test_registration_inquire_mode_step_rejects(text: str) -> None:
    assert re.fullmatch(REGISTRATION_INQUIRE_MODE_STEP, text) is None


def test_every_registration_inquire_mode_has_a_wording_test() -> None:
    tested_modes = sorted({mode for _, _, mode in _REGISTRATION_INQUIRE_MODE_WORDINGS})
    assert tested_modes == known_registration_inquire_modes()


_REGISTRATION_FAULT_WORDINGS = [
    (
        "the customer submits a basic inquiry using a malformed national code",
        "basic",
        "a malformed national code",
    ),
    (
        "the customer submits a full inquiry using a malformed national code",
        "full",
        "a malformed national code",
    ),
    (
        "the customer submits a full inquiry using an unknown national code",
        "full",
        "an unknown national code",
    ),
    (
        "the customer submits a full inquiry using an unknown birth date",
        "full",
        "an unknown birth date",
    ),
]


@pytest.mark.parametrize(("text", "kind", "fault"), _REGISTRATION_FAULT_WORDINGS)
def test_registration_inquire_fault_step_matches(text: str, kind: str, fault: str) -> None:
    match = re.fullmatch(REGISTRATION_INQUIRE_FAULT_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("kind") == kind
    assert match.group("fault") == fault


def test_registration_inquire_fault_does_not_steal_mode() -> None:
    assert (
        re.fullmatch(
            REGISTRATION_INQUIRE_FAULT_STEP,
            "the customer submits a full inquiry with strong validation",
        )
        is None
    )


_REGISTRATION_WEIGHT_RULE_WORDINGS = [
    "staff submit invalid registration weights for a weight above one",
    "staff submit invalid registration weights for a weight below one",
    "staff submit invalid registration weights for a sum below one",
    "staff submit invalid registration weights for a sum above one",
    "staff submit invalid registration weights for all weights zero",
    "staff submit invalid registration weights for all providers inactive",
]


@pytest.mark.parametrize("text", _REGISTRATION_WEIGHT_RULE_WORDINGS)
def test_registration_invalid_weights_step_matches(text: str) -> None:
    match = re.fullmatch(REGISTRATION_INVALID_WEIGHTS_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("rule")


@pytest.mark.parametrize(
    ("text", "title"),
    [
        ("the registration inquiry is rejected as INVALID_PARAMETER", "INVALID_PARAMETER"),
        (
            "the registration inquiry is rejected as KYC_IDENTITY_NOT_FOUND",
            "KYC_IDENTITY_NOT_FOUND",
        ),
        (
            "the registration provider settings are rejected as INVALID_PARAMETER",
            "INVALID_PARAMETER",
        ),
        (
            "the registration provider settings are rejected as KYC_SETTING_VALIDATION_ERROR",
            "KYC_SETTING_VALIDATION_ERROR",
        ),
    ],
)
def test_registration_rejected_steps_match(text: str, title: str) -> None:
    inquiry = re.fullmatch(REGISTRATION_INQUIRY_REJECTED_STEP, text)
    settings = re.fullmatch(REGISTRATION_SETTINGS_REJECTED_STEP, text)
    matched = inquiry or settings
    assert matched is not None, f"pattern must match: {text!r}"
    assert matched.group("title") == title
    assert (inquiry is None) != (settings is None)


@pytest.mark.parametrize(
    ("text", "provider"),
    [
        ("the address provider is jibit", "jibit"),
        ("the address provider is sitaad", "sitaad"),
    ],
)
def test_postal_provider_pin_step_matches(text: str, provider: str) -> None:
    match = re.fullmatch(POSTAL_PROVIDER_PIN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("provider") == provider


@pytest.mark.parametrize(
    "text",
    [
        "the live address provider weights are recorded",
        "the registration provider is jibit for a full inquiry",
        "the address provider is enovin",
    ],
)
def test_postal_provider_pin_step_rejects(text: str) -> None:
    assert re.fullmatch(POSTAL_PROVIDER_PIN_STEP, text) is None


_POSTAL_INQUIRE_WORDINGS = [
    ("the customer inquires a valid postal code", "a valid postal code"),
    ("the customer inquires an unknown postal code", "an unknown postal code"),
    ("the customer inquires an invalid postal code", "an invalid postal code"),
    ("the customer inquires a valid postal code twice", "a valid postal code twice"),
]


@pytest.mark.parametrize(("text", "mode"), _POSTAL_INQUIRE_WORDINGS)
def test_postal_inquire_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(POSTAL_INQUIRE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "the customer inquires Shahkar",
        "the customer submits a full inquiry twice",
        "the customer inquires a valid postal code thrice",
        "staff submit invalid address provider weights for all weights zero",
    ],
)
def test_postal_inquire_step_rejects(text: str) -> None:
    assert re.fullmatch(POSTAL_INQUIRE_STEP, text) is None


def test_every_postal_inquire_mode_has_a_wording_test() -> None:
    tested_modes = sorted({mode for _, mode in _POSTAL_INQUIRE_WORDINGS})
    assert tested_modes == known_postal_inquire_modes()


_POSTAL_OUTCOME_WORDINGS = [
    ("the postal-code inquiry succeeds", "succeeds"),
    ("the postal-code inquiry is not found", "is not found"),
    ("the postal-code inquiry is rejected", "is rejected"),
]


@pytest.mark.parametrize(("text", "outcome"), _POSTAL_OUTCOME_WORDINGS)
def test_postal_inquiry_outcome_step_matches(text: str, outcome: str) -> None:
    match = re.fullmatch(POSTAL_INQUIRY_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


@pytest.mark.parametrize(
    "text",
    [
        "the registration inquiry is rejected as INVALID_PARAMETER",
        "the first postal-code journal was live and the latest was cached",
        "the Shahkar inquiry is rejected",
    ],
)
def test_postal_inquiry_outcome_step_rejects(text: str) -> None:
    assert re.fullmatch(POSTAL_INQUIRY_OUTCOME_STEP, text) is None


def test_every_postal_inquiry_outcome_has_a_wording_test() -> None:
    tested_outcomes = sorted({outcome for _, outcome in _POSTAL_OUTCOME_WORDINGS})
    assert tested_outcomes == known_postal_inquiry_outcomes()


_POSTAL_WEIGHT_RULE_WORDINGS = [
    "staff submit invalid address provider weights for a weight above one",
    "staff submit invalid address provider weights for a weight below one",
    "staff submit invalid address provider weights for a sum below one",
    "staff submit invalid address provider weights for a sum above one",
    "staff submit invalid address provider weights for all weights zero",
]


@pytest.mark.parametrize("text", _POSTAL_WEIGHT_RULE_WORDINGS)
def test_postal_invalid_weights_step_matches(text: str) -> None:
    match = re.fullmatch(POSTAL_INVALID_WEIGHTS_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("rule")


def test_postal_invalid_weights_does_not_steal_registration() -> None:
    assert (
        re.fullmatch(
            POSTAL_INVALID_WEIGHTS_STEP,
            "staff submit invalid registration weights for a weight above one",
        )
        is None
    )
    assert (
        re.fullmatch(
            REGISTRATION_INVALID_WEIGHTS_STEP,
            "staff submit invalid address provider weights for a weight above one",
        )
        is None
    )


@pytest.mark.parametrize(
    ("text", "title"),
    [
        ("the address provider settings are rejected as INVALID_PARAMETER", "INVALID_PARAMETER"),
        (
            "the address provider settings are rejected as KYC_SETTING_VALIDATION_ERROR",
            "KYC_SETTING_VALIDATION_ERROR",
        ),
    ],
)
def test_postal_settings_rejected_step_matches(text: str, title: str) -> None:
    match = re.fullmatch(POSTAL_SETTINGS_REJECTED_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("title") == title


def test_postal_settings_rejected_does_not_steal_registration() -> None:
    assert (
        re.fullmatch(
            POSTAL_SETTINGS_REJECTED_STEP,
            "the registration provider settings are rejected as INVALID_PARAMETER",
        )
        is None
    )
    assert (
        re.fullmatch(
            REGISTRATION_SETTINGS_REJECTED_STEP,
            "the address provider settings are rejected as INVALID_PARAMETER",
        )
        is None
    )


@pytest.mark.parametrize(
    ("text", "period"),
    [
        ("the customer opens the mid payment period", "mid"),
        ("the customer opens the final payment period", "final"),
    ],
)
def test_landline_open_period_step_matches(text: str, period: str) -> None:
    match = re.fullmatch(LANDLINE_OPEN_PERIOD_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("period") == period


@pytest.mark.parametrize(
    "text",
    [
        "the customer opens the app hub",
        "the customer opens landline bill inquiry from the hub",
        "the customer opens the yearly payment period",
    ],
)
def test_landline_open_period_step_rejects(text: str) -> None:
    assert re.fullmatch(LANDLINE_OPEN_PERIOD_STEP, text) is None


@pytest.mark.parametrize("feature", known_hub_features())
def test_open_from_hub_step_matches(feature: str) -> None:
    text = f"the customer opens {feature} from the hub"
    match = re.fullmatch(OPEN_FROM_HUB_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("feature") == feature


@pytest.mark.parametrize(
    "text",
    [
        "the customer opens the app hub",
        "the staff opens bill inquiry from the dashboard",
        "the customer opens the mid payment period",
        "the customer opens landline bill inquiry",
    ],
)
def test_open_from_hub_step_rejects(text: str) -> None:
    assert re.fullmatch(OPEN_FROM_HUB_STEP, text) is None


def test_open_from_hub_step_binds_unknown_tail() -> None:
    match = re.fullmatch(OPEN_FROM_HUB_STEP, "the customer opens top-up from the hub")
    assert match is not None
    assert match.group("feature") == "top-up"


@pytest.mark.parametrize(
    ("text", "term", "state"),
    [
        ("the mid period is payable", "mid", "payable"),
        ("the final period is payable", "final", "payable"),
        ("the final period is without debt", "final", "without debt"),
    ],
)
def test_landline_period_state_step_matches(text: str, term: str, state: str) -> None:
    match = re.fullmatch(LANDLINE_PERIOD_STATE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("term") == term
    assert match.group("state") == state


def test_landline_period_state_step_rejects() -> None:
    assert (
        re.fullmatch(LANDLINE_PERIOD_STATE_STEP, "the final payment period is not actionable")
        is None
    )
    assert re.fullmatch(LANDLINE_PERIOD_STATE_STEP, "the mid period is hidden") is None


_LANDLINE_VALIDATE_CASE_WORDINGS = [
    ("the customer validates a landline with missing type", "missing type"),
    ("the customer validates a landline with empty inquiry id", "empty inquiry id"),
    ("the customer validates a landline with short inquiry id", "short inquiry id"),
    ("the customer validates a landline with wrong type water", "wrong type water"),
]


@pytest.mark.parametrize(("text", "inquiry_case"), _LANDLINE_VALIDATE_CASE_WORDINGS)
def test_landline_validate_case_step_matches(text: str, inquiry_case: str) -> None:
    match = re.fullmatch(LANDLINE_VALIDATE_CASE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("inquiry_case") == inquiry_case


def test_landline_validate_case_step_rejects() -> None:
    assert (
        re.fullmatch(LANDLINE_VALIDATE_CASE_STEP, "the customer validates the pooled landline")
        is None
    )


def test_landline_validate_case_step_binds_unknown_tail() -> None:
    match = re.fullmatch(
        LANDLINE_VALIDATE_CASE_STEP, "the customer validates a landline with toasted"
    )
    assert match is not None
    assert match.group("inquiry_case") == "toasted"


def test_every_landline_validate_case_has_a_wording_test() -> None:
    tested = sorted({case for _, case in _LANDLINE_VALIDATE_CASE_WORDINGS})
    assert tested == known_landline_validate_cases()


_TCI_REQUEST_WORDINGS = [
    (
        "the operator requests a TCI mid inquiry for the pooled landline",
        "mid inquiry for the pooled landline",
    ),
    (
        "the operator requests a TCI final inquiry for the pooled landline",
        "final inquiry for the pooled landline",
    ),
    (
        "the operator requests a TCI final inquiry with invalid credentials",
        "final inquiry with invalid credentials",
    ),
    (
        "the operator requests a TCI final inquiry with a leading zero",
        "final inquiry with a leading zero",
    ),
]


@pytest.mark.parametrize(("text", "mode"), _TCI_REQUEST_WORDINGS)
def test_tci_request_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(TCI_REQUEST_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_tci_request_step_rejects() -> None:
    assert re.fullmatch(TCI_REQUEST_STEP, "the customer validates the pooled landline") is None


def test_tci_request_step_binds_unknown_tail() -> None:
    match = re.fullmatch(TCI_REQUEST_STEP, "the operator requests a TCI toasted")
    assert match is not None
    assert match.group("mode") == "toasted"


def test_every_tci_request_mode_has_a_wording_test() -> None:
    tested = sorted({mode for _, mode in _TCI_REQUEST_WORDINGS})
    assert tested == known_tci_request_modes()


@pytest.mark.parametrize(
    ("text", "tel_status"),
    [
        ("the TCI inquiry reports tel status 4", "4"),
        ("the TCI inquiry reports tel status 1", "1"),
    ],
)
def test_tci_tel_status_step_matches(text: str, tel_status: str) -> None:
    match = re.fullmatch(TCI_TEL_STATUS_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("tel_status") == tel_status


def test_tci_tel_status_step_rejects() -> None:
    assert (
        re.fullmatch(
            TCI_TEL_STATUS_STEP,
            "the TCI inquiry completes with a definitive tel status or province error",
        )
        is None
    )


_LANDLINE_VALIDATE_THEN_WORDINGS = [
    ("the landline validate succeeds", "succeeds"),
    (
        "the landline validate includes both mid and final terms",
        "includes both mid and final terms",
    ),
    ("the landline validate includes a payable mid term", "includes a payable mid term"),
    (
        "the landline validate does not include a payable final term",
        "does not include a payable final term",
    ),
    ("the landline validate completes without a payable bill", "completes without a payable bill"),
    (
        "the landline validate is rejected for a disallowed province",
        "is rejected for a disallowed province",
    ),
]


@pytest.mark.parametrize(("text", "outcome"), _LANDLINE_VALIDATE_THEN_WORDINGS)
def test_landline_validate_then_step_matches(text: str, outcome: str) -> None:
    match = re.fullmatch(LANDLINE_VALIDATE_THEN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


def test_landline_validate_then_step_rejects() -> None:
    assert (
        re.fullmatch(
            LANDLINE_VALIDATE_THEN_STEP,
            "every landline bill info is telephone with zero fee",
        )
        is None
    )


def test_landline_validate_then_step_binds_unknown_tail() -> None:
    match = re.fullmatch(LANDLINE_VALIDATE_THEN_STEP, "the landline validate is toasted")
    assert match is not None
    assert match.group("outcome") == "is toasted"


def test_every_landline_validate_outcome_has_a_wording_test() -> None:
    tested = sorted({outcome for _, outcome in _LANDLINE_VALIDATE_THEN_WORDINGS})
    assert tested == known_landline_validate_outcomes()


_TCI_INQUIRY_OUTCOME_WORDINGS = [
    ("the TCI inquiry fails authentication", "fails authentication"),
    (
        "the TCI inquiry reports that the province is not allowed",
        "reports that the province is not allowed",
    ),
    (
        "the TCI inquiry completes with a definitive tel status or province error",
        "completes with a definitive tel status or province error",
    ),
]


@pytest.mark.parametrize(("text", "outcome"), _TCI_INQUIRY_OUTCOME_WORDINGS)
def test_tci_inquiry_outcome_step_matches(text: str, outcome: str) -> None:
    match = re.fullmatch(TCI_INQUIRY_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


def test_tci_inquiry_outcome_step_rejects_tel_status() -> None:
    assert re.fullmatch(TCI_INQUIRY_OUTCOME_STEP, "the TCI inquiry reports tel status 4") is None


def test_tci_inquiry_outcome_step_binds_unknown_tail() -> None:
    match = re.fullmatch(TCI_INQUIRY_OUTCOME_STEP, "the TCI inquiry is toasted")
    assert match is not None
    assert match.group("outcome") == "is toasted"


def test_every_tci_inquiry_outcome_has_a_wording_test() -> None:
    tested = sorted({outcome for _, outcome in _TCI_INQUIRY_OUTCOME_WORDINGS})
    assert tested == known_tci_inquiry_outcomes()


_BILL_INQUIRY_CASE_WORDINGS = [
    ("the customer inquires a bill with short identifiers", "short identifiers"),
    ("the customer inquires a bill with long identifiers", "long identifiers"),
    ("the customer inquires a bill with empty pay id", "empty pay id"),
    ("the customer inquires a bill with broken checksum", "broken checksum"),
    ("the customer inquires a bill with type mismatch", "type mismatch"),
    ("the customer inquires a bill with amount too low", "amount too low"),
    ("the customer inquires a bill with inquiry id without type", "inquiry id without type"),
    ("the customer inquires a bill with invalid cell number", "invalid cell number"),
]


@pytest.mark.parametrize(("text", "bill_case"), _BILL_INQUIRY_CASE_WORDINGS)
def test_bill_inquiry_case_step_matches(text: str, bill_case: str) -> None:
    match = re.fullmatch(BILL_INQUIRY_CASE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("bill_case") == bill_case


def test_bill_inquiry_case_step_rejects() -> None:
    assert (
        re.fullmatch(BILL_INQUIRY_CASE_STEP, "the customer starts bill payment with empty pay id")
        is None
    )
    assert (
        re.fullmatch(BILL_INQUIRY_CASE_STEP, "the customer validates a landline with missing type")
        is None
    )


def test_bill_inquiry_case_step_binds_unknown_tail() -> None:
    match = re.fullmatch(BILL_INQUIRY_CASE_STEP, "the customer inquires a bill with toasted")
    assert match is not None
    assert match.group("bill_case") == "toasted"


def test_every_bill_inquiry_case_has_a_wording_test() -> None:
    tested = sorted({case for _, case in _BILL_INQUIRY_CASE_WORDINGS})
    assert tested == known_bill_inquiry_cases()


_BILL_INIT_CASE_WORDINGS = [
    ("the customer starts bill payment with empty pay id", "empty pay id"),
    ("the customer starts bill payment with amount too low", "amount too low"),
]


@pytest.mark.parametrize(("text", "init_case"), _BILL_INIT_CASE_WORDINGS)
def test_bill_init_case_step_matches(text: str, init_case: str) -> None:
    match = re.fullmatch(BILL_INIT_CASE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("init_case") == init_case


def test_bill_init_case_does_not_steal_inquiry() -> None:
    assert (
        re.fullmatch(BILL_INIT_CASE_STEP, "the customer inquires a bill with empty pay id") is None
    )


def test_every_bill_init_case_has_a_wording_test() -> None:
    tested = sorted({case for _, case in _BILL_INIT_CASE_WORDINGS})
    assert tested == known_bill_init_cases()


_REFUND_LOOKUP_WORDINGS = [
    (
        "the refund inquiry 7ecc14c8-336b-4bf1-a3d2-002a845aa194 is looked up by providerId",
        "7ecc14c8-336b-4bf1-a3d2-002a845aa194",
        "providerId",
    ),
    (
        "the refund inquiry 8191843271728811026725 is looked up by trackingCode",
        "8191843271728811026725",
        "trackingCode",
    ),
    (
        "the refund inquiry 11988051571593929197689 is looked up by trackingCode",
        "11988051571593929197689",
        "trackingCode",
    ),
    (
        "the refund inquiry 0705103639 is looked up by providerId",
        "0705103639",
        "providerId",
    ),
    (
        "the refund inquiry 1f8d08a1-3c12-4ece-a85c-5aa577575e655620f1d1c6 is looked up by providerId",
        "1f8d08a1-3c12-4ece-a85c-5aa577575e655620f1d1c6",
        "providerId",
    ),
    (
        "the refund inquiry 19532rgtr728881673090528677258 is looked up by trackingCode",
        "19532rgtr728881673090528677258",
        "trackingCode",
    ),
]


@pytest.mark.parametrize(("text", "inquiry_id", "id_type"), _REFUND_LOOKUP_WORDINGS)
def test_refund_lookup_step_matches(text: str, inquiry_id: str, id_type: str) -> None:
    match = re.fullmatch(REFUND_LOOKUP_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("inquiry_id") == inquiry_id
    assert match.group("id_type") == id_type


def test_refund_lookup_step_rejects() -> None:
    assert re.fullmatch(REFUND_LOOKUP_STEP, "the refund inquiry request succeeds") is None
    assert (
        re.fullmatch(
            REFUND_LOOKUP_STEP,
            "the returned providerId matches 7ecc14c8-336b-4bf1-a3d2-002a845aa194",
        )
        is None
    )
    assert (
        re.fullmatch(REFUND_LOOKUP_STEP, "the refund inquiry foo_bar is looked up by providerId")
        is None
    )


_REFUND_RETURNED_WORDINGS = [
    (
        "the returned providerId matches 7ecc14c8-336b-4bf1-a3d2-002a845aa194",
        "providerId",
        "7ecc14c8-336b-4bf1-a3d2-002a845aa194",
    ),
    (
        "the returned trackingCode matches 8191843271728811026725",
        "trackingCode",
        "8191843271728811026725",
    ),
    (
        "the returned trackingCode matches 11988051571593929197689",
        "trackingCode",
        "11988051571593929197689",
    ),
    ("the returned providerId matches 0705103639", "providerId", "0705103639"),
]


@pytest.mark.parametrize(("text", "id_type", "inquiry_id"), _REFUND_RETURNED_WORDINGS)
def test_refund_returned_id_step_matches(text: str, id_type: str, inquiry_id: str) -> None:
    match = re.fullmatch(REFUND_RETURNED_ID_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("id_type") == id_type
    assert match.group("inquiry_id") == inquiry_id


@pytest.mark.parametrize(
    ("text", "destination"),
    [
        ("the refund destination type is wallet", "wallet"),
        ("the refund destination type is iban", "iban"),
    ],
)
def test_refund_destination_type_step_matches(text: str, destination: str) -> None:
    match = re.fullmatch(REFUND_DESTINATION_TYPE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("destination") == destination


def test_refund_destination_type_step_rejects() -> None:
    assert (
        re.fullmatch(
            REFUND_DESTINATION_TYPE_STEP, "the refund inquiry request is rejected as invalid"
        )
        is None
    )
    assert re.fullmatch(REFUND_DESTINATION_TYPE_STEP, "the refund destination type is card") is None


def test_every_refund_destination_has_a_wording_test() -> None:
    tested = sorted({"wallet", "iban"})
    assert tested == known_refund_destinations()


_TRANSFER_CONDITION_WORDINGS = [
    ("the source customer attempts a transfer that is an invalid source", "an invalid source"),
    (
        "the source customer attempts a transfer that is an invalid destination",
        "an invalid destination",
    ),
    (
        "the source customer attempts a transfer that is under the minimum amount",
        "under the minimum amount",
    ),
    (
        "the source customer attempts a transfer that is over the maximum amount",
        "over the maximum amount",
    ),
    ("the source customer attempts a transfer that is an invalid amount", "an invalid amount"),
    (
        "the source customer attempts a transfer that is the same wallet as destination",
        "the same wallet as destination",
    ),
    (
        "the source customer attempts a transfer that is a non-cashoutable amount",
        "a non-cashoutable amount",
    ),
]


@pytest.mark.parametrize(("text", "condition"), _TRANSFER_CONDITION_WORDINGS)
def test_transfer_condition_step_matches(text: str, condition: str) -> None:
    match = re.fullmatch(TRANSFER_CONDITION_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("condition") == condition


def test_transfer_condition_step_rejects() -> None:
    assert (
        re.fullmatch(
            TRANSFER_CONDITION_STEP,
            "the source customer transfers a valid amount to the destination",
        )
        is None
    )


def test_transfer_condition_step_binds_unknown_tail() -> None:
    match = re.fullmatch(
        TRANSFER_CONDITION_STEP,
        "the source customer attempts a transfer that is toasted",
    )
    assert match is not None
    assert match.group("condition") == "toasted"


def test_every_transfer_condition_has_a_wording_test() -> None:
    tested = sorted({condition for _, condition in _TRANSFER_CONDITION_WORDINGS})
    assert tested == known_transfer_conditions()


@pytest.mark.parametrize(
    ("text", "expected_outcome"),
    [
        ("the transfer is rejected with incorrect member cell", "incorrect member cell"),
        ("the transfer is rejected with out of limit", "out of limit"),
        ("the transfer is rejected with insufficient balance", "insufficient balance"),
        ("the transfer is rejected with incorrect input data", "incorrect input data"),
        ("the transfer is rejected with same wallet", "same wallet"),
        ("the transfer is rejected with ticket rejection", "ticket rejection"),
    ],
)
def test_transfer_rejected_step_matches(text: str, expected_outcome: str) -> None:
    match = re.fullmatch(TRANSFER_REJECTED_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("expected_outcome") == expected_outcome


def test_transfer_rejected_step_binds_unknown_tail() -> None:
    match = re.fullmatch(TRANSFER_REJECTED_STEP, "the transfer is rejected with toasted")
    assert match is not None
    assert match.group("expected_outcome") == "toasted"


def test_transfer_rejected_step_rejects_wrong_stem() -> None:
    assert re.fullmatch(TRANSFER_REJECTED_STEP, "the ticket is rejected with out of limit") is None


_WALLET_MIX_WORDINGS = [
    ("a logged-in customer with default and time-bound wallets", "default and time-bound wallets"),
    ("a logged-in customer with only time-bound wallets", "only time-bound wallets"),
    (
        "a logged-in customer with only an expired time-bound wallet",
        "only an expired time-bound wallet",
    ),
    ("a logged-in customer with only a default wallet", "only a default wallet"),
    (
        "a logged-in customer with only a cashoutable default wallet",
        "only a cashoutable default wallet",
    ),
    (
        "a logged-in customer with only a non-cashoutable default wallet",
        "only a non-cashoutable default wallet",
    ),
]


@pytest.mark.parametrize(("text", "wallet_mix"), _WALLET_MIX_WORDINGS)
def test_wallet_mix_step_matches(text: str, wallet_mix: str) -> None:
    match = re.fullmatch(WALLET_MIX_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("wallet_mix") == wallet_mix


def test_wallet_mix_step_rejects() -> None:
    assert re.fullmatch(WALLET_MIX_STEP, "a logged-in customer without any wallet") is None
    assert re.fullmatch(WALLET_MIX_STEP, "a logged-in customer with only_a_default_wallet") is None


def test_wallet_mix_step_binds_unknown_tail() -> None:
    match = re.fullmatch(WALLET_MIX_STEP, "a logged-in customer with a toasted mix")
    assert match is not None
    assert match.group("wallet_mix") == "a toasted mix"


def test_every_wallet_mix_has_a_wording_test() -> None:
    tested = sorted({mix for _, mix in _WALLET_MIX_WORDINGS})
    assert tested == known_wallet_mixes()


_PROMISSORY_STAGE_WORDINGS = [
    ("an issued promissory note is at stage paid", "paid"),
    ("an issued promissory note is at stage signed", "signed"),
    ("an issued promissory note is at stage sealed", "sealed"),
    ("an issued promissory note is at stage confirmed", "confirmed"),
]


@pytest.mark.parametrize(("text", "stage"), _PROMISSORY_STAGE_WORDINGS)
def test_promissory_stage_step_matches(text: str, stage: str) -> None:
    match = re.fullmatch(PROMISSORY_STAGE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("stage") == stage


def test_promissory_stage_step_rejects() -> None:
    assert (
        re.fullmatch(
            PROMISSORY_STAGE_STEP, "an issued promissory note is marked paid without a payment"
        )
        is None
    )


def test_every_promissory_stage_has_a_wording_test() -> None:
    tested = sorted({stage for _, stage in _PROMISSORY_STAGE_WORDINGS})
    assert tested == known_promissory_stages()


_PROMISSORY_DETAIL_WORDINGS = [
    ("tracking code", "the customer starts a promissory note without tracking code"),
    ("owner", "the customer starts a promissory note without owner"),
    ("iban", "the customer starts a promissory note without iban"),
    ("amount", "the customer starts a promissory note without amount"),
]


@pytest.mark.parametrize(("detail", "text"), _PROMISSORY_DETAIL_WORDINGS)
def test_promissory_init_missing_step_matches(detail: str, text: str) -> None:
    match = re.fullmatch(PROMISSORY_INIT_MISSING_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("detail") == detail


def test_promissory_init_missing_step_rejects() -> None:
    assert (
        re.fullmatch(
            PROMISSORY_INIT_MISSING_STEP,
            "the customer starts a promissory note with a non-numeric amount",
        )
        is None
    )


def test_every_promissory_init_detail_has_a_wording_test() -> None:
    tested = sorted({detail for detail, _ in _PROMISSORY_DETAIL_WORDINGS})
    assert tested == known_promissory_init_details()


@pytest.mark.parametrize(
    ("text", "detail"),
    [
        ("starting without tracking code is rejected", "tracking code"),
        ("starting without owner is rejected", "owner"),
        ("starting without iban is rejected", "iban"),
        ("starting without amount is rejected", "amount"),
    ],
)
def test_promissory_init_missing_rejected_step_matches(text: str, detail: str) -> None:
    match = re.fullmatch(PROMISSORY_INIT_MISSING_REJECTED_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("detail") == detail


def test_promissory_init_missing_rejected_step_rejects() -> None:
    assert (
        re.fullmatch(
            PROMISSORY_INIT_MISSING_REJECTED_STEP,
            "routing without a requesting business is rejected",
        )
        is None
    )
    assert (
        re.fullmatch(
            PROMISSORY_INIT_MISSING_REJECTED_STEP,
            "starting with a non-numeric amount is rejected",
        )
        is None
    )


_PROMISSORY_PIN_WORDINGS = [
    ("routing is set to Saderat", "Saderat"),
    ("routing is set to Kuknos for Tejarat", "Kuknos for Tejarat"),
]


@pytest.mark.parametrize(("text", "pin"), _PROMISSORY_PIN_WORDINGS)
def test_promissory_pin_step_matches(text: str, pin: str) -> None:
    match = re.fullmatch(PROMISSORY_PIN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("pin") == pin


def test_promissory_pin_step_rejects() -> None:
    assert re.fullmatch(PROMISSORY_PIN_STEP, "promissory provider routing is configured") is None


def test_every_promissory_pin_has_a_wording_test() -> None:
    tested = sorted({pin for _, pin in _PROMISSORY_PIN_WORDINGS})
    assert tested == known_promissory_pins()


_PROMISSORY_ROUTE_WORDINGS = [
    ("the customer routes that note to Saderat", "to Saderat"),
    ("the customer routes that note to Tejarat", "to Tejarat"),
    (
        "the customer routes that note without a requesting business",
        "without a requesting business",
    ),
    (
        "the customer routes that note to an unsupported recipient",
        "to an unsupported recipient",
    ),
    (
        "the customer routes that note with protected attributes set by the client",
        "with protected attributes set by the client",
    ),
]


@pytest.mark.parametrize(("text", "mode"), _PROMISSORY_ROUTE_WORDINGS)
def test_promissory_route_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(PROMISSORY_ROUTE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_promissory_route_step_rejects() -> None:
    assert re.fullmatch(PROMISSORY_ROUTE_STEP, "the customer starts that promissory note") is None
    assert (
        re.fullmatch(PROMISSORY_ROUTE_STEP, "the customer seals that note without a sign reference")
        is None
    )


def test_every_promissory_route_mode_has_a_wording_test() -> None:
    tested = sorted({mode for _, mode in _PROMISSORY_ROUTE_WORDINGS})
    assert tested == known_promissory_route_modes()


_PROMISSORY_INIT_WITH_WORDINGS = [
    (
        "the customer starts a promissory note with a non-numeric amount",
        "a non-numeric amount",
    ),
    (
        "the customer starts a promissory note with an oversized description",
        "an oversized description",
    ),
    (
        "the customer starts a promissory note with protected attributes set by the client",
        "protected attributes set by the client",
    ),
]


@pytest.mark.parametrize(("text", "mode"), _PROMISSORY_INIT_WITH_WORDINGS)
def test_promissory_init_with_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(PROMISSORY_INIT_WITH_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "the customer starts that promissory note",
        "the customer starts a promissory note without amount",
        "the customer starts stamp payment for the note",
    ],
)
def test_promissory_init_with_step_rejects(text: str) -> None:
    assert re.fullmatch(PROMISSORY_INIT_WITH_STEP, text) is None


def test_every_promissory_init_with_mode_has_a_wording_test() -> None:
    tested = sorted({mode for _, mode in _PROMISSORY_INIT_WITH_WORDINGS})
    assert tested == known_promissory_init_with_modes()


_PROMISSORY_ADMIN_WORDINGS = [
    ("an administrator opens promissory provider settings", "opens promissory provider settings"),
    (
        "an administrator searches promissory settings recipients",
        "searches promissory settings recipients",
    ),
    ("an administrator opens promissory success rates", "opens promissory success rates"),
    (
        "an administrator searches promissory success-rate history",
        "searches promissory success-rate history",
    ),
]


@pytest.mark.parametrize(("text", "action"), _PROMISSORY_ADMIN_WORDINGS)
def test_promissory_admin_step_matches(text: str, action: str) -> None:
    match = re.fullmatch(PROMISSORY_ADMIN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("action") == action


@pytest.mark.parametrize(
    "text",
    [
        "an administrator cancels the promissory note",
        "an administrator reverts status for that unknown promissory note",
        "an administrator notifies a generated batch with that unknown code",
    ],
)
def test_promissory_admin_step_rejects(text: str) -> None:
    assert re.fullmatch(PROMISSORY_ADMIN_STEP, text) is None


def test_every_promissory_admin_action_has_a_wording_test() -> None:
    tested = sorted({action for _, action in _PROMISSORY_ADMIN_WORDINGS})
    assert tested == known_promissory_admin_actions()


_PROMISSORY_CONCURRENT_WORDINGS = [
    (
        "concurrent route requests are issued for that code",
        "route requests are issued for that code",
    ),
    ("concurrent admin cancel requests are issued", "admin cancel requests are issued"),
    ("concurrent inquiry requests are issued", "inquiry requests are issued"),
]


@pytest.mark.parametrize(("text", "kind"), _PROMISSORY_CONCURRENT_WORDINGS)
def test_promissory_concurrent_step_matches(text: str, kind: str) -> None:
    match = re.fullmatch(PROMISSORY_CONCURRENT_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("kind") == kind


def test_promissory_concurrent_step_rejects() -> None:
    assert (
        re.fullmatch(PROMISSORY_CONCURRENT_STEP, "the concurrent inquiries remain available")
        is None
    )


def test_every_promissory_concurrent_kind_has_a_wording_test() -> None:
    tested = sorted({kind for _, kind in _PROMISSORY_CONCURRENT_WORDINGS})
    assert tested == known_promissory_concurrent_kinds()


_PROMISSORY_RENEW_WORDINGS = [
    ("renew is available for that note", "available"),
    ("renew is not available for that note", "not available"),
]


@pytest.mark.parametrize(("text", "availability"), _PROMISSORY_RENEW_WORDINGS)
def test_promissory_renew_step_matches(text: str, availability: str) -> None:
    match = re.fullmatch(PROMISSORY_RENEW_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("availability") == availability


def test_promissory_renew_step_rejects() -> None:
    assert re.fullmatch(PROMISSORY_RENEW_STEP, "at least one cancel succeeds") is None


def test_every_promissory_renew_state_has_a_wording_test() -> None:
    tested = sorted({state for _, state in _PROMISSORY_RENEW_WORDINGS})
    assert tested == known_promissory_renew_states()


_PROMISSORY_PROVIDER_WORDINGS = [
    ("the note is assigned to the Saderat provider", "Saderat"),
    ("the note is assigned to the Kuknos provider", "Kuknos"),
]


@pytest.mark.parametrize(("text", "provider"), _PROMISSORY_PROVIDER_WORDINGS)
def test_promissory_provider_step_matches(text: str, provider: str) -> None:
    match = re.fullmatch(PROMISSORY_PROVIDER_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("provider") == provider


def test_promissory_provider_step_rejects() -> None:
    assert re.fullmatch(PROMISSORY_PROVIDER_STEP, "the promissory note is canceled") is None


def test_every_promissory_provider_has_a_wording_test() -> None:
    tested = sorted({provider for _, provider in _PROMISSORY_PROVIDER_WORDINGS})
    assert tested == known_promissory_providers()


_PROMISSORY_BAD_REQUEST_WORDINGS = [
    (
        "the promissory request routing without a requesting business is rejected",
        "routing without a requesting business",
    ),
    (
        "the promissory request routing to an unsupported recipient is rejected",
        "routing to an unsupported recipient",
    ),
    (
        "the promissory request starting with a non-numeric amount is rejected",
        "starting with a non-numeric amount",
    ),
    (
        "the promissory request signature without a ticket is rejected",
        "signature without a ticket",
    ),
]


@pytest.mark.parametrize(("text", "reason"), _PROMISSORY_BAD_REQUEST_WORDINGS)
def test_promissory_bad_request_step_matches(text: str, reason: str) -> None:
    match = re.fullmatch(PROMISSORY_BAD_REQUEST_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("reason") == reason


@pytest.mark.parametrize(
    "text",
    [
        "starting without tracking code is rejected",
        "the payment request is rejected",
        "the request is rejected as invalid",
        "the refund is rejected for the note status",
    ],
)
def test_promissory_bad_request_step_rejects(text: str) -> None:
    assert re.fullmatch(PROMISSORY_BAD_REQUEST_STEP, text) is None


def test_every_promissory_bad_request_has_a_wording_test() -> None:
    tested = sorted({reason for _, reason in _PROMISSORY_BAD_REQUEST_WORDINGS})
    assert tested == known_promissory_bad_requests()


_PROMISSORY_SUCCESS_WORDINGS = [
    ("the promissory action start succeeds", "start succeeds"),
    ("the promissory action cancel completes successfully", "cancel completes successfully"),
    (
        "the promissory action start with an oversized description succeeds",
        "start with an oversized description succeeds",
    ),
    ("the promissory action notify request succeeds", "notify request succeeds"),
]


@pytest.mark.parametrize(("text", "result"), _PROMISSORY_SUCCESS_WORDINGS)
def test_promissory_success_step_matches(text: str, result: str) -> None:
    match = re.fullmatch(PROMISSORY_SUCCESS_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("result") == result


def test_promissory_success_step_rejects() -> None:
    assert re.fullmatch(PROMISSORY_SUCCESS_STEP, "at least one cancel succeeds") is None
    assert re.fullmatch(PROMISSORY_SUCCESS_STEP, "the promissory note is canceled") is None


def test_every_promissory_success_has_a_wording_test() -> None:
    tested = sorted({result for _, result in _PROMISSORY_SUCCESS_WORDINGS})
    assert tested == known_promissory_successes()


_PROMISSORY_REFUND_WORDINGS = [
    ("the refund is rejected for the note status", "for the note status"),
    ("the refund is rejected because payment was not found", "because payment was not found"),
]


@pytest.mark.parametrize(("text", "reason"), _PROMISSORY_REFUND_WORDINGS)
def test_promissory_refund_rejected_step_matches(text: str, reason: str) -> None:
    match = re.fullmatch(PROMISSORY_REFUND_REJECTED_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("reason") == reason


def test_promissory_refund_rejected_step_rejects() -> None:
    assert re.fullmatch(PROMISSORY_REFUND_REJECTED_STEP, "the payment request is rejected") is None


def test_every_promissory_refund_reason_has_a_wording_test() -> None:
    tested = sorted({reason for _, reason in _PROMISSORY_REFUND_WORDINGS})
    assert tested == known_promissory_refund_reasons()


_PROMISSORY_PROTECTED_WORDINGS = [
    ("the note does not keep those protected attributes from routing", "routing"),
    ("the note does not keep those protected attributes from starting", "starting"),
]


@pytest.mark.parametrize(("text", "action"), _PROMISSORY_PROTECTED_WORDINGS)
def test_promissory_protected_step_matches(text: str, action: str) -> None:
    match = re.fullmatch(PROMISSORY_PROTECTED_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("action") == action


def test_promissory_protected_step_rejects() -> None:
    assert (
        re.fullmatch(
            PROMISSORY_PROTECTED_STEP,
            "exactly one promissory note exists for that tracking code",
        )
        is None
    )


def test_every_promissory_protected_action_has_a_wording_test() -> None:
    tested = sorted({action for _, action in _PROMISSORY_PROTECTED_WORDINGS})
    assert tested == known_promissory_protected_actions()


_PROMISSORY_CONCURRENT_RESULT_WORDINGS = [
    ("each concurrent response is a known business result", "a known business result"),
    ("each concurrent response is note not found", "note not found"),
]


@pytest.mark.parametrize(("text", "result"), _PROMISSORY_CONCURRENT_RESULT_WORDINGS)
def test_promissory_concurrent_result_step_matches(text: str, result: str) -> None:
    match = re.fullmatch(PROMISSORY_CONCURRENT_RESULT_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("result") == result


def test_promissory_concurrent_result_step_rejects() -> None:
    assert (
        re.fullmatch(PROMISSORY_CONCURRENT_RESULT_STEP, "the concurrent inquiries remain available")
        is None
    )
    assert (
        re.fullmatch(PROMISSORY_CONCURRENT_RESULT_STEP, "the promissory note is not found") is None
    )


def test_every_promissory_concurrent_result_has_a_wording_test() -> None:
    tested = sorted({result for _, result in _PROMISSORY_CONCURRENT_RESULT_WORDINGS})
    assert tested == known_promissory_concurrent_results()


_PROMISSORY_KUKNOS_NOTE_WORDINGS = [
    ("a Kuknos Tejarat note is rejected", "rejected"),
    ("a Kuknos Tejarat note is paid with renew turned off", "paid with renew turned off"),
]


@pytest.mark.parametrize(("text", "state"), _PROMISSORY_KUKNOS_NOTE_WORDINGS)
def test_promissory_kuknos_note_step_matches(text: str, state: str) -> None:
    match = re.fullmatch(PROMISSORY_KUKNOS_NOTE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("state") == state


def test_promissory_kuknos_note_step_rejects() -> None:
    assert re.fullmatch(PROMISSORY_KUKNOS_NOTE_STEP, "an issued promissory note exists") is None
    assert (
        re.fullmatch(PROMISSORY_KUKNOS_NOTE_STEP, "a Kuknos Tejarat note is paid_with_renew_off")
        is None
    )


def test_every_promissory_kuknos_note_state_has_a_wording_test() -> None:
    tested = sorted({state for _, state in _PROMISSORY_KUKNOS_NOTE_WORDINGS})
    assert tested == known_promissory_kuknos_note_states()


_PROMISSORY_START_OUTCOME_WORDINGS = [
    ("the promissory start is rejected for the note status", "is rejected for the note status"),
]


@pytest.mark.parametrize(("text", "outcome"), _PROMISSORY_START_OUTCOME_WORDINGS)
def test_promissory_start_outcome_step_matches(text: str, outcome: str) -> None:
    match = re.fullmatch(PROMISSORY_START_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


def test_promissory_start_outcome_step_rejects() -> None:
    assert (
        re.fullmatch(PROMISSORY_START_OUTCOME_STEP, "the promissory action start succeeds") is None
    )
    assert re.fullmatch(PROMISSORY_START_OUTCOME_STEP, "the promissory note is not found") is None


def test_every_promissory_start_outcome_has_a_wording_test() -> None:
    tested = sorted({outcome for _, outcome in _PROMISSORY_START_OUTCOME_WORDINGS})
    assert tested == known_promissory_start_outcomes()


_PROMISSORY_RENEWAL_RESULT_WORDINGS = [
    ("the promissory note was not renewed", "not renewed"),
]


@pytest.mark.parametrize(("text", "renewal"), _PROMISSORY_RENEWAL_RESULT_WORDINGS)
def test_promissory_renewal_result_step_matches(text: str, renewal: str) -> None:
    match = re.fullmatch(PROMISSORY_RENEWAL_RESULT_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("renewal") == renewal


def test_promissory_renewal_result_step_rejects() -> None:
    assert re.fullmatch(PROMISSORY_RENEWAL_RESULT_STEP, "the promissory note is canceled") is None
    assert re.fullmatch(PROMISSORY_RENEWAL_RESULT_STEP, "the promissory note is not found") is None
    assert re.fullmatch(PROMISSORY_RENEWAL_RESULT_STEP, "renew is available for that note") is None


def test_every_promissory_renewal_result_has_a_wording_test() -> None:
    tested = sorted({renewal for _, renewal in _PROMISSORY_RENEWAL_RESULT_WORDINGS})
    assert tested == known_promissory_renewal_results()


@pytest.mark.parametrize(
    ("text", "fault"),
    [
        (
            "the customer submits a Shahkar inquiry with a missing national code",
            "a missing national code",
        ),
        (
            "the customer submits a Shahkar inquiry with a missing cell number",
            "a missing cell number",
        ),
        (
            "the customer submits a Shahkar inquiry with an invalid national code",
            "an invalid national code",
        ),
        (
            "the customer submits a Shahkar inquiry with an invalid cell number",
            "an invalid cell number",
        ),
    ],
)
def test_shahkar_fault_step_matches(text: str, fault: str) -> None:
    match = re.fullmatch(SHAHKAR_FAULT_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("fault") == fault


def test_shahkar_fault_step_rejects() -> None:
    assert re.fullmatch(SHAHKAR_FAULT_STEP, "the customer inquires Shahkar") is None
    assert (
        re.fullmatch(
            SHAHKAR_FAULT_STEP,
            "the customer submits a full inquiry using a malformed national code",
        )
        is None
    )


_SHAHKAR_IDENTITY_WORDINGS = [
    ("the customer has a matching cell number", "a matching cell number"),
    (
        "the customer has a cell number that does not belong to them",
        "a cell number that does not belong to them",
    ),
    ("the customer has a national identity", "a national identity"),
]


@pytest.mark.parametrize(("text", "identity"), _SHAHKAR_IDENTITY_WORDINGS)
def test_shahkar_identity_step_matches(text: str, identity: str) -> None:
    match = re.fullmatch(SHAHKAR_IDENTITY_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("identity") == identity


@pytest.mark.parametrize(
    "text",
    [
        "the customer has completed native liveness",
        "the customer has only registered liveness for digital signature",
        "the customer has a new promissory tracking code",
    ],
)
def test_shahkar_identity_step_rejects(text: str) -> None:
    assert re.fullmatch(SHAHKAR_IDENTITY_STEP, text) is None


def test_every_shahkar_identity_has_a_wording_test() -> None:
    tested = sorted({identity for _, identity in _SHAHKAR_IDENTITY_WORDINGS})
    assert tested == known_shahkar_identities()


_SHAHKAR_INQUIRE_WORDINGS = [
    ("the customer inquires Shahkar", "Shahkar"),
    ("the customer inquires Shahkar twice", "Shahkar twice"),
]


@pytest.mark.parametrize(("text", "mode"), _SHAHKAR_INQUIRE_WORDINGS)
def test_shahkar_inquire_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(SHAHKAR_INQUIRE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "the customer inquires a valid postal code",
        "the customer submits a Shahkar inquiry with a missing national code",
        "the customer inquires Shahkar thrice",
    ],
)
def test_shahkar_inquire_step_rejects(text: str) -> None:
    assert re.fullmatch(SHAHKAR_INQUIRE_STEP, text) is None


def test_every_shahkar_inquire_mode_has_a_wording_test() -> None:
    tested = sorted({mode for _, mode in _SHAHKAR_INQUIRE_WORDINGS})
    assert tested == known_shahkar_inquire_modes()


_SHAHKAR_OUTCOME_WORDINGS = [
    ("the Shahkar inquiry is verified", "verified"),
    ("the Shahkar inquiry is unverified", "unverified"),
    ("the Shahkar inquiry is rejected", "rejected"),
]


@pytest.mark.parametrize(("text", "outcome"), _SHAHKAR_OUTCOME_WORDINGS)
def test_shahkar_inquiry_outcome_step_matches(text: str, outcome: str) -> None:
    match = re.fullmatch(SHAHKAR_INQUIRY_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


@pytest.mark.parametrize(
    "text",
    [
        "the first Shahkar journal was live and the latest was cached",
        "the postal-code inquiry is rejected",
        "the registration inquiry is rejected as INVALID_PARAMETER",
        "the Shahkar inquiry is rejected as INVALID_PARAMETER",
    ],
)
def test_shahkar_inquiry_outcome_step_rejects(text: str) -> None:
    assert re.fullmatch(SHAHKAR_INQUIRY_OUTCOME_STEP, text) is None


def test_every_shahkar_inquiry_outcome_has_a_wording_test() -> None:
    tested = sorted({outcome for _, outcome in _SHAHKAR_OUTCOME_WORDINGS})
    assert tested == known_shahkar_inquiry_outcomes()


@pytest.mark.parametrize(
    ("text", "liveness_prep"),
    [
        (
            "the customer has only registered liveness for digital signature",
            "only registered liveness",
        ),
        (
            "the customer has signature without selfie for digital signature",
            "signature without selfie",
        ),
        ("the customer has selfie without video for digital signature", "selfie without video"),
    ],
)
def test_digital_signature_liveness_prep_step_matches(text: str, liveness_prep: str) -> None:
    match = re.fullmatch(DIGITAL_SIGNATURE_LIVENESS_PREP_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("liveness_prep") == liveness_prep


def test_digital_signature_liveness_prep_step_rejects() -> None:
    assert (
        re.fullmatch(
            DIGITAL_SIGNATURE_LIVENESS_PREP_STEP, "the customer has completed native liveness"
        )
        is None
    )
    assert (
        re.fullmatch(
            DIGITAL_SIGNATURE_LIVENESS_PREP_STEP,
            "the customer has initiated a basic digital signature",
        )
        is None
    )


_DS_SETUP_WORDINGS = [
    ("the customer has initiated a basic digital signature", "initiated a basic digital signature"),
    ("the customer has a generated digital signature", "a generated digital signature"),
]


@pytest.mark.parametrize(("text", "setup"), _DS_SETUP_WORDINGS)
def test_digital_signature_setup_step_matches(text: str, setup: str) -> None:
    match = re.fullmatch(DIGITAL_SIGNATURE_SETUP_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("setup") == setup


@pytest.mark.parametrize(
    "text",
    [
        "the customer has completed native liveness",
        "the customer has only registered liveness for digital signature",
        "the customer has a matching cell number",
    ],
)
def test_digital_signature_setup_step_rejects(text: str) -> None:
    assert re.fullmatch(DIGITAL_SIGNATURE_SETUP_STEP, text) is None


def test_every_digital_signature_setup_has_a_wording_test() -> None:
    tested = sorted({setup for _, setup in _DS_SETUP_WORDINGS})
    assert tested == known_digital_signature_setups()


_DS_INITIATE_WORDINGS = [
    ("the customer initiates a basic digital signature", "a basic digital signature"),
    (
        "the customer initiates a basic digital signature without a password",
        "a basic digital signature without a password",
    ),
]


@pytest.mark.parametrize(("text", "mode"), _DS_INITIATE_WORDINGS)
def test_digital_signature_initiate_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(DIGITAL_SIGNATURE_INITIATE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "the customer generates the digital signature certificate",
        "the customer revokes the digital signature",
        "the customer has initiated a basic digital signature",
    ],
)
def test_digital_signature_initiate_step_rejects(text: str) -> None:
    assert re.fullmatch(DIGITAL_SIGNATURE_INITIATE_STEP, text) is None


def test_every_digital_signature_initiate_mode_has_a_wording_test() -> None:
    tested = sorted({mode for _, mode in _DS_INITIATE_WORDINGS})
    assert tested == known_digital_signature_initiate_modes()


_DS_VALIDATE_WORDINGS = [
    ("the customer validates the digital signature password", "the digital signature password"),
    (
        "the customer validates a wrong digital signature password",
        "a wrong digital signature password",
    ),
]


@pytest.mark.parametrize(("text", "mode"), _DS_VALIDATE_WORDINGS)
def test_digital_signature_validate_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(DIGITAL_SIGNATURE_VALIDATE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "the customer initiates a basic digital signature",
        "the validate password response succeeds",
        "the customer validates the digital signature",
    ],
)
def test_digital_signature_validate_step_rejects(text: str) -> None:
    assert re.fullmatch(DIGITAL_SIGNATURE_VALIDATE_STEP, text) is None


def test_every_digital_signature_validate_mode_has_a_wording_test() -> None:
    tested = sorted({mode for _, mode in _DS_VALIDATE_WORDINGS})
    assert tested == known_digital_signature_validate_modes()


_DS_RESPONSE_WORDINGS = [
    (
        "the digital signature initiate succeeds with a provider tracking code",
        "initiate succeeds with a provider tracking code",
    ),
    ("the digital signature generate succeeds", "generate succeeds"),
    ("the digital signature revoke succeeds", "revoke succeeds"),
    ("the digital signature validate password succeeds", "validate password succeeds"),
    (
        "the digital signature generate reports incomplete liveness",
        "generate reports incomplete liveness",
    ),
    ("the digital signature initiate reports a bad request", "initiate reports a bad request"),
    (
        "the digital signature validate password reports signature not found",
        "validate password reports signature not found",
    ),
    (
        "the digital signature validate password reports a password mismatch",
        "validate password reports a password mismatch",
    ),
]


@pytest.mark.parametrize(("text", "result"), _DS_RESPONSE_WORDINGS)
def test_digital_signature_response_step_matches(text: str, result: str) -> None:
    match = re.fullmatch(DIGITAL_SIGNATURE_RESPONSE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("result") == result


@pytest.mark.parametrize(
    "text",
    [
        "the provider signature record is pending for that provider tracking code",
        "the initiate response succeeds",
        "the Shahkar inquiry is rejected",
    ],
)
def test_digital_signature_response_step_rejects(text: str) -> None:
    assert re.fullmatch(DIGITAL_SIGNATURE_RESPONSE_STEP, text) is None


def test_every_digital_signature_response_has_a_wording_test() -> None:
    tested = sorted({result for _, result in _DS_RESPONSE_WORDINGS})
    assert tested == known_digital_signature_responses()


_DS_DSP_WORDINGS = [
    (
        "the provider signature record is pending for that provider tracking code",
        "pending for that provider tracking code",
    ),
    (
        "the provider signature record is initiated for that signature tracking code",
        "initiated for that signature tracking code",
    ),
    (
        "the provider signature record is revoked for that signature tracking code",
        "revoked for that signature tracking code",
    ),
]


@pytest.mark.parametrize(("text", "record"), _DS_DSP_WORDINGS)
def test_digital_signature_dsp_step_matches(text: str, record: str) -> None:
    match = re.fullmatch(DIGITAL_SIGNATURE_DSP_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("record") == record


@pytest.mark.parametrize(
    "text",
    [
        "the initiate response succeeds with a provider tracking code",
        "the promissory note is canceled",
    ],
)
def test_digital_signature_dsp_step_rejects(text: str) -> None:
    assert re.fullmatch(DIGITAL_SIGNATURE_DSP_STEP, text) is None


def test_every_digital_signature_dsp_record_has_a_wording_test() -> None:
    tested = sorted({record for _, record in _DS_DSP_WORDINGS})
    assert tested == known_digital_signature_dsp_records()


@pytest.mark.parametrize(
    ("text", "invalid_input"),
    [
        ("a customer routes a Mellat transfer with zero amount", "zero amount"),
        ("a customer routes a Mellat transfer with bad iban", "bad iban"),
        ("a customer routes a Mellat transfer with injection owner", "injection owner"),
        ("a customer routes a Mellat transfer with missing tracking", "missing tracking"),
    ],
)
def test_mellat_invalid_route_step_matches(text: str, invalid_input: str) -> None:
    match = re.fullmatch(MELLAT_INVALID_ROUTE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("invalid_input") == invalid_input


def test_mellat_invalid_route_step_rejects() -> None:
    assert (
        re.fullmatch(
            MELLAT_INVALID_ROUTE_STEP, "a customer routes the same Mellat tracking code twice"
        )
        is None
    )
    assert (
        re.fullmatch(
            MELLAT_INVALID_ROUTE_STEP, "a customer routes a marker-amount Mellat transfer only"
        )
        is None
    )


@pytest.mark.parametrize(
    ("text", "gateway"),
    [
        ("the Nemo app will cash out through Mellat", "Mellat"),
        ("the Nemo app will cash out through Shahin", "Shahin"),
        ("the Nemo app will cash out through Manual", "Manual"),
    ],
)
def test_nemo_cash_out_through_step_matches(text: str, gateway: str) -> None:
    match = re.fullmatch(NEMO_CASH_OUT_THROUGH_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("gateway") == gateway


def test_nemo_cash_out_through_does_not_steal_shared_gateway() -> None:
    assert re.fullmatch(NEMO_CASH_OUT_THROUGH_STEP, "cash-out goes through Mellat") is None
    assert re.fullmatch(CASH_OUT_GATEWAY_STEP, "the Nemo app will cash out through Mellat") is None


_NEMO_PREDICT_WORDINGS = [
    ("the customer predicts a cash-out fee for the configured card", "for the configured card"),
    ("the customer predicts a cash-out fee at the marker amount", "at the marker amount"),
    ("the customer predicts a cash-out fee at the minimum amount", "at the minimum amount"),
    ("the customer predicts a cash-out fee at the maximum amount", "at the maximum amount"),
    ("the customer predicts a cash-out fee for an unknown user", "for an unknown user"),
    (
        "the customer predicts a cash-out fee without a destination card",
        "without a destination card",
    ),
    ("the customer predicts a cash-out fee of zero", "of zero"),
    ("the customer predicts a cash-out fee with a negative amount", "with a negative amount"),
    ("the customer predicts a cash-out fee with an empty card number", "with an empty card number"),
    (
        "the customer predicts a cash-out fee with the card-number field omitted",
        "with the card-number field omitted",
    ),
    ("the customer predicts a cash-out fee with an invalid card type", "with an invalid card type"),
    ("the customer predicts a cash-out fee with a huge amount", "with a huge amount"),
]


@pytest.mark.parametrize(("text", "mode"), _NEMO_PREDICT_WORDINGS)
def test_nemo_predict_fee_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(NEMO_PREDICT_FEE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "DSH runs the cash-out fee secure-store diagnostic",
        "the customer registers an IBAN cash-out",
        "the customer predicts a cash-out fee",
    ],
)
def test_nemo_predict_fee_step_rejects(text: str) -> None:
    assert re.fullmatch(NEMO_PREDICT_FEE_STEP, text) is None


def test_every_nemo_predict_mode_has_a_wording_test() -> None:
    tested = sorted({mode for _, mode in _NEMO_PREDICT_WORDINGS})
    assert tested == known_nemo_predict_modes()


_NEMO_PREDICT_OUTCOME_WORDINGS = [
    ("the cash-out fee prediction succeeds", "succeeds"),
    ("the cash-out fee prediction is rejected", "is rejected"),
    ("the cash-out fee prediction is not an amount-range error", "is not an amount-range error"),
]


@pytest.mark.parametrize(("text", "outcome"), _NEMO_PREDICT_OUTCOME_WORDINGS)
def test_nemo_predict_outcome_step_matches(text: str, outcome: str) -> None:
    match = re.fullmatch(NEMO_PREDICT_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


@pytest.mark.parametrize(
    "text",
    [
        "the secure-store diagnostic is recorded",
        "the unknown-user fee prediction is rejected",
        "the cash-out register succeeds",
    ],
)
def test_nemo_predict_outcome_step_rejects(text: str) -> None:
    assert re.fullmatch(NEMO_PREDICT_OUTCOME_STEP, text) is None


def test_every_nemo_predict_outcome_has_a_wording_test() -> None:
    tested = sorted({outcome for _, outcome in _NEMO_PREDICT_OUTCOME_WORDINGS})
    assert tested == known_nemo_predict_outcomes()


_NEMO_REGISTER_WORDINGS = [
    ("the customer registers an IBAN cash-out", "an IBAN cash-out"),
    (
        "the customer registers an IBAN cash-out at the minimum amount",
        "an IBAN cash-out at the minimum amount",
    ),
    (
        "the customer registers an IBAN cash-out at the maximum amount",
        "an IBAN cash-out at the maximum amount",
    ),
    (
        "the customer registers an IBAN cash-out and waits for a terminal state",
        "an IBAN cash-out and waits for a terminal state",
    ),
    (
        "the customer registers an IBAN cash-out for an unknown user",
        "an IBAN cash-out for an unknown user",
    ),
    ("the customer registers a cash-out to an invalid IBAN", "a cash-out to an invalid IBAN"),
    (
        "the customer registers a cash-out to an IBAN with spaces",
        "a cash-out to an IBAN with spaces",
    ),
    ("the customer registers a cash-out without an IBAN", "a cash-out without an IBAN"),
    ("the customer registers a cash-out without a birth date", "a cash-out without a birth date"),
    (
        "the customer registers a cash-out with an invalid birth date",
        "a cash-out with an invalid birth date",
    ),
    (
        "the customer registers a cash-out below the minimum amount",
        "a cash-out below the minimum amount",
    ),
    (
        "the customer registers a cash-out above the maximum amount",
        "a cash-out above the maximum amount",
    ),
]


@pytest.mark.parametrize(("text", "mode"), _NEMO_REGISTER_WORDINGS)
def test_nemo_register_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(NEMO_REGISTER_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "the customer asks for cash-out detail with an unknown tracking code",
        "the customer registers an IBAN cash-out onto the manual portal",
        "the customer registers an IBAN cash-out onto Mellat",
        "the customer registers an IBAN cash-out onto Mellat and waits",
        "the customer registers a crisis-path cash-out on the manual portal",
        "an unknown user registers an IBAN cash-out",
        "the customer predicts a cash-out fee for the configured card",
    ],
)
def test_nemo_register_step_rejects(text: str) -> None:
    assert re.fullmatch(NEMO_REGISTER_STEP, text) is None


def test_nemo_register_step_binds_unknown_tail() -> None:
    match = re.fullmatch(
        NEMO_REGISTER_STEP, "the customer registers an IBAN cash-out for a toasted user"
    )
    assert match is not None
    assert match.group("mode") == "an IBAN cash-out for a toasted user"


def test_nemo_register_step_forbids_dot_star() -> None:
    assert ".*" not in NEMO_REGISTER_STEP
    assert ".+" not in NEMO_REGISTER_STEP


def test_every_nemo_register_mode_has_a_wording_test() -> None:
    tested = sorted({mode for _, mode in _NEMO_REGISTER_WORDINGS})
    assert tested == known_nemo_register_modes()


_NEMO_REGISTER_OUTCOME_WORDINGS = [
    ("the Nemo cash-out register succeeds", "register succeeds"),
    ("the Nemo cash-out register reaches a terminal state", "register reaches a terminal state"),
    ("the Nemo cash-out register is rejected", "register is rejected"),
    ("the Nemo cash-out detail is rejected", "detail is rejected"),
]


@pytest.mark.parametrize(("text", "outcome"), _NEMO_REGISTER_OUTCOME_WORDINGS)
def test_nemo_register_outcome_step_matches(text: str, outcome: str) -> None:
    match = re.fullmatch(NEMO_REGISTER_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


@pytest.mark.parametrize(
    "text",
    [
        "the cash-out fee prediction succeeds",
        "the Mellat cash-out reaches a terminal state",
        "the cash-out is registered and detail succeeds",
        "unknown cash-out detail is rejected",
    ],
)
def test_nemo_register_outcome_step_rejects(text: str) -> None:
    assert re.fullmatch(NEMO_REGISTER_OUTCOME_STEP, text) is None


def test_every_nemo_register_outcome_has_a_wording_test() -> None:
    tested = sorted({outcome for _, outcome in _NEMO_REGISTER_OUTCOME_WORDINGS})
    assert tested == known_nemo_register_outcomes()


_MELLI_DIRECT_WHEN_WORDINGS = [
    ("treasury requests a Melli ACH direct payout", "requests a Melli ACH direct payout"),
    (
        "treasury requests a zero-amount Melli ACH direct payout",
        "requests a zero-amount Melli ACH direct payout",
    ),
    (
        "treasury requests a Melli ACH direct payout from an invalid source",
        "requests a Melli ACH direct payout from an invalid source",
    ),
    (
        "treasury requests a Melli ACH direct payout from a non-Melli source",
        "requests a Melli ACH direct payout from a non-Melli source",
    ),
    (
        "treasury requests a Melli ACH direct payout to the same bank",
        "requests a Melli ACH direct payout to the same bank",
    ),
    ("treasury reuses a Melli ACH tracking code", "reuses a Melli ACH tracking code"),
    (
        "treasury requests a Melli ACH direct payout with the client inactive",
        "requests a Melli ACH direct payout with the client inactive",
    ),
    (
        "treasury requests a Melli payout with the wrong agenda",
        "requests a Melli payout with the wrong agenda",
    ),
    (
        "treasury requests a Melli ACH direct payout without a source account",
        "requests a Melli ACH direct payout without a source account",
    ),
    (
        "treasury waits for a Melli ACH direct payout to settle",
        "waits for a Melli ACH direct payout to settle",
    ),
]


@pytest.mark.parametrize(("text", "mode"), _MELLI_DIRECT_WHEN_WORDINGS)
def test_melli_direct_when_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(MELLI_DIRECT_WHEN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "treasury requests a Mellat ACH direct payout",
        "treasury requests a Mellat ACH direct payout from a non-Mellat source",
        "a customer routes a Mellat transfer with zero amount",
    ],
)
def test_melli_direct_when_step_rejects(text: str) -> None:
    assert re.fullmatch(MELLI_DIRECT_WHEN_STEP, text) is None


def test_every_melli_direct_mode_has_a_wording_test() -> None:
    tested = sorted({mode for _, mode in _MELLI_DIRECT_WHEN_WORDINGS})
    assert tested == known_melli_direct_modes()


_MELLAT_DIRECT_WHEN_WORDINGS = [
    ("treasury requests a Mellat ACH direct payout", "requests a Mellat ACH direct payout"),
    (
        "treasury requests a zero-amount Mellat ACH direct payout",
        "requests a zero-amount Mellat ACH direct payout",
    ),
    (
        "treasury requests a Mellat ACH direct payout from an invalid source",
        "requests a Mellat ACH direct payout from an invalid source",
    ),
    (
        "treasury requests a Mellat ACH direct payout without a source account",
        "requests a Mellat ACH direct payout without a source account",
    ),
    (
        "treasury requests a Mellat ACH direct payout to the same bank",
        "requests a Mellat ACH direct payout to the same bank",
    ),
    (
        "treasury requests a Mellat ACH direct payout from a non-Mellat source",
        "requests a Mellat ACH direct payout from a non-Mellat source",
    ),
    ("treasury reuses a Mellat ACH tracking code", "reuses a Mellat ACH tracking code"),
    (
        "treasury requests a Mellat ACH direct payout with the wrong client ids",
        "requests a Mellat ACH direct payout with the wrong client ids",
    ),
    (
        "treasury waits for a Mellat ACH direct payout to settle",
        "waits for a Mellat ACH direct payout to settle",
    ),
]


@pytest.mark.parametrize(("text", "mode"), _MELLAT_DIRECT_WHEN_WORDINGS)
def test_mellat_direct_when_step_matches(text: str, mode: str) -> None:
    match = re.fullmatch(MELLAT_DIRECT_WHEN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_mellat_direct_when_step_rejects() -> None:
    assert (
        re.fullmatch(MELLAT_DIRECT_WHEN_STEP, "treasury requests a Melli ACH direct payout") is None
    )


def test_every_mellat_direct_mode_has_a_wording_test() -> None:
    tested = sorted({mode for _, mode in _MELLAT_DIRECT_WHEN_WORDINGS})
    assert tested == known_mellat_direct_modes()


_MELLI_DIRECT_OUTCOME_WORDINGS = [
    ("the Melli payout settles on inquiry", "settles on inquiry"),
    ("the Melli payout is rejected", "is rejected"),
    (
        "the Melli payout does not attach from a non-Melli source",
        "does not attach from a non-Melli source",
    ),
    (
        "the Melli payout stays off PAYA for a same-bank destination",
        "stays off PAYA for a same-bank destination",
    ),
    (
        "the Melli payout keeps a single ledger row on duplicate",
        "keeps a single ledger row on duplicate",
    ),
    (
        "the Melli payout is not the treasury path for a wrong agenda",
        "is not the treasury path for a wrong agenda",
    ),
    ("the Melli payout eventually settles", "eventually settles"),
]


@pytest.mark.parametrize(("text", "outcome"), _MELLI_DIRECT_OUTCOME_WORDINGS)
def test_melli_direct_outcome_step_matches(text: str, outcome: str) -> None:
    match = re.fullmatch(MELLI_DIRECT_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


def test_melli_direct_outcome_does_not_steal_duplicate_route() -> None:
    text = "the Melli payout keeps a single ledger row on duplicate"
    assert re.fullmatch(MELLI_DIRECT_OUTCOME_STEP, text) is not None
    assert re.fullmatch(DUPLICATE_ROUTE_STEP, text) is None


def test_every_melli_direct_outcome_has_a_wording_test() -> None:
    tested = sorted({outcome for _, outcome in _MELLI_DIRECT_OUTCOME_WORDINGS})
    assert tested == known_melli_direct_outcomes()


_MELLAT_DIRECT_OUTCOME_WORDINGS = [
    ("the Mellat payout settles on inquiry", "settles on inquiry"),
    ("the Mellat payout is rejected", "is rejected"),
    (
        "the Mellat payout stays off PAYA for a same-bank destination",
        "stays off PAYA for a same-bank destination",
    ),
    (
        "the Mellat payout does not attach from a non-Mellat source",
        "does not attach from a non-Mellat source",
    ),
    (
        "the Mellat payout keeps a single ledger row on duplicate",
        "keeps a single ledger row on duplicate",
    ),
    ("the Mellat payout eventually settles", "eventually settles"),
]


@pytest.mark.parametrize(("text", "outcome"), _MELLAT_DIRECT_OUTCOME_WORDINGS)
def test_mellat_direct_outcome_step_matches(text: str, outcome: str) -> None:
    match = re.fullmatch(MELLAT_DIRECT_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


def test_mellat_direct_outcome_step_rejects() -> None:
    assert re.fullmatch(MELLAT_DIRECT_OUTCOME_STEP, "the Melli payout is rejected") is None


def test_every_mellat_direct_outcome_has_a_wording_test() -> None:
    tested = sorted({outcome for _, outcome in _MELLAT_DIRECT_OUTCOME_WORDINGS})
    assert tested == known_mellat_direct_outcomes()


@pytest.mark.parametrize("mode", known_mellat_dsh_request_modes())
def test_mellat_dsh_request_step_matches(mode: str) -> None:
    text = f"the customer requests a Mellat cash-out {mode}"
    match = re.fullmatch(MELLAT_DSH_REQUEST_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "the customer requests a Mellat IBAN cash-out",
        "the customer requests a Mellat SATNA cash-out",
        "the customer requests Mellat cash-outs to IBANs from other banks",
        "the customer requests a Mellat cash-out",
    ],
)
def test_mellat_dsh_request_step_rejects(text: str) -> None:
    assert re.fullmatch(MELLAT_DSH_REQUEST_STEP, text) is None


@pytest.mark.parametrize("mode", known_mellat_dsh_requests_modes())
def test_mellat_dsh_requests_step_matches(mode: str) -> None:
    text = f"the customer requests Mellat cash-outs {mode}"
    match = re.fullmatch(MELLAT_DSH_REQUESTS_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize("mode", known_mellat_dsh_tracking_modes())
def test_mellat_dsh_tracking_step_matches(mode: str) -> None:
    text = f"the customer {mode}"
    match = re.fullmatch(MELLAT_DSH_TRACKING_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_mellat_dsh_tracking_does_not_steal_gateway_duplicate() -> None:
    assert (
        re.fullmatch(
            MELLAT_DSH_TRACKING_STEP, "a customer routes the same Mellat tracking code twice"
        )
        is None
    )


@pytest.mark.parametrize("mode", known_mellat_dsh_act_modes())
def test_mellat_dsh_act_step_matches(mode: str) -> None:
    text = f"the customer {mode}"
    match = re.fullmatch(MELLAT_DSH_ACT_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_mellat_dsh_act_does_not_steal_request() -> None:
    assert (
        re.fullmatch(MELLAT_DSH_ACT_STEP, "the customer requests a Mellat cash-out without an IBAN")
        is None
    )


@pytest.mark.parametrize("mode", known_mellat_dsh_staff_modes())
def test_mellat_dsh_staff_step_matches(mode: str) -> None:
    text = f"DSH {mode}"
    match = re.fullmatch(MELLAT_DSH_STAFF_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_mellat_dsh_staff_does_not_steal_split_weights() -> None:
    assert (
        re.fullmatch(
            MELLAT_DSH_STAFF_STEP,
            "DSH splits cash-out weights evenly between Manual and Mellat",
        )
        is None
    )
    assert (
        re.fullmatch(
            MELLAT_DSH_STAFF_STEP,
            "DSH splits Nemo cash-out weights evenly between Manual and Mellat",
        )
        is None
    )


@pytest.mark.parametrize("outcome", known_mellat_dsh_outcomes())
def test_mellat_dsh_outcome_step_matches(outcome: str) -> None:
    text = f"the Mellat cash-out {outcome}"
    match = re.fullmatch(MELLAT_DSH_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


@pytest.mark.parametrize(
    "text",
    [
        "duplicate Mellat dashboard routes keep a single transfer row",
        "the Mellat call does not return a server error",
        "the cash-out appears on the Shahin provider statement",
        "the registered cash-out reaches a terminal Mellat state",
    ],
)
def test_mellat_dsh_outcome_step_rejects(text: str) -> None:
    assert re.fullmatch(MELLAT_DSH_OUTCOME_STEP, text) is None


@pytest.mark.parametrize("mode", known_manual_request_modes())
def test_manual_request_step_matches(mode: str) -> None:
    text = f"the customer requests {mode}"
    match = re.fullmatch(MANUAL_REQUEST_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_manual_request_does_not_steal_nemo_e2e() -> None:
    assert (
        re.fullmatch(
            MANUAL_REQUEST_STEP, "the customer registers an IBAN cash-out onto the manual portal"
        )
        is None
    )


@pytest.mark.parametrize("mode", known_manual_execute_modes())
def test_manual_execute_step_matches(mode: str) -> None:
    text = f"the customer executes {mode}"
    match = re.fullmatch(MANUAL_EXECUTE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize("mode", known_manual_inquire_modes())
def test_manual_inquire_step_matches(mode: str) -> None:
    text = f"the customer inquires {mode}"
    match = re.fullmatch(MANUAL_INQUIRE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize("mode", known_manual_act_modes())
def test_manual_act_step_matches(mode: str) -> None:
    text = f"the customer {mode}"
    match = re.fullmatch(MANUAL_ACT_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_manual_act_does_not_steal_request_execute_inquire() -> None:
    assert re.fullmatch(MANUAL_ACT_STEP, "the customer requests a manual portal cash-out") is None
    assert (
        re.fullmatch(
            MANUAL_ACT_STEP, "the customer executes a manual portal cash-out that stays in progress"
        )
        is None
    )
    assert (
        re.fullmatch(MANUAL_ACT_STEP, "the customer inquires an in-progress manual cash-out")
        is None
    )


@pytest.mark.parametrize("mode", known_manual_staff_modes())
def test_manual_staff_step_matches(mode: str) -> None:
    text = f"DSH {mode}"
    match = re.fullmatch(MANUAL_STAFF_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_manual_staff_does_not_steal_split_weights() -> None:
    assert (
        re.fullmatch(
            MANUAL_STAFF_STEP,
            "DSH splits cash-out weights evenly between Manual and Mellat",
        )
        is None
    )
    assert (
        re.fullmatch(
            MANUAL_STAFF_STEP,
            "DSH splits Nemo cash-out weights evenly between Manual and Mellat",
        )
        is None
    )


@pytest.mark.parametrize("outcome", known_manual_outcomes())
def test_manual_outcome_step_matches(outcome: str) -> None:
    text = f"the manual cash-out {outcome}"
    match = re.fullmatch(MANUAL_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


def test_manual_outcome_step_covers_a_new_stem_sentence_without_regex_edit() -> None:
    match = re.fullmatch(MANUAL_OUTCOME_STEP, "the manual cash-out is queued")
    assert match is not None
    assert match.group("outcome") == "is queued"


def test_manual_outcome_does_not_steal_duplicate_route() -> None:
    assert (
        re.fullmatch(MANUAL_OUTCOME_STEP, "duplicate manual routes keep a single transfer row")
        is None
    )
    assert (
        re.fullmatch(MANUAL_OUTCOME_STEP, "the cash-out is routed through the manual portal")
        is None
    )
    assert (
        re.fullmatch(MANUAL_OUTCOME_STEP, "a bank-transfer row is created on the manual portal")
        is None
    )
    assert re.fullmatch(MANUAL_OUTCOME_STEP, "the Mellat cash-out is rejected") is None


@pytest.mark.parametrize("mode", known_mellat_ach_modes())
def test_mellat_ach_when_step_matches(mode: str) -> None:
    text = f"a customer {mode}"
    match = re.fullmatch(MELLAT_ACH_WHEN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_mellat_ach_when_does_not_steal_gateway_or_concurrent() -> None:
    assert (
        re.fullmatch(MELLAT_ACH_WHEN_STEP, "a customer routes the same Mellat tracking code twice")
        is None
    )
    assert (
        re.fullmatch(
            MELLAT_ACH_WHEN_STEP, "customers concurrently route the same ACH tracking code"
        )
        is None
    )


@pytest.mark.parametrize("outcome", known_mellat_ach_outcomes())
def test_mellat_ach_outcome_step_matches(outcome: str) -> None:
    text = f"the PAYA cash-out {outcome}"
    match = re.fullmatch(MELLAT_ACH_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


def test_mellat_ach_outcome_does_not_steal_shared_thens() -> None:
    assert re.fullmatch(MELLAT_ACH_OUTCOME_STEP, "the call is rejected as invalid input") is None
    assert (
        re.fullmatch(MELLAT_ACH_OUTCOME_STEP, "duplicate Mellat routes keep a single transfer row")
        is None
    )


@pytest.mark.parametrize("mode", known_mellat_gateway_modes())
def test_mellat_gateway_when_step_matches(mode: str) -> None:
    text = f"a customer {mode}"
    match = re.fullmatch(MELLAT_GATEWAY_WHEN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize(
    "text",
    [
        "a customer routes a Mellat transfer with zero amount",
        "a customer routes an ordinary cross-bank PAYA transfer",
        "the customer routes the same Mellat tracking code twice",
    ],
)
def test_mellat_gateway_when_step_rejects(text: str) -> None:
    assert re.fullmatch(MELLAT_GATEWAY_WHEN_STEP, text) is None


@pytest.mark.parametrize("outcome", known_mellat_internal_route_outcomes())
def test_mellat_internal_route_step_matches(outcome: str) -> None:
    text = f"the Mellat internal route {outcome}"
    match = re.fullmatch(MELLAT_INTERNAL_ROUTE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


def test_mellat_internal_route_step_rejects() -> None:
    assert re.fullmatch(MELLAT_INTERNAL_ROUTE_STEP, "the Mellat cash-out is rejected") is None
    assert (
        re.fullmatch(MELLAT_INTERNAL_ROUTE_STEP, "the Mellat internal gateway client is active")
        is None
    )


def test_mellat_internal_route_step_binds_unknown_tail() -> None:
    match = re.fullmatch(MELLAT_INTERNAL_ROUTE_STEP, "the Mellat internal route is toasted")
    assert match is not None
    assert match.group("outcome") == "is toasted"


@pytest.mark.parametrize("mode", known_nemo_gateway_ask_modes())
def test_nemo_gateway_ask_step_matches(mode: str) -> None:
    text = f"the customer asks which cash-out route {mode}"
    match = re.fullmatch(NEMO_GATEWAY_ASK_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize("mode", known_nemo_gateway_app_modes())
def test_nemo_gateway_app_step_matches(mode: str) -> None:
    text = f"the customer asks the app {mode}"
    match = re.fullmatch(NEMO_GATEWAY_APP_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize("outcome", known_nemo_gateway_predicted_outcomes())
def test_nemo_gateway_predicted_step_matches(outcome: str) -> None:
    text = f"the predicted cash-out route {outcome}"
    match = re.fullmatch(NEMO_GATEWAY_PREDICTED_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


@pytest.mark.parametrize("outcome", known_nemo_gateway_app_outcomes())
def test_nemo_gateway_app_outcome_step_matches(outcome: str) -> None:
    text = f"the app cash-out {outcome}"
    match = re.fullmatch(NEMO_GATEWAY_APP_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


@pytest.mark.parametrize("mode", known_nemo_e2e_register_modes())
def test_nemo_e2e_register_step_matches(mode: str) -> None:
    text = f"the customer registers {mode}"
    match = re.fullmatch(NEMO_E2E_REGISTER_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_nemo_e2e_register_does_not_steal_iban_register() -> None:
    assert re.fullmatch(NEMO_E2E_REGISTER_STEP, "the customer registers an IBAN cash-out") is None
    assert (
        re.fullmatch(NEMO_REGISTER_STEP, "the customer registers an IBAN cash-out onto Mellat")
        is None
    )


@pytest.mark.parametrize("outcome", known_nemo_e2e_outcomes())
def test_nemo_e2e_outcome_step_matches(outcome: str) -> None:
    text = f"the registered cash-out {outcome}"
    match = re.fullmatch(NEMO_E2E_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


@pytest.mark.parametrize("mode", known_parsian_request_modes())
def test_parsian_request_step_matches(mode: str) -> None:
    text = f"the customer requests {mode}"
    match = re.fullmatch(PARSIAN_REQUEST_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


@pytest.mark.parametrize("peer", known_peer_inquire_peers())
def test_peer_inquire_step_matches(peer: str) -> None:
    text = f"the customer inquires that {peer} cash-out"
    match = re.fullmatch(PEER_INQUIRE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("peer") == peer


@pytest.mark.parametrize("rail", known_peer_live_rails())
def test_peer_live_step_matches(rail: str) -> None:
    text = f"the customer executes a live {rail} cash-out"
    match = re.fullmatch(PEER_LIVE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("rail") == rail


def test_peer_live_does_not_steal_dsh_provider_statement() -> None:
    assert (
        re.fullmatch(
            PEER_LIVE_STEP,
            "the customer executes a live Mellat cash-out onto the provider statement",
        )
        is None
    )


@pytest.mark.parametrize("mode", known_ft_shahin_request_modes())
def test_ft_shahin_request_step_matches(mode: str) -> None:
    text = f"the customer requests a ft shahin cash-out with {mode}"
    match = re.fullmatch(FT_SHAHIN_REQUEST_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_ft_shahin_request_does_not_steal_siblings() -> None:
    assert (
        re.fullmatch(FT_SHAHIN_REQUEST_STEP, "the customer requests a same-bank Shahin cash-out")
        is None
    )
    assert re.fullmatch(FT_SHAHIN_REQUEST_STEP, "the customer requests a Mellat cash-out") is None
    assert (
        re.fullmatch(FT_SHAHIN_REQUEST_STEP, "the customer requests a Parsian PAYA cash-out")
        is None
    )
    assert (
        re.fullmatch(FT_SHAHIN_REQUEST_STEP, "the customer executes a live Parsian PAYA cash-out")
        is None
    )


def test_ft_shahin_request_step_binds_unknown_tail() -> None:
    text = "the customer requests a ft shahin cash-out with a toasted rail"
    match = re.fullmatch(FT_SHAHIN_REQUEST_STEP, text)
    assert match is not None
    assert match.group("mode") == "a toasted rail"


def test_ft_shahin_inquire_step_matches() -> None:
    match = re.fullmatch(FT_SHAHIN_INQUIRE_STEP, "the customer inquires that ft shahin cash-out")
    assert match is not None


def test_ft_shahin_inquire_does_not_steal_siblings() -> None:
    assert (
        re.fullmatch(FT_SHAHIN_INQUIRE_STEP, "the customer inquires that Parsian cash-out") is None
    )
    assert re.fullmatch(FT_SHAHIN_INQUIRE_STEP, "the customer inquires that SATNA cash-out") is None
    assert (
        re.fullmatch(FT_SHAHIN_INQUIRE_STEP, "the customer inquires that Mellat cash-out") is None
    )


@pytest.mark.parametrize("mode", known_ft_shahin_route_modes())
def test_ft_shahin_route_step_matches(mode: str) -> None:
    text = f"the customer routes the same ft shahin cash-out twice with {mode}"
    match = re.fullmatch(FT_SHAHIN_ROUTE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_ft_shahin_route_does_not_steal_mellat_dsh() -> None:
    assert (
        re.fullmatch(
            FT_SHAHIN_ROUTE_STEP, "the customer routes the same Mellat tracking code twice"
        )
        is None
    )


@pytest.mark.parametrize("mode", known_ft_shahin_dsh_modes())
def test_ft_shahin_dsh_when_step_matches(mode: str) -> None:
    text = f"DSH prepares a ft shahin cash-out with {mode}"
    match = re.fullmatch(FT_SHAHIN_DSH_WHEN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_ft_shahin_dsh_does_not_steal_mellat() -> None:
    assert (
        re.fullmatch(
            FT_SHAHIN_DSH_WHEN_STEP,
            "DSH splits cash-out weights evenly between Manual and Mellat",
        )
        is None
    )
    assert re.fullmatch(FT_SHAHIN_DSH_WHEN_STEP, "DSH looks up a settled Mellat cash-out") is None


@pytest.mark.parametrize("outcome", known_ft_shahin_outcomes())
def test_ft_shahin_outcome_step_matches(outcome: str) -> None:
    text = f"the ft shahin cash-out {outcome}"
    match = re.fullmatch(FT_SHAHIN_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


def test_ft_shahin_outcome_does_not_steal_peer_routed() -> None:
    assert (
        re.fullmatch(FT_SHAHIN_OUTCOME_STEP, "the cash-out is routed through Parsian PAYA") is None
    )
    assert re.fullmatch(PEER_ROUTED_STEP, "the ft shahin cash-out is routed internally") is None
    assert (
        re.fullmatch(
            PEER_REJECTED_STEP,
            "the ft shahin cash-out is rejected without storing a transfer",
        )
        is None
    )
    assert (
        re.fullmatch(FT_SHAHIN_OUTCOME_STEP, "the cash-out is rejected without storing a transfer")
        is None
    )


def test_ft_shahin_treasury_given_step_matches() -> None:
    for rail in ("ACH", "internal"):
        text = f"ft shahin treasury can pay out over {rail}"
        match = re.fullmatch(FT_SHAHIN_TREASURY_GIVEN_STEP, text)
        assert match is not None, f"pattern must match: {text!r}"
        assert match.group("rail") == rail


@pytest.mark.parametrize("mode", known_ft_shahin_direct_modes())
def test_ft_shahin_direct_when_step_matches(mode: str) -> None:
    text = f"treasury requests a ft shahin payout with {mode}"
    match = re.fullmatch(FT_SHAHIN_DIRECT_WHEN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("mode") == mode


def test_ft_shahin_direct_when_does_not_steal_mellat_or_melli() -> None:
    assert (
        re.fullmatch(FT_SHAHIN_DIRECT_WHEN_STEP, "treasury requests a Mellat ACH direct payout")
        is None
    )
    assert (
        re.fullmatch(FT_SHAHIN_DIRECT_WHEN_STEP, "treasury requests a Melli ACH direct payout")
        is None
    )


@pytest.mark.parametrize("outcome", known_ft_shahin_direct_outcomes())
def test_ft_shahin_direct_outcome_step_matches(outcome: str) -> None:
    text = f"the ft shahin payout {outcome}"
    match = re.fullmatch(FT_SHAHIN_DIRECT_OUTCOME_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("outcome") == outcome


@pytest.mark.parametrize("route", known_peer_routed_tails())
def test_peer_routed_step_matches(route: str) -> None:
    text = f"the cash-out is routed {route}"
    match = re.fullmatch(PEER_ROUTED_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("route") == route


def test_peer_routed_step_rejects() -> None:
    assert (
        re.fullmatch(PEER_ROUTED_STEP, "the cash-out is rejected without storing a transfer")
        is None
    )


def test_peer_routed_step_binds_unknown_tail() -> None:
    match = re.fullmatch(PEER_ROUTED_STEP, "the cash-out is routed through a toasted rail")
    assert match is not None
    assert match.group("route") == "through a toasted rail"


@pytest.mark.parametrize("reason", known_peer_rejected_tails())
def test_peer_rejected_step_matches(reason: str) -> None:
    text = f"the cash-out is rejected {reason}"
    match = re.fullmatch(PEER_REJECTED_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("reason") == reason


def test_peer_rejected_step_rejects() -> None:
    assert re.fullmatch(PEER_REJECTED_STEP, "the cash-out is routed through Parsian PAYA") is None


@pytest.mark.parametrize(
    "text",
    [
        'the telephone bill pool has a "no_debt" case',
        'the telephone bill pool has an "invalid_phone" case',
        'the telephone bill pool has a "both_terms_debt_region" case',
    ],
)
def test_telephone_pool_case_step_matches(text: str) -> None:
    match = re.fullmatch(TELEPHONE_POOL_CASE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("case_name")


@pytest.mark.parametrize(
    "text",
    [
        "the telephone bill pool has a no_debt case",
        'the telephone bill pool has a "" case',
    ],
)
def test_telephone_pool_case_step_rejects(text: str) -> None:
    assert re.fullmatch(TELEPHONE_POOL_CASE_STEP, text) is None


@pytest.mark.parametrize(
    ("text", "gateway"),
    [
        ("cash-out goes through Mellat", "Mellat"),
        ("cash-out goes through Mellat PAYA", "Mellat PAYA"),
        ("cash-out goes through Mellat SATNA", "Mellat SATNA"),
        ("cash-out goes through Manual", "Manual"),
        ("cash-out goes through Parsian PAYA", "Parsian PAYA"),
        ("cash-out goes through ft shahin", "ft shahin"),
        ("cash-out goes through ft shahin PAYA", "ft shahin PAYA"),
        ("cash-out goes through ft shahin SATNA", "ft shahin SATNA"),
    ],
)
def test_cash_out_gateway_step_matches(text: str, gateway: str) -> None:
    match = re.fullmatch(CASH_OUT_GATEWAY_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("gateway") == gateway


def test_cash_out_gateway_step_rejects() -> None:
    assert re.fullmatch(CASH_OUT_GATEWAY_STEP, "cash-out goes through") is None
    assert re.fullmatch(CASH_OUT_GATEWAY_STEP, "cash-out goes through Mellat_PAYA") is None


def test_cash_out_gateway_step_binds_unknown_tail() -> None:
    match = re.fullmatch(CASH_OUT_GATEWAY_STEP, "cash-out goes through a toasted gateway")
    assert match is not None
    assert match.group("gateway") == "a toasted gateway"


@pytest.mark.parametrize(
    ("text", "capability"),
    [
        ("a Nemo customer can register an IBAN cash-out", "register an IBAN cash-out"),
        ("a Nemo customer can predict a cash-out fee", "predict a cash-out fee"),
    ],
)
def test_nemo_customer_capability_step_matches(text: str, capability: str) -> None:
    match = re.fullmatch(NEMO_CUSTOMER_CAPABILITY_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("capability") == capability


def test_nemo_customer_capability_step_rejects() -> None:
    assert re.fullmatch(NEMO_CUSTOMER_CAPABILITY_STEP, "a Nemo customer can") is None
    assert re.fullmatch(NEMO_CUSTOMER_CAPABILITY_STEP, "a Nemo customer can toast_bread") is None


def test_nemo_customer_capability_step_binds_unknown_tail() -> None:
    match = re.fullmatch(NEMO_CUSTOMER_CAPABILITY_STEP, "a Nemo customer can toast bread")
    assert match is not None
    assert match.group("capability") == "toast bread"


@pytest.mark.parametrize(
    ("pattern", "text", "title"),
    [
        (
            BILL_INQUIRY_REJECTED_STEP,
            "the bill inquiry is rejected as INVALID_PARAMETER",
            "INVALID_PARAMETER",
        ),
        (
            BILL_INQUIRY_REJECTED_STEP,
            "the bill inquiry is rejected as INVALID_UTILITY_BILL_TYPE",
            "INVALID_UTILITY_BILL_TYPE",
        ),
        (
            BILL_PAYMENT_INIT_REJECTED_STEP,
            "the bill payment init is rejected as BILL_AMOUNT_INVALID",
            "BILL_AMOUNT_INVALID",
        ),
        (
            ADMIN_BILLS_CONFIG_REJECTED_STEP,
            "the admin bills config update is rejected as INVALID_PARAMETER",
            "INVALID_PARAMETER",
        ),
    ],
)
def test_bill_rejection_steps_match(pattern: str, text: str, title: str) -> None:
    match = re.fullmatch(pattern, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("result_title") == title


@pytest.mark.parametrize(
    ("pattern", "text"),
    [
        (BILL_INQUIRY_REJECTED_STEP, "the bill payment init is rejected as INVALID_PARAMETER"),
        (BILL_PAYMENT_INIT_REJECTED_STEP, "the bill inquiry is rejected as INVALID_PARAMETER"),
        (ADMIN_BILLS_CONFIG_REJECTED_STEP, "the bill inquiry is rejected as INVALID_PARAMETER"),
    ],
)
def test_bill_rejection_steps_do_not_cross_match(pattern: str, text: str) -> None:
    assert re.fullmatch(pattern, text) is None


@pytest.mark.parametrize("tile", known_dashboard_tiles())
def test_open_from_dashboard_step_matches(tile: str) -> None:
    text = f"the staff opens {tile} from the dashboard"
    match = re.fullmatch(OPEN_FROM_DASHBOARD_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("tile") == tile


def test_open_from_dashboard_step_rejects() -> None:
    assert (
        re.fullmatch(
            OPEN_FROM_DASHBOARD_STEP, "the customer opens landline bill inquiry from the hub"
        )
        is None
    )
    assert (
        re.fullmatch(OPEN_FROM_DASHBOARD_STEP, "the staff opens electricity inquiry distribution")
        is None
    )
    assert re.fullmatch(OPEN_FROM_DASHBOARD_STEP, "the staff opens Super App settings") is None


def test_open_from_dashboard_step_binds_unknown_tail() -> None:
    match = re.fullmatch(OPEN_FROM_DASHBOARD_STEP, "the staff opens wallet from the dashboard")
    assert match is not None
    assert match.group("tile") == "wallet"


def test_open_operator_distribution_step_matches() -> None:
    match = re.fullmatch(
        OPEN_OPERATOR_DISTRIBUTION_STEP, "the staff opens the mci operator distribution"
    )
    assert match is not None
    assert match.group("operator") == "mci"


@pytest.mark.parametrize(
    "text",
    [
        "the staff opens electricity inquiry distribution",
        "the staff opens the operator distribution",
    ],
)
def test_open_operator_distribution_step_rejects(text: str) -> None:
    assert re.fullmatch(OPEN_OPERATOR_DISTRIBUTION_STEP, text) is None


@pytest.mark.parametrize(
    "text",
    [
        "the staff sets operator distribution weights to 10, 10, 10 and 10",
        "the staff sets operator distribution weights to 0, 20, 30 and 50",
    ],
)
def test_set_operator_weights_step_matches(text: str) -> None:
    match = re.fullmatch(SET_OPERATOR_WEIGHTS_STEP, text)
    assert match is not None
    assert match.group("raw")


def test_operator_picker_shown_and_lists_steps_match() -> None:
    shown = re.fullmatch(
        OPERATOR_PICKER_SHOWN_STEP, "the operator picker is shown for internet package"
    )
    lists = re.fullmatch(
        OPERATOR_PICKER_LISTS_STEP, "the operator picker lists the topup operators"
    )
    assert shown is not None and shown.group("product") == "internet package"
    assert lists is not None and lists.group("product") == "topup"


def test_operator_distribution_shown_and_providers_match() -> None:
    shown = re.fullmatch(
        OPERATOR_DISTRIBUTION_SHOWN_STEP,
        "the operator distribution is shown for internet package mci",
    )
    providers = re.fullmatch(
        OPERATOR_PROVIDERS_SHOWN_STEP,
        "the operator distribution shows providers eniac, rayan mehr, jiring and behsa",
    )
    assert shown is not None and shown.group("title_key") == "internet package mci"
    assert providers is not None
    assert providers.group("a", "b", "c", "d") == ("eniac", "rayan mehr", "jiring", "behsa")


@pytest.mark.parametrize(
    ("text", "state"),
    [
        ("operator distribution confirm is enabled", "enabled"),
        ("operator distribution confirm is disabled", "disabled"),
    ],
)
def test_operator_confirm_state_step_matches(text: str, state: str) -> None:
    match = re.fullmatch(OPERATOR_CONFIRM_STATE_STEP, text)
    assert match is not None
    assert match.group("state") == state


def test_operator_confirm_does_not_steal_inquiry_confirm() -> None:
    assert (
        re.fullmatch(OPERATOR_CONFIRM_STATE_STEP, "inquiry distribution confirm is disabled")
        is None
    )
    assert (
        re.fullmatch(INQUIRY_CONFIRM_STATE_STEP, "operator distribution confirm is disabled")
        is None
    )


def test_operator_weights_and_admin_weights_match() -> None:
    ui = re.fullmatch(
        OPERATOR_WEIGHTS_ARE_STEP, "the operator distribution weights are 0, 20, 30 and 50"
    )
    admin = re.fullmatch(
        MCI_ADMIN_WEIGHTS_STEP, "the mci internet package admin weights are 0, 20, 30 and 50"
    )
    assert ui is not None and ui.group("raw") == "0, 20, 30 and 50"
    assert admin is not None and admin.group("raw") == "0, 20, 30 and 50"


@pytest.mark.parametrize(
    ("text", "filter_field"),
    [
        (f"the merchants with Rahkaran codes are filtered by {field}", field)
        for field in known_filter_fields()
    ],
)
def test_filter_with_rahkaran_step_matches(text: str, filter_field: str) -> None:
    match = re.fullmatch(FILTER_WITH_RAHKARAN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("filter_field") == filter_field


def test_filter_with_rahkaran_step_rejects() -> None:
    assert (
        re.fullmatch(
            FILTER_WITH_RAHKARAN_STEP,
            "the merchants without Rahkaran codes are filtered by business name",
        )
        is None
    )
    assert (
        re.fullmatch(FILTER_WITH_RAHKARAN_STEP, "the merchants are filtered by business name")
        is None
    )


def test_filter_with_rahkaran_step_binds_unknown_tail() -> None:
    match = re.fullmatch(
        FILTER_WITH_RAHKARAN_STEP,
        "the merchants with Rahkaran codes are filtered by toasted field",
    )
    assert match is not None
    assert match.group("filter_field") == "toasted field"


@pytest.mark.parametrize(
    ("text", "filter_field"),
    [
        (
            f"the filtered merchants with Rahkaran codes must contain the {field}",
            field,
        )
        for field in known_filter_fields()
    ],
)
def test_filtered_contain_with_step_matches(text: str, filter_field: str) -> None:
    match = re.fullmatch(FILTERED_CONTAIN_WITH_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("filter_field") == filter_field


@pytest.mark.parametrize("filter_field", list(known_without_rahkaran_filter_fields()))
def test_filter_without_rahkaran_step_matches(filter_field: str) -> None:
    text = f"the merchants without Rahkaran codes are filtered by {filter_field}"
    match = re.fullmatch(FILTER_WITHOUT_RAHKARAN_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("filter_field") == filter_field


def test_filter_without_rahkaran_step_rejects() -> None:
    assert (
        re.fullmatch(
            FILTER_WITHOUT_RAHKARAN_STEP,
            "the merchants with Rahkaran codes are filtered by business name",
        )
        is None
    )


def test_filter_without_rahkaran_step_binds_unknown_tail() -> None:
    match = re.fullmatch(
        FILTER_WITHOUT_RAHKARAN_STEP,
        "the merchants without Rahkaran codes are filtered by toasted field",
    )
    assert match is not None
    assert match.group("filter_field") == "toasted field"


@pytest.mark.parametrize("filter_field", list(known_without_rahkaran_filter_fields()))
def test_filtered_contain_without_step_matches(filter_field: str) -> None:
    text = f"the filtered merchants without Rahkaran codes must contain the {filter_field}"
    match = re.fullmatch(FILTERED_CONTAIN_WITHOUT_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("filter_field") == filter_field


@pytest.mark.parametrize(
    ("text", "transaction_type"),
    [(f"a {kind} transaction is created", kind) for kind in known_transaction_types()],
)
def test_create_transaction_step_matches(text: str, transaction_type: str) -> None:
    match = re.fullmatch(CREATE_TRANSACTION_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("transaction_type") == transaction_type


def test_create_transaction_step_rejects() -> None:
    assert re.fullmatch(CREATE_TRANSACTION_STEP, "a transaction is created") is None
    assert re.fullmatch(CREATE_TRANSACTION_STEP, "a credit_purchase transaction is created") is None


def test_create_transaction_step_binds_unknown_tail() -> None:
    match = re.fullmatch(CREATE_TRANSACTION_STEP, "a toasted kind transaction is created")
    assert match is not None
    assert match.group("transaction_type") == "toasted kind"


@pytest.mark.parametrize("table", list(known_ledger_tables()))
def test_ledger_table_step_matches(table: str) -> None:
    text = f"the transaction must be present in the {table} table"
    match = re.fullmatch(LEDGER_TABLE_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.group("table") == table


def test_ledger_table_step_rejects() -> None:
    assert re.fullmatch(LEDGER_TABLE_STEP, "the ledger records the transaction request") is None
    assert (
        re.fullmatch(LEDGER_TABLE_STEP, "the transaction amount must match the requested amount")
        is None
    )
    assert (
        re.fullmatch(LEDGER_TABLE_STEP, "the transaction must be present in the Foo table") is None
    )


@pytest.mark.parametrize(
    ("text", "groups"),
    [
        (
            'the bundle catalog is requested for operator id "1" cell "09124445456"',
            {"operator_id": "1", "cell_number": "09124445456", "sim_card_type": None},
        ),
        (
            'the bundle catalog is requested for operator id "4" cell "09981255989" '
            'SIM type "PREPAID"',
            {"operator_id": "4", "cell_number": "09981255989", "sim_card_type": "PREPAID"},
        ),
        (
            'the bundle catalog is requested for operator id "1" cell "09124445456" '
            'SIM type "toasted"',
            {"operator_id": "1", "cell_number": "09124445456", "sim_card_type": "toasted"},
        ),
    ],
)
def test_bundle_catalog_operator_cell_step_matches(text: str, groups: dict[str, str]) -> None:
    match = re.fullmatch(BUNDLE_CATALOG_OPERATOR_CELL_STEP, text)
    assert match is not None, f"pattern must match: {text!r}"
    assert match.groupdict() == groups


@pytest.mark.parametrize(
    "text",
    [
        "the bundle catalog is requested for operator id 1 cell 09124445456",
        'the bundle catalog is requested for operator id "1"',
        'the bundle catalog is requested for SIM card type "POSTPAID"',
        'the top-up operators list is requested for operator id "1" cell "09124445456"',
    ],
)
def test_bundle_catalog_operator_cell_step_rejects(text: str) -> None:
    assert re.fullmatch(BUNDLE_CATALOG_OPERATOR_CELL_STEP, text) is None


def _inline_parsers_re_literals(path: Path) -> list[str]:
    """Extract ``parsers.re(r"...")`` string literals from a step file."""
    found: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "re" or not node.args:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            found.append(arg.value)
            continue
        if isinstance(arg, ast.Name):
            raise AssertionError(
                f'{path}: parsers.re({arg.id}) must be an inline r"..." string, '
                "not an imported constant"
            )
    return found


def test_no_parsers_re_uses_an_imported_constant() -> None:
    """IDE plugins only see quoted strings on the decorator."""
    steps_dir = Path("tests/bdd/steps")
    for path in sorted(steps_dir.glob("*.py")):
        _inline_parsers_re_literals(path)


def test_service_constants_match_inline_decorator_regexes() -> None:
    """Dispatch-table constants must equal the regex written on the step."""
    literals: list[str] = []
    for path in sorted(Path("tests/bdd/steps").glob("*.py")):
        literals.extend(_inline_parsers_re_literals(path))
    expected = {
        LOGIN_PANEL_ACTION_STEP,
        LOGIN_UI_STATE_STEP,
        DUPLICATE_ROUTE_STEP,
        BILL_DISTRIBUTION_OPEN_STEP,
        INQUIRY_CONFIRM_STATE_STEP,
        TELEPHONE_POOL_CASE_STEP,
        CASH_OUT_GATEWAY_STEP,
        NEMO_CUSTOMER_CAPABILITY_STEP,
        BILL_INQUIRY_REJECTED_STEP,
        BILL_PAYMENT_INIT_REJECTED_STEP,
        ADMIN_BILLS_CONFIG_REJECTED_STEP,
        OPEN_FROM_DASHBOARD_STEP,
        OPEN_FROM_HUB_STEP,
        OPEN_OPERATOR_DISTRIBUTION_STEP,
        SET_OPERATOR_WEIGHTS_STEP,
        OPERATOR_PICKER_SHOWN_STEP,
        OPERATOR_PICKER_LISTS_STEP,
        OPERATOR_DISTRIBUTION_SHOWN_STEP,
        OPERATOR_PROVIDERS_SHOWN_STEP,
        OPERATOR_WEIGHTS_ARE_STEP,
        OPERATOR_CONFIRM_STATE_STEP,
        MCI_ADMIN_WEIGHTS_STEP,
        ADMIN_SET_ELECTRICITY_WEIGHTS_STEP,
        SET_FIRST_PROVIDER_WEIGHT_STEP,
        SET_INQUIRY_WEIGHTS_STEP,
        SET_PROVIDER_WEIGHT_STEP,
        INQUIRY_DISTRIBUTION_SHOWN_STEP,
        INQUIRY_PROVIDERS_SHOWN_STEP,
        INQUIRY_WEIGHTS_ARE_STEP,
        INQUIRY_PROVIDER_WEIGHT_IS_STEP,
        ELECTRICITY_ADMIN_WEIGHTS_STEP,
        REGISTRATION_PROVIDER_PIN_STEP,
        REGISTRATION_INQUIRE_MODE_STEP,
        REGISTRATION_INQUIRE_FAULT_STEP,
        REGISTRATION_INVALID_WEIGHTS_STEP,
        REGISTRATION_INQUIRY_REJECTED_STEP,
        REGISTRATION_SETTINGS_REJECTED_STEP,
        POSTAL_PROVIDER_PIN_STEP,
        POSTAL_INQUIRE_STEP,
        POSTAL_INQUIRY_OUTCOME_STEP,
        POSTAL_INVALID_WEIGHTS_STEP,
        POSTAL_SETTINGS_REJECTED_STEP,
        LANDLINE_OPEN_PERIOD_STEP,
        LANDLINE_PERIOD_STATE_STEP,
        LANDLINE_VALIDATE_CASE_STEP,
        TCI_REQUEST_STEP,
        TCI_TEL_STATUS_STEP,
        LANDLINE_VALIDATE_THEN_STEP,
        TCI_INQUIRY_OUTCOME_STEP,
        BILL_INQUIRY_CASE_STEP,
        BILL_INIT_CASE_STEP,
        REFUND_LOOKUP_STEP,
        REFUND_RETURNED_ID_STEP,
        REFUND_DESTINATION_TYPE_STEP,
        TRANSFER_CONDITION_STEP,
        TRANSFER_REJECTED_STEP,
        WALLET_MIX_STEP,
        PROMISSORY_STAGE_STEP,
        PROMISSORY_PIN_STEP,
        PROMISSORY_ROUTE_STEP,
        PROMISSORY_INIT_MISSING_STEP,
        PROMISSORY_INIT_WITH_STEP,
        PROMISSORY_INIT_MISSING_REJECTED_STEP,
        PROMISSORY_ADMIN_STEP,
        PROMISSORY_CONCURRENT_STEP,
        PROMISSORY_RENEW_STEP,
        PROMISSORY_PROVIDER_STEP,
        PROMISSORY_BAD_REQUEST_STEP,
        PROMISSORY_SUCCESS_STEP,
        PROMISSORY_REFUND_REJECTED_STEP,
        PROMISSORY_PROTECTED_STEP,
        PROMISSORY_CONCURRENT_RESULT_STEP,
        PROMISSORY_KUKNOS_NOTE_STEP,
        PROMISSORY_START_OUTCOME_STEP,
        PROMISSORY_RENEWAL_RESULT_STEP,
        SHAHKAR_IDENTITY_STEP,
        SHAHKAR_INQUIRE_STEP,
        SHAHKAR_FAULT_STEP,
        SHAHKAR_INQUIRY_OUTCOME_STEP,
        DIGITAL_SIGNATURE_LIVENESS_PREP_STEP,
        DIGITAL_SIGNATURE_SETUP_STEP,
        DIGITAL_SIGNATURE_INITIATE_STEP,
        DIGITAL_SIGNATURE_VALIDATE_STEP,
        DIGITAL_SIGNATURE_RESPONSE_STEP,
        DIGITAL_SIGNATURE_DSP_STEP,
        MELLAT_INVALID_ROUTE_STEP,
        NEMO_CASH_OUT_THROUGH_STEP,
        NEMO_PREDICT_FEE_STEP,
        NEMO_PREDICT_OUTCOME_STEP,
        NEMO_REGISTER_STEP,
        NEMO_REGISTER_OUTCOME_STEP,
        MELLI_DIRECT_WHEN_STEP,
        MELLAT_DIRECT_WHEN_STEP,
        MELLI_DIRECT_OUTCOME_STEP,
        MELLAT_DIRECT_OUTCOME_STEP,
        MELLAT_DSH_REQUEST_STEP,
        MELLAT_DSH_REQUESTS_STEP,
        MELLAT_DSH_TRACKING_STEP,
        MELLAT_DSH_ACT_STEP,
        MELLAT_DSH_STAFF_STEP,
        MELLAT_DSH_OUTCOME_STEP,
        MANUAL_REQUEST_STEP,
        MANUAL_EXECUTE_STEP,
        MANUAL_INQUIRE_STEP,
        MANUAL_ACT_STEP,
        MANUAL_STAFF_STEP,
        MANUAL_OUTCOME_STEP,
        MELLAT_ACH_WHEN_STEP,
        MELLAT_ACH_OUTCOME_STEP,
        MELLAT_GATEWAY_WHEN_STEP,
        MELLAT_INTERNAL_ROUTE_STEP,
        NEMO_GATEWAY_ASK_STEP,
        NEMO_GATEWAY_APP_STEP,
        NEMO_GATEWAY_PREDICTED_STEP,
        NEMO_GATEWAY_APP_OUTCOME_STEP,
        NEMO_E2E_REGISTER_STEP,
        NEMO_E2E_OUTCOME_STEP,
        PARSIAN_REQUEST_STEP,
        PEER_INQUIRE_STEP,
        PEER_LIVE_STEP,
        PEER_ROUTED_STEP,
        PEER_REJECTED_STEP,
        FT_SHAHIN_REQUEST_STEP,
        FT_SHAHIN_INQUIRE_STEP,
        FT_SHAHIN_ROUTE_STEP,
        FT_SHAHIN_DSH_WHEN_STEP,
        FT_SHAHIN_OUTCOME_STEP,
        FT_SHAHIN_TREASURY_GIVEN_STEP,
        FT_SHAHIN_DIRECT_WHEN_STEP,
        FT_SHAHIN_DIRECT_OUTCOME_STEP,
        FILTER_WITH_RAHKARAN_STEP,
        FILTER_WITHOUT_RAHKARAN_STEP,
        FILTERED_CONTAIN_WITH_STEP,
        FILTERED_CONTAIN_WITHOUT_STEP,
        CREATE_TRANSACTION_STEP,
        LEDGER_TABLE_STEP,
    }
    missing = expected - set(literals)
    assert not missing, f"inline decorator regex missing for constants: {missing}"
