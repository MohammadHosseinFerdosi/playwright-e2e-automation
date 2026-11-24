"""Admin API orchestration for bill inquiry provider distributions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.api.bill_mng.admin.configs import (
    AdminBillConfigsBody,
    InquiryDistribution,
    get_admin_bills_configs,
    put_admin_bills_config_for_api_type,
)
from tests.api.bill_mng.bill_types import BillType
from tests.api.bill_mng.bills.result import result_title_from_body
from tests.api.client import ApiClient
from tests.config.settings import Settings
from tests.services.api_assert import ensure_ok
from tests.services.assert_report import AssertionReport, attach_api_result
from tests.services.dashboard_admin import require_dashboard_username
from tests.services.provider_weights import (
    assert_weights_equal,
    parse_weights,
    require_noted,
    weights_in_order,
)

# UI order for electricity: Finnotech (0), Ghabzino (1).
ELECTRICITY_PROVIDERS: tuple[int, ...] = (0, 1)


def _electricity_distributions_from_weights(
    weights: Sequence[int],
) -> list[dict[str, Any]]:
    if len(weights) != len(ELECTRICITY_PROVIDERS):
        raise ValueError(
            f"Expected {len(ELECTRICITY_PROVIDERS)} electricity weights, got {weights!r}"
        )
    return [
        {"provider": provider, "weight": float(weight)}
        for provider, weight in zip(ELECTRICITY_PROVIDERS, weights, strict=True)
    ]


class BillInquiryAdminSession:
    """Per-scenario note/restore + PUT tracking for electricity inquiry configs."""

    def __init__(self, client: ApiClient, settings: Settings) -> None:
        self._client = client
        self._user_id = require_dashboard_username(settings)
        self.ui_values: list[int] | None = None
        self.admin_distributions: list[InquiryDistribution] | None = None
        self.bill_type: BillType | None = None
        self.last_put: dict[str, Any] = {}
        self._admin_restored = False

    def note_ui_weights(self, values: list[int]) -> None:
        """Store UI modal weight snapshot for later comparison."""
        self.ui_values = values

    def note_electricity_distributions(self) -> None:
        """Snapshot current electricity admin distributions (restored on teardown)."""
        self.bill_type = BillType.ELECTRICITY
        self.admin_distributions = self.fetch_electricity_distributions()
        self._admin_restored = False

    def fetch_electricity_distributions(self) -> list[InquiryDistribution]:
        """GET admin configs and return electricity inquiry distributions."""
        result = get_admin_bills_configs(self._client, self._user_id)
        ensure_ok(result, context="GET /admin/bills/configs")
        body = result["body"]
        if not isinstance(body, AdminBillConfigsBody):
            raise TypeError(f"expected AdminBillConfigsBody, got {type(body).__name__}")
        return list(body.config_for(BillType.ELECTRICITY).inquiry_distributions)

    def set_electricity_weights(self, raw: str) -> None:
        """PUT electricity inquiry weights from a Gherkin weight list."""
        result = put_admin_bills_config_for_api_type(
            self._client,
            self._user_id,
            BillType.ELECTRICITY,
            inquiry_distributions=_electricity_distributions_from_weights(parse_weights(raw)),
        )
        self.last_put = result
        attach_api_result("Admin bills config PUT", result)

    def restore_noted_distributions(self) -> None:
        """PUT the noted distributions back and mark restored."""
        distributions = require_noted(
            self.admin_distributions, what="electricity admin distributions"
        )
        bill_type = require_noted(self.bill_type, what="bill type for admin restore")
        result = put_admin_bills_config_for_api_type(
            self._client,
            self._user_id,
            bill_type,
            inquiry_distributions=distributions,
        )
        ensure_ok(result, context="PUT admin bills config restore")
        self._admin_restored = True

    def restore_on_teardown(self) -> None:
        """Idempotent finalizer — skip when already restored or nothing noted."""
        if self._admin_restored or self.admin_distributions is None or self.bill_type is None:
            return
        put_admin_bills_config_for_api_type(
            self._client,
            self._user_id,
            self.bill_type,
            inquiry_distributions=self.admin_distributions,
        )

    def assert_put_succeeded(self) -> None:
        """Assert last admin PUT returned HTTP 200."""
        report = AssertionReport("Admin bills config update succeeds")
        report.equals("HTTP status", actual=self.last_put.get("status_code"), expected=200)
        report.attach_json("response body", self.last_put.get("body"))
        report.assert_all()

    def assert_put_rejected(self, result_title: str) -> None:
        """Assert last admin PUT was rejected with the expected result title."""
        attach_api_result("Admin bills config rejection", self.last_put)
        report = AssertionReport("Admin bills config rejection")
        body = self.last_put.get("body")
        report.equals("HTTP status", actual=self.last_put.get("status_code"), expected=422)
        report.equals(
            "result.title",
            actual=result_title_from_body(body),
            expected=result_title.strip(),
        )
        report.attach_json("response body", body).assert_all()

    def assert_electricity_weights(self, raw: str) -> None:
        """Assert live admin electricity weights match ``raw``."""
        actual = weights_in_order(
            self.fetch_electricity_distributions(),
            providers=ELECTRICITY_PROVIDERS,
        )
        assert_weights_equal("Admin electricity inquiry weights", actual, parse_weights(raw))

    def assert_electricity_matches_noted(self) -> None:
        """Assert live admin electricity weights match the noted snapshot."""
        expected = require_noted(self.admin_distributions, what="electricity admin distributions")
        actual = self.fetch_electricity_distributions()
        assert_weights_equal(
            "Restored admin electricity inquiry weights",
            weights_in_order(actual, providers=ELECTRICITY_PROVIDERS),
            weights_in_order(expected, providers=ELECTRICITY_PROVIDERS),
        )


def bind_bill_inquiry_admin(
    request: pytest.FixtureRequest,
    client: ApiClient,
    settings: Settings,
) -> BillInquiryAdminSession:
    """Create a session and register teardown restore."""
    session = BillInquiryAdminSession(client, settings)
    request.addfinalizer(session.restore_on_teardown)
    return session
