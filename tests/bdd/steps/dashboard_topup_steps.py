"""Dashboard Super App — topup / IPKG provider weight UI + admin steps."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.config.settings import Settings
from tests.services.dashboard_topup_ui import (
    assert_operator_confirm_state,
    assert_operator_distribution_shown,
    assert_operator_picker_shown,
    assert_operator_providers,
    assert_operator_tiles,
    assert_operator_weights,
    assert_operator_weights_match_noted,
    open_operator_distribution,
    set_operator_weights,
)
from tests.services.topup_operator_admin import (
    TopupOperatorAdminSession,
    bind_topup_operator_admin,
)
from tests.ui.pages.dashboard.operator_picker_modal import DashboardOperatorPickerModal
from tests.ui.pages.dashboard.topup_provider_weights_modal import (
    DashboardTopupProviderWeightsModal,
)

scenarios("../features/dashboard/topup_ipkg_provider_weights.feature")


@pytest.fixture
def topup_operator_admin(
    request: pytest.FixtureRequest,
    dashboard_client: ApiClient,
    settings: Settings,
    dashboard_access_token: str,
) -> TopupOperatorAdminSession:
    """Per-scenario internet-package admin config note/restore session."""
    return bind_topup_operator_admin(request, dashboard_client, settings, dashboard_access_token)


@when("the staff closes the operator picker")
def _(dashboard_operator_picker_modal: DashboardOperatorPickerModal) -> None:
    dashboard_operator_picker_modal.close()


@when(parsers.re(r"^the staff opens the (?P<operator>[A-Za-z0-9]+) operator distribution$"))
def _(
    operator: str,
    dashboard_operator_picker_modal: DashboardOperatorPickerModal,
    dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal,
) -> None:
    open_operator_distribution(
        operator,
        dashboard_operator_picker_modal,
        dashboard_topup_provider_weights_modal,
    )


@when("the staff notes the current operator distribution weights")
def _(
    dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal,
    topup_operator_admin: TopupOperatorAdminSession,
) -> None:
    topup_operator_admin.note_ui_weights(dashboard_topup_provider_weights_modal.weight_values())


@when("the staff notes the current internet package admin operator configs")
def _(topup_operator_admin: TopupOperatorAdminSession) -> None:
    topup_operator_admin.note_internet_configs()


@when(parsers.re(r"^the staff sets operator distribution weights to (?P<raw>[\d, and]+)$"))
def _(
    dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal,
    raw: str,
) -> None:
    set_operator_weights(dashboard_topup_provider_weights_modal, raw)


@when("the staff goes back from operator distribution")
def _(dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal) -> None:
    dashboard_topup_provider_weights_modal.click_back()


@when("the staff confirms operator distribution update")
def _(dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal) -> None:
    dashboard_topup_provider_weights_modal.click_confirm()


@when("the staff restores the noted internet package admin operator configs")
def _(topup_operator_admin: TopupOperatorAdminSession) -> None:
    topup_operator_admin.restore_noted_configs()


@then(parsers.re(r"^the operator picker is shown for (?P<product>internet package|topup)$"))
def _(
    product: str,
    dashboard_operator_picker_modal: DashboardOperatorPickerModal,
) -> None:
    assert_operator_picker_shown(dashboard_operator_picker_modal, product)


@then(parsers.re(r"^the operator picker lists the (?P<product>internet package|topup) operators$"))
def _(
    product: str,
    dashboard_operator_picker_modal: DashboardOperatorPickerModal,
) -> None:
    assert_operator_tiles(dashboard_operator_picker_modal, product)


@then(parsers.re(r"^the operator distribution is shown for (?P<title_key>[A-Za-z0-9 ]+)$"))
def _(
    title_key: str,
    dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal,
) -> None:
    assert_operator_distribution_shown(dashboard_topup_provider_weights_modal, title_key)


@then(
    parsers.re(
        r"^the operator distribution shows providers "
        r"(?P<a>[A-Za-z0-9 ]+), (?P<b>[A-Za-z0-9 ]+), (?P<c>[A-Za-z0-9 ]+) "
        r"and (?P<d>[A-Za-z0-9 ]+)$"
    )
)
def _(
    dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal,
    a: str,
    b: str,
    c: str,
    d: str,
) -> None:
    assert_operator_providers(dashboard_topup_provider_weights_modal, a, b, c, d)


@then(parsers.re(r"^the operator distribution weights are (?P<raw>[\d, and]+)$"))
def _(
    dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal,
    raw: str,
) -> None:
    assert_operator_weights(dashboard_topup_provider_weights_modal, raw)


@then("the operator distribution weights match the noted values")
def _(
    dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal,
    topup_operator_admin: TopupOperatorAdminSession,
) -> None:
    assert_operator_weights_match_noted(
        dashboard_topup_provider_weights_modal, topup_operator_admin.ui_values
    )


@then(parsers.re(r"^operator distribution confirm is (?P<state>enabled|disabled)$"))
def _(
    state: str,
    dashboard_topup_provider_weights_modal: DashboardTopupProviderWeightsModal,
) -> None:
    assert_operator_confirm_state(dashboard_topup_provider_weights_modal, state)


@then(parsers.re(r"^the mci internet package admin weights are (?P<raw>[\d, and]+)$"))
def _(topup_operator_admin: TopupOperatorAdminSession, raw: str) -> None:
    topup_operator_admin.assert_mci_internet_weights(raw)


@then("the mci internet package admin enabled flags match the weights")
def _(topup_operator_admin: TopupOperatorAdminSession) -> None:
    topup_operator_admin.assert_mci_enabled_matches_weights()


@then("the mci internet package admin configs match the noted values")
def _(topup_operator_admin: TopupOperatorAdminSession) -> None:
    topup_operator_admin.assert_mci_configs_match_noted()
