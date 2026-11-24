"""Orchestrate basic Shahkar inquiry: pin provider when needed, inquire, restore."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.client import ApiClient
from tests.api.kyc.shahkar.admin_settings_provider import (
    post_admin_kyc_settings_shahkar_provider,
)
from tests.api.kyc.shahkar.admin_settings_provider_search import (
    post_admin_kyc_settings_shahkar_provider_search,
)
from tests.api.kyc.shahkar.cell_number_inquiry import post_kyc_cell_number_inquiry
from tests.api.kyc.shahkar.models import (
    CellNumberInquiryRequest,
    ShahkarProviderSetting,
    ShahkarProviderSettingsRequest,
    ShahkarSettingDetail,
    ShahkarSettingsSearchBody,
)
from tests.services.api_assert import ensure_ok
from tests.services.assert_report import mask_pii
from tests.services.db.mongo_client import MongoDbClient
from tests.services.kyc.shahkar_secrets import ShahkarSecrets

SHAHKAR_DB = "kyc_db"
SHAHKAR_COLLECTION = "shahkar_request_journals"
PROVIDER_SLOT_COUNT = 8
MIN_WEIGHT_AUTO_WEIGHTING = 0.05
SHAPARAK_PROVIDER = 5
CACHE_POLL_TIMEOUT_S = 10.0
CACHE_POLL_INTERVAL_S = 0.5
INVALID_NATIONAL_CODE_STUB = "000"
INVALID_CELL_NUMBER_STUB = "0912"
JOURNAL_PROJECTION = {"_id": 1, "fetchedFromCache": 1}


class ShahkarJournal(BaseModel):
    """Projected Shahkar journal fields used by the cache scenario."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str = Field(alias="_id")
    fetched_from_cache: bool | None = Field(default=None, alias="fetchedFromCache")


@dataclass
class ShahkarContext:
    """Per-scenario inquiry and journal envelopes."""

    secrets: ShahkarSecrets
    national_code: str | None = None
    cell_number: str | None = None
    last_inquiry: dict[str, Any] = field(default_factory=dict)
    first_journal: ShahkarJournal | None = None
    cached_journal: ShahkarJournal | None = None

    def __repr__(self) -> str:
        return (
            "ShahkarContext("
            f"secrets={self.secrets!r}, "
            f"has_national_code={self.national_code is not None}, "
            f"has_cell_number={self.cell_number is not None}, "
            f"last_status={self.last_inquiry.get('status_code')!r}, "
            f"first_journal={self.first_journal!r}, "
            f"cached_journal={self.cached_journal!r})"
        )

    def __str__(self) -> str:
        return repr(self)


