"""Dashboard Super App bill-inquiry UI orchestration and asserts."""

from __future__ import annotations

from collections.abc import Callable

from tests.services.assert_report import assert_equals
from tests.services.dashboard_weight_ui import (
    assert_confirm_enabled,
    assert_weights_from_raw,
    assert_weights_match_noted,
    set_weights_from_raw,
)
from tests.ui.labels.dashboard import (
    DISTRIBUTION_TITLE_KEYS,
    PROVIDER_KEYS,
    DashboardLabels,
    resolve_label,
)
from tests.ui.pages.dashboard.bill_inquiry_modal import DashboardBillInquiryModal
from tests.ui.pages.dashboard.bill_provider_weights_modal import (
    DashboardBillProviderWeightsModal,
)
from tests.ui.pages.dashboard.super_app_page import DashboardSuperAppPage


def ensure_bill_picker_open(
    super_app: DashboardSuperAppPage,
    picker: DashboardBillInquiryModal,
    weights: DashboardBillProviderWeightsModal,
) -> None:
    """Open the bill inquiry picker, backing out of the weights modal if needed."""
    if picker.is_open():
        return
    if weights.is_open():
        weights.click_back()
    super_app.open_bill_inquiry()
    picker.should_be_open()


def open_electricity_distribution(
    super_app: DashboardSuperAppPage,
    picker: DashboardBillInquiryModal,
    weights: DashboardBillProviderWeightsModal,
) -> None:
    """Open electricity inquiry provider distribution from the dashboard."""
    ensure_bill_picker_open(super_app, picker, weights)
    picker.open_electricity()
    weights.should_be_open(DashboardLabels.ELECTRICITY_INQUIRY)


def open_landline_distribution(
    super_app: DashboardSuperAppPage,
    picker: DashboardBillInquiryModal,
    weights: DashboardBillProviderWeightsModal,
) -> None:
    """Open landline inquiry provider distribution from the dashboard."""
    ensure_bill_picker_open(super_app, picker, weights)
    picker.open_landline()
    weights.should_be_open(DashboardLabels.LANDLINE_INQUIRY)


BILL_DISTRIBUTION_OPEN_STEP = (
    r"^the staff opens (?P<bill_type>electricity|landline) inquiry distribution$"
)

_DistributionOpener = Callable[
    [DashboardSuperAppPage, DashboardBillInquiryModal, DashboardBillProviderWeightsModal],
    None,
]

_DISTRIBUTION_OPENERS: dict[str, _DistributionOpener] = {
    "electricity": open_electricity_distribution,
    "landline": open_landline_distribution,
}


def known_bill_distribution_types() -> list[str]:
    """Registered bill types, for the regex unit test to keep in sync."""
    return sorted(_DISTRIBUTION_OPENERS)


def open_bill_distribution(
    bill_type: str,
    super_app: DashboardSuperAppPage,
    picker: DashboardBillInquiryModal,
    weights: DashboardBillProviderWeightsModal,
) -> None:
    """Open one bill type's inquiry provider distribution from the dashboard.

    Args:
        bill_type: Captured bill-type phrase (``"electricity"`` or ``"landline"``).
        super_app: Super App settings page object.
        picker: Bill inquiry picker modal.
        weights: Provider weights modal.

    Raises:
        KeyError: If the bill type has no registered opener — a ``.feature`` typo
            fails loudly with the known types listed.
    """
    opener = _DISTRIBUTION_OPENERS.get(bill_type)
    if opener is None:
        raise KeyError(
            f"No distribution opener for {bill_type!r}; "
            f"known types: {known_bill_distribution_types()}"
        )
    opener(super_app, picker, weights)


def set_inquiry_weights(modal: DashboardBillProviderWeightsModal, raw: str) -> None:
    """Set inquiry distribution weights from a Gherkin list."""
    set_weights_from_raw(modal, raw)


def set_first_provider_weight(modal: DashboardBillProviderWeightsModal, value: str) -> None:
    """Set the first listed provider weight from a Gherkin digit string."""
    modal.set_weight_at(0, int(value))


def set_inquiry_provider_weight(
    modal: DashboardBillProviderWeightsModal,
    provider: str,
    value: str,
) -> None:
    """Set one provider weight by English Gherkin key."""
    label = resolve_label(PROVIDER_KEYS, provider, kind="provider")
    modal.set_weight_for_provider(label, int(value))


