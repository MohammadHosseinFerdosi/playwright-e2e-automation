"""Dashboard Super App topup / IPKG UI orchestration and asserts."""

from __future__ import annotations

from collections.abc import Callable

from tests.services.dashboard_weight_ui import (
    assert_confirm_enabled,
    assert_weights_from_raw,
    assert_weights_match_noted,
    set_weights_from_raw,
)
from tests.ui.labels.dashboard import (
    DISTRIBUTION_TITLE_PRODUCT_KEYS,
    OPERATOR_KEYS,
    OPERATOR_TILES_INTERNET,
    OPERATOR_TILES_TOPUP,
    PRODUCT_KEYS,
    PROVIDER_KEYS,
    resolve_label,
)
from tests.ui.pages.dashboard.operator_picker_modal import DashboardOperatorPickerModal
from tests.ui.pages.dashboard.super_app_page import DashboardSuperAppPage
from tests.ui.pages.dashboard.topup_provider_weights_modal import (
    DashboardTopupProviderWeightsModal,
)

_PRODUCT_OPENERS: dict[str, Callable[[DashboardSuperAppPage], None]] = {
    "internet package": DashboardSuperAppPage.open_internet_package,
    "topup": DashboardSuperAppPage.open_topup,
}

_OPERATOR_TILES: dict[str, tuple[str, ...]] = {
    "internet package": OPERATOR_TILES_INTERNET,
    "topup": OPERATOR_TILES_TOPUP,
}

OPEN_FROM_DASHBOARD_STEP = r"^the staff opens (?P<tile>[A-Za-z0-9 -]+) from the dashboard$"
OPEN_OPERATOR_DISTRIBUTION_STEP = (
    r"^the staff opens the (?P<operator>[A-Za-z0-9]+) operator distribution$"
)
SET_OPERATOR_WEIGHTS_STEP = r"^the staff sets operator distribution weights to (?P<raw>[\d, and]+)$"
OPERATOR_PICKER_SHOWN_STEP = (
    r"^the operator picker is shown for (?P<product>internet package|topup)$"
)
OPERATOR_PICKER_LISTS_STEP = (
    r"^the operator picker lists the (?P<product>internet package|topup) operators$"
)
OPERATOR_DISTRIBUTION_SHOWN_STEP = (
    r"^the operator distribution is shown for (?P<title_key>[A-Za-z0-9 ]+)$"
)
OPERATOR_PROVIDERS_SHOWN_STEP = (
    r"^the operator distribution shows providers "
    r"(?P<a>[A-Za-z0-9 ]+), (?P<b>[A-Za-z0-9 ]+), (?P<c>[A-Za-z0-9 ]+) "
    r"and (?P<d>[A-Za-z0-9 ]+)$"
)
OPERATOR_WEIGHTS_ARE_STEP = r"^the operator distribution weights are (?P<raw>[\d, and]+)$"
OPERATOR_CONFIRM_STATE_STEP = r"^operator distribution confirm is (?P<state>enabled|disabled)$"
MCI_ADMIN_WEIGHTS_STEP = r"^the mci internet package admin weights are (?P<raw>[\d, and]+)$"

_DashboardOpen = Callable[
    [
        DashboardSuperAppPage,
        DashboardOperatorPickerModal,
        DashboardTopupProviderWeightsModal,
    ],
    None,
]


def _open_bill_inquiry_tile(
    super_app: DashboardSuperAppPage,
    _picker: DashboardOperatorPickerModal,
    _weights: DashboardTopupProviderWeightsModal,
) -> None:
    super_app.open_bill_inquiry()


def _open_product_tile(
    product: str,
) -> _DashboardOpen:
    def _run(
        super_app: DashboardSuperAppPage,
        picker: DashboardOperatorPickerModal,
        weights: DashboardTopupProviderWeightsModal,
    ) -> None:
        open_product_picker(product, super_app, picker, weights)

    return _run


_DASHBOARD_TILES: dict[str, _DashboardOpen] = {
    "bill inquiry": _open_bill_inquiry_tile,
    "internet package": _open_product_tile("internet package"),
    "topup": _open_product_tile("topup"),
}


def known_dashboard_tiles() -> list[str]:
    """Registered dashboard tile phrases, for the regex unit test to keep in sync."""
    return sorted(_DASHBOARD_TILES)