class ShahkarFlow:
    """Inquire Shahkar; pin Shaparak only when a real inquiry needs a provider."""

    def __init__(
        self,
        client: ApiClient,
        mongo_client: MongoDbClient,
        secrets: ShahkarSecrets,
    ) -> None:
        self._client = client
        self._mongo = mongo_client
        self.secrets = secrets
        self._snapshot: ShahkarSettingDetail | None = None
        self._pinned = False

    def prepare(self) -> None:
        """Drop journals for this national code. Do not pin until Given selects a cell."""
        self._snapshot = None
        self._pinned = False
        self._clear_journals()

    def teardown(self) -> None:
        """Restore live provider weights when this scenario pinned Shaparak."""
        if not self._pinned or self._snapshot is None:
            return
        request = ShahkarProviderSettingsRequest.model_validate({"setting_detail": self._snapshot})
        ensure_ok(
            post_admin_kyc_settings_shahkar_provider(self._client, request),
            context="restore Shahkar provider settings",
        )

    def use_national_identity(self, ctx: ShahkarContext) -> None:
        """Bind the configured national identity for invalid-payload inquiries."""
        ctx.national_code = self.secrets.national_code

    def use_matching_cell(self, ctx: ShahkarContext) -> None:
        """Select the cell number that belongs to the national identity."""
        self._ensure_shaparak()
        ctx.national_code = self.secrets.national_code
        ctx.cell_number = self.secrets.matching_cell_number

    def use_mismatch_cell(self, ctx: ShahkarContext) -> None:
        """Select a cell number that does not belong to the national identity."""
        self._ensure_shaparak()
        ctx.national_code = self.secrets.national_code
        ctx.cell_number = self.secrets.mismatch_cell_number

    def store_inquiry(self, ctx: ShahkarContext) -> None:
        """POST one Shahkar inquiry for the cell selected in Given."""
        if ctx.national_code is None or ctx.cell_number is None:
            raise RuntimeError("Shahkar identity was not selected")
        ctx.last_inquiry = ensure_ok(
            self._inquire(ctx.national_code, ctx.cell_number),
            context="Shahkar cell-number inquiry",
        )

    def store_inquiry_twice(self, ctx: ShahkarContext) -> None:
        """POST twice; capture the live journal then wait for a cache hit."""
        self.store_inquiry(ctx)
        cell_number = ctx.cell_number
        if cell_number is None:
            raise RuntimeError("Shahkar identity was not selected")
        ctx.first_journal = self._read_latest_journal(cell_number)
        self.store_inquiry(ctx)
        ctx.cached_journal = self._wait_until_cached_journal(cell_number)

    def store_fault_inquiry(self, ctx: ShahkarContext, fault: str) -> None:
        """POST an incomplete or invalid identity inquiry (expect a 422)."""
        national_code, cell_number = _identity_for_fault(fault, ctx)
        ctx.last_inquiry = self._inquire(national_code, cell_number)

    def _ensure_shaparak(self) -> None:
        if self._pinned:
            return
        self._snapshot = self._fetch_live_setting_detail()
        ensure_ok(
            post_admin_kyc_settings_shahkar_provider(self._client, _pin_shaparak_request()),
            context="pin Shahkar provider",
        )
        self._pinned = True

    def _fetch_live_setting_detail(self) -> ShahkarSettingDetail:
        searched = ensure_ok(
            post_admin_kyc_settings_shahkar_provider_search(self._client),
            context="search Shahkar provider settings",
        )
        body = searched.get("body")
        if isinstance(body, ShahkarSettingsSearchBody):
            return body.setting_detail
        raise RuntimeError(mask_pii(f"Shahkar settings search missing settingDetail: {body!r}"))

    def _clear_journals(self) -> None:
        result = self._mongo.delete_many(
            SHAHKAR_DB,
            SHAHKAR_COLLECTION,
            {"user.nationalCode": str(self.secrets.national_code)},
        )
        if result.get("status_code") != 0:
            raise RuntimeError(mask_pii(f"clear Shahkar journals failed: {result}"))

    def _inquire(self, national_code: str | None, cell_number: str | None) -> dict[str, Any]:
        payload: dict[str, str] = {}
        if national_code is not None:
            payload["national_code"] = national_code
        if cell_number is not None:
            payload["cell_number"] = cell_number
        request = CellNumberInquiryRequest.model_validate(payload)
        return post_kyc_cell_number_inquiry(
            self._client,
            self.secrets.requester_app_name,
            request,
        )

    def _read_latest_journal(self, cell_number: str) -> ShahkarJournal | None:
        result = self._mongo.find_one(
            SHAHKAR_DB,
            SHAHKAR_COLLECTION,
            {"user.cellNumber": str(cell_number)},
            sort=[("_id", -1)],
            projection=JOURNAL_PROJECTION,
        )
        if result.get("status_code") != 0:
            raise RuntimeError(mask_pii(f"read Shahkar journal failed: {result}"))
        body = result.get("body")
        if not isinstance(body, dict) or not body.get("_id"):
            return None
        try:
            return ShahkarJournal.model_validate(body)
        except ValidationError as exc:
            raise RuntimeError(mask_pii(f"Shahkar journal shape invalid: {exc}")) from exc

    def _wait_until_cached_journal(self, cell_number: str) -> ShahkarJournal:
        deadline = time.monotonic() + CACHE_POLL_TIMEOUT_S
        last: ShahkarJournal | None = None
        while time.monotonic() < deadline:
            last = self._read_latest_journal(cell_number)
            if last is not None and last.fetched_from_cache is True:
                return last
            time.sleep(CACHE_POLL_INTERVAL_S)
        raise TimeoutError(
            mask_pii(
                f"Shahkar journal was not served from cache within "
                f"{CACHE_POLL_TIMEOUT_S}s; last={last!r}"
            )
        )


def _pin_shaparak_request() -> ShahkarProviderSettingsRequest:
    rows = [
        ShahkarProviderSetting.model_validate(
            {
                "provider_name": index,
                "weight": 1.0 if index == SHAPARAK_PROVIDER else 0.0,
                "active": index == SHAPARAK_PROVIDER,
            }
        )
        for index in range(PROVIDER_SLOT_COUNT)
    ]
    return ShahkarProviderSettingsRequest.model_validate(
        {
            "setting_detail": {
                "provider_settings": rows,
                "active_auto_weighting": False,
                "min_weight_auto_weighting": MIN_WEIGHT_AUTO_WEIGHTING,
            }
        }
    )


def _identity_for_fault(fault: str, ctx: ShahkarContext) -> tuple[str | None, str | None]:
    if ctx.national_code is None:
        raise RuntimeError("Shahkar national identity was not selected")
    mapping: dict[str, tuple[str | None, str | None]] = {
        "a missing national code": (None, ctx.secrets.matching_cell_number),
        "a missing cell number": (ctx.national_code, None),
        "an invalid national code": (
            INVALID_NATIONAL_CODE_STUB,
            ctx.secrets.matching_cell_number,
        ),
        "an invalid cell number": (ctx.national_code, INVALID_CELL_NUMBER_STUB),
    }
    identity = mapping.get(fault)
    if identity is None:
        raise ValueError(f"unknown Shahkar identity fault {fault!r}")
    return identity
