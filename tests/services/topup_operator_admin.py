"""Admin API orchestration for topup / IPKG operator provider settings."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.api.client import ApiClient
from tests.api.top_ups.admin.operator_settings import (
    OperatorConfig,
    OperatorId,
    OperatorSettingsBody,
    TopUpProduct,
    get_operator_settings,
    put_operator_settings,
)
from tests.config.settings import Settings
from tests.services.api_assert import ensure_ok
from tests.services.dashboard_admin import require_dashboard_username
from tests.services.provider_weights import (
    assert_enabled_matches_weights,
    assert_weights_equal,
    parse_weights,
    require_noted,
    weights_in_order,
)
from tests.ui.labels.dashboard import MCI_INTERNET_PROVIDERS


def _mci_config(configs: Sequence[OperatorConfig]) -> OperatorConfig:
    by_operator = {item.operator: item for item in configs}
    try:
        return by_operator[int(OperatorId.MCI)]
    except KeyError as exc:
        raise LookupError("No MCI config in noted operator configs") from exc


class TopupOperatorAdminSession:
    """Per-scenario note/restore for internet-package operator admin configs."""

    def __init__(
        self,
        client: ApiClient,
        settings: Settings,
        access_token: CHANGE_ME
    ) -> None:
        self._client = client
        self._user_id = require_dashboard_username(settings)
        self._access_token = CHANGE_ME
        self.ui_values: list[int] | None = None
        self.admin_configs: list[OperatorConfig] | None = None
        self.product: TopUpProduct | None = None
        self._admin_restored = False

    def note_ui_weights(self, values: list[int]) -> None:
        """Store UI modal weight snapshot for later comparison."""
        self.ui_values = values

    def note_internet_configs(self) -> None:
        """Snapshot current internet-package admin operator configs."""
        body = self.fetch_internet_settings()
        self.product = TopUpProduct.INTERNET
        self.admin_configs = body.configs
        self._admin_restored = False

    def fetch_internet_settings(self) -> OperatorSettingsBody:
        """GET internet operator settings and return the typed body."""
        result = get_operator_settings(
            self._client,
            self._user_id,
            TopUpProduct.INTERNET,
            access_token=CHANGE_ME
        )
        ensure_ok(result, context="GET internet operator settings")
        body = result["body"]
        if not isinstance(body, OperatorSettingsBody):
            raise TypeError(f"expected OperatorSettingsBody, got {type(body).__name__}")
        return body

    def restore_noted_configs(self) -> None:
        """PUT the noted configs back and mark restored."""
        configs = require_noted(self.admin_configs, what="internet package admin configs")
        result = put_operator_settings(
            self._client,
            self._user_id,
            TopUpProduct.INTERNET,
            configs,
            access_token=CHANGE_ME
        )
        ensure_ok(result, context="PUT internet operator settings (restore)")
        self._admin_restored = True

    def restore_on_teardown(self) -> None:
        """Idempotent finalizer — skip when already restored or nothing noted."""
        if self._admin_restored or not self.admin_configs or self.product is None:
            return
        put_operator_settings(
            self._client,
            self._user_id,
            self.product,
            self.admin_configs,
            access_token=CHANGE_ME
        )

    def assert_mci_internet_weights(self, raw: str) -> None:
        """Assert live MCI internet admin weights match ``raw``."""
        body = self.fetch_internet_settings()
        actual = weights_in_order(
            body.config_for(OperatorId.MCI).distributions,
            providers=MCI_INTERNET_PROVIDERS,
        )
        assert_weights_equal("MCI internet package admin weights", actual, parse_weights(raw))

    def assert_mci_enabled_matches_weights(self) -> None:
        """Assert MCI distribution ``enabled`` flags match weights."""
        body = self.fetch_internet_settings()
        assert_enabled_matches_weights(body.config_for(OperatorId.MCI).distributions)

    def assert_mci_configs_match_noted(self) -> None:
        """Assert MCI weights match the noted snapshot and enabled flags agree."""
        expected_configs = require_noted(self.admin_configs, what="admin configs")
        body = self.fetch_internet_settings()
        expected = _mci_config(expected_configs)
        actual = body.config_for(OperatorId.MCI)
        assert_weights_equal(
            "MCI internet package admin configs match noted values",
            weights_in_order(actual.distributions, providers=MCI_INTERNET_PROVIDERS),
            weights_in_order(expected.distributions, providers=MCI_INTERNET_PROVIDERS),
        )
        assert_enabled_matches_weights(actual.distributions)


def bind_topup_operator_admin(
    request: pytest.FixtureRequest,
    client: ApiClient,
    settings: Settings,
    access_token: CHANGE_ME
) -> TopupOperatorAdminSession:
    """Create a session and register teardown restore."""
    session = TopupOperatorAdminSession(client, settings, access_token)
    request.addfinalizer(session.restore_on_teardown)
    return session