def open_from_dashboard(
    tile: str,
    super_app: DashboardSuperAppPage,
    picker: DashboardOperatorPickerModal,
    weights: DashboardTopupProviderWeightsModal,
) -> None:
    """Open one Super App tile from the captured Gherkin phrase.

    Args:
        tile: Captured tail from ``OPEN_FROM_DASHBOARD_STEP``.
        super_app: Super App settings page object.
        picker: Operator picker (used by topup / internet package).
        weights: Provider-weights modal (used by topup / internet package).

    Raises:
        KeyError: If the tile has no registered opener.
    """
    opener = _DASHBOARD_TILES.get(tile)
    if opener is None:
        raise KeyError(f"No dashboard tile for {tile!r}; known: {known_dashboard_tiles()}")
    opener(super_app, picker, weights)


def open_product_picker(
    product: str,
    super_app: DashboardSuperAppPage,
    picker: DashboardOperatorPickerModal,
    weights: DashboardTopupProviderWeightsModal,
) -> None:
    """Open internet package or topup from the dashboard (operator picker)."""
    if picker.is_open():
        return
    if weights.is_open():
        weights.click_back()
        return
    key = product.strip().lower()
    try:
        opener = _PRODUCT_OPENERS[key]
    except KeyError as exc:
        raise KeyError(f"Unknown product {product!r}") from exc
    opener(super_app)
    picker.should_be_open(resolve_label(PRODUCT_KEYS, key, kind="product"))


def open_operator_distribution(
    operator: str,
    picker: DashboardOperatorPickerModal,
    weights: DashboardTopupProviderWeightsModal,
) -> None:
    """Open an operator's provider distribution, or stay if already open."""
    if weights.is_open():
        return
    label = resolve_label(OPERATOR_KEYS, operator, kind="operator")
    picker.open_operator(label)


def set_operator_weights(modal: DashboardTopupProviderWeightsModal, raw: str) -> None:
    """Set operator distribution weights from a Gherkin list."""
    set_weights_from_raw(modal, raw)


def assert_operator_picker_shown(
    picker: DashboardOperatorPickerModal,
    product: str,
) -> None:
    """Assert the operator picker title for a product key."""
    title = resolve_label(PRODUCT_KEYS, product, kind="product")
    picker.should_be_open(title)


def assert_operator_tiles(
    picker: DashboardOperatorPickerModal,
    product: str,
) -> None:
    """Assert the operator tiles listed for a product key."""
    key = product.strip().lower()
    try:
        tiles = _OPERATOR_TILES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown product {product!r}") from exc
    picker.should_list_operators(tiles)


def assert_operator_distribution_shown(
    modal: DashboardTopupProviderWeightsModal,
    title_key: str,
) -> None:
    """Assert the distribution dialog title for a product+operator key."""
    title = resolve_label(DISTRIBUTION_TITLE_PRODUCT_KEYS, title_key, kind="distribution title")
    modal.should_be_open(title)


def assert_operator_providers(
    modal: DashboardTopupProviderWeightsModal,
    a: str,
    b: str,
    c: str,
    d: str,
) -> None:
    """Assert the four provider labels shown in the distribution dialog."""
    modal.should_show_providers(
        resolve_label(PROVIDER_KEYS, a, kind="provider"),
        resolve_label(PROVIDER_KEYS, b, kind="provider"),
        resolve_label(PROVIDER_KEYS, c, kind="provider"),
        resolve_label(PROVIDER_KEYS, d, kind="provider"),
    )


def assert_operator_weights(modal: DashboardTopupProviderWeightsModal, raw: str) -> None:
    """Assert UI operator distribution weights match a Gherkin list."""
    assert_weights_from_raw(modal, raw, label="Operator distribution weights")


def assert_operator_weights_match_noted(
    modal: DashboardTopupProviderWeightsModal,
    noted: list[int] | None,
) -> None:
    """Assert UI weights match a previously noted snapshot."""
    assert_weights_match_noted(
        modal,
        noted,
        label="Operator distribution weights match noted values",
        what="operator distribution weights",
    )


def assert_operator_confirm_enabled(
    modal: DashboardTopupProviderWeightsModal,
    *,
    enabled: bool,
) -> None:
    """Assert operator distribution Confirm is enabled or disabled."""
    label = (
        "Operator distribution confirm is enabled"
        if enabled
        else "Operator distribution confirm is disabled"
    )
    assert_confirm_enabled(modal, enabled=enabled, label=label)


def assert_operator_confirm_state(
    modal: DashboardTopupProviderWeightsModal,
    state: str,
) -> None:
    """Assert Confirm state from the captured Gherkin phrase.

    Args:
        modal: Operator provider weights modal.
        state: Captured state (``"enabled"`` or ``"disabled"``).
    """
    assert_operator_confirm_enabled(modal, enabled=state == "enabled")