def assert_distribution_shown(
    modal: DashboardBillProviderWeightsModal,
    bill_type: str,
) -> None:
    """Assert the distribution dialog title for a Gherkin bill-type key."""
    title = resolve_label(DISTRIBUTION_TITLE_KEYS, bill_type, kind="distribution title")
    modal.should_be_open(title)


def assert_inquiry_providers(
    modal: DashboardBillProviderWeightsModal,
    first: str,
    second: str,
) -> None:
    """Assert the two provider labels shown in the distribution dialog."""
    modal.should_show_providers(
        resolve_label(PROVIDER_KEYS, first, kind="provider"),
        resolve_label(PROVIDER_KEYS, second, kind="provider"),
    )


def assert_inquiry_weights(modal: DashboardBillProviderWeightsModal, raw: str) -> None:
    """Assert UI inquiry weights match a Gherkin list."""
    assert_weights_from_raw(modal, raw, label="Inquiry weights")


def assert_inquiry_provider_weight(
    modal: DashboardBillProviderWeightsModal,
    provider: str,
    value: str,
) -> None:
    """Assert one provider weight by English Gherkin key."""
    label = resolve_label(PROVIDER_KEYS, provider, kind="provider")
    actual = modal.weight_for_provider(label)
    assert_equals(f"Inquiry weight for {provider}", actual, int(value))


def assert_inquiry_weights_match_noted(
    modal: DashboardBillProviderWeightsModal,
    noted: list[int] | None,
) -> None:
    """Assert UI weights match a previously noted snapshot."""
    assert_weights_match_noted(
        modal,
        noted,
        label="Inquiry weights match noted values",
        what="inquiry weights",
    )


INQUIRY_CONFIRM_STATE_STEP = r"^inquiry distribution confirm is (?P<state>enabled|disabled)$"
ADMIN_SET_ELECTRICITY_WEIGHTS_STEP = (
    r"^the admin sets electricity inquiry weights to (?P<raw>[-0-9, and]+) via the admin API$"
)
SET_FIRST_PROVIDER_WEIGHT_STEP = r"^the staff sets the first provider weight to (?P<value>-?\d+)$"
SET_INQUIRY_WEIGHTS_STEP = r"^the staff sets inquiry weights to (?P<raw>[-0-9, and]+)$"
SET_PROVIDER_WEIGHT_STEP = (
    r"^the staff sets the inquiry weight for (?P<provider>[A-Za-z0-9]+) to (?P<value>-?\d+)$"
)
INQUIRY_DISTRIBUTION_SHOWN_STEP = (
    r"^the inquiry distribution is shown for (?P<bill_type>[A-Za-z0-9 ]+)$"
)
INQUIRY_PROVIDERS_SHOWN_STEP = (
    r"^the inquiry distribution shows providers "
    r"(?P<first>[A-Za-z0-9]+) and (?P<second>[A-Za-z0-9]+)$"
)
INQUIRY_WEIGHTS_ARE_STEP = r"^the inquiry weights are (?P<raw>[-0-9, and]+)$"
INQUIRY_PROVIDER_WEIGHT_IS_STEP = (
    r"^the inquiry weight for (?P<provider>[A-Za-z0-9]+) is (?P<value>-?\d+)$"
)
ELECTRICITY_ADMIN_WEIGHTS_STEP = (
    r"^the electricity admin inquiry weights are (?P<raw>[-0-9, and]+)$"
)


def assert_inquiry_confirm_enabled(
    modal: DashboardBillProviderWeightsModal,
    *,
    enabled: bool,
) -> None:
    """Assert inquiry distribution Confirm is enabled or disabled."""
    label = (
        "Inquiry distribution confirm is enabled"
        if enabled
        else "Inquiry distribution confirm is disabled"
    )
    assert_confirm_enabled(modal, enabled=enabled, label=label)


def assert_inquiry_confirm_state(
    modal: DashboardBillProviderWeightsModal,
    state: str,
) -> None:
    """Assert Confirm state from the captured Gherkin phrase.

    Args:
        modal: Provider weights modal.
        state: Captured state (``"enabled"`` or ``"disabled"`` — the regex
            alternation closes the domain).
    """
    assert_inquiry_confirm_enabled(modal, enabled=state == "enabled")
