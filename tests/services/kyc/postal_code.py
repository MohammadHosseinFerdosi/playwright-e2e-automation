"""Orchestrate postal-code inquiry: pin provider, inquire, restore weights."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.client import ApiClient
from tests.api.kyc.addresses.admin_settings_provider import (
    get_admin_kyc_settings_address_provider,
    post_admin_kyc_settings_address_provider,
)
from tests.api.kyc.addresses.models import (
    AddressProviderSetting,
    AddressProviderSettingsRequest,
    AddressSettingDetail,
    AddressSettingsBody,
)
from tests.api.kyc.addresses.postal_code import get_addresses_postal_code
from tests.services.api_assert import ensure_ok
from tests.services.assert_report import mask_pii
from tests.services.db.mongo_client import MongoDbClient
from tests.services.kyc.postal_code_secrets import PostalCodeSecrets

POSTAL_DB = "kyc_db"
POSTAL_COLLECTION = "address_detail_journals"
PROVIDER_SLOT_COUNT = 3
CACHE_POLL_TIMEOUT_S = 10.0
CACHE_POLL_INTERVAL_S = 0.5
JIBIT = 1
SITAAD = 2
PROVIDER_ENUMS = {"jibit": JIBIT, "sitaad": SITAAD}


class PostalJournal(BaseModel):
    """Postal-code journal fields used by inquiry and cache checks."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(alias="_id")
    fetched_from_cache: bool | None = Field(default=None, alias="fetchedFromCache")
    postal_code: str | None = Field(default=None, alias="postalCode")
    status: str | None = None
    provider: str | None = None
    result_status: str | None = Field(default=None, alias="resultStatus")
    audit: dict[str, Any] = Field(default_factory=dict)


@dataclass
class PostalCodeContext:
    """Per-scenario inquiry, settings, and journal envelopes."""

    secrets: PostalCodeSecrets
    provider: str | None = None
    last_inquiry: dict[str, Any] = field(default_factory=dict)
    last_settings: dict[str, Any] = field(default_factory=dict)
    first_journal: PostalJournal | None = None
    cached_journal: PostalJournal | None = None
    live_journal: PostalJournal | None = None

    def __repr__(self) -> str:
        return (
            "PostalCodeContext("
            f"provider={self.provider!r}, "
            f"last_status={self.last_inquiry.get('status_code')!r})"
        )

    def __str__(self) -> str:
        return repr(self)


class PostalCodeFlow:
    """Inquire postal codes; pin Jibit/Sitaad only when a provider is selected."""

    def __init__(
        self,
        client: ApiClient,
        mongo_client: MongoDbClient,
        secrets: PostalCodeSecrets,
    ) -> None:
        self._client = client
        self._mongo = mongo_client
        self.secrets = secrets
        self._snapshot: AddressSettingDetail | None = None

    def prepare(self) -> None:
        """Snapshot live weights and drop journals for the configured postal codes."""
        self.record_live_weights()
        self._clear_journals(self.secrets.postal_code)
        self._clear_journals(self.secrets.unknown_postal_code)
        self._clear_journals(self.secrets.invalid_postal_code)

    def record_live_weights(self) -> None:
        """GET and keep the live address-provider weights as the restore baseline."""
        self._snapshot = self._fetch_live_setting_detail()

    def captured_address_settings(self) -> AddressSettingDetail:
        """Return the live snapshot taken in ``prepare``."""
        snapshot = self._snapshot
        if snapshot is None:
            raise RuntimeError("address provider settings were not snapshotted")
        return snapshot

    def live_address_settings(self) -> AddressSettingDetail:
        """GET the current address provider settings."""
        return self._fetch_live_setting_detail()

    def teardown(self) -> None:
        """Restore live provider weights after pin or a settings POST."""
        if self._snapshot is None:
            return
        request = AddressProviderSettingsRequest.model_validate(
            {"setting_detail": self._snapshot}
        )
        ensure_ok(
            post_admin_kyc_settings_address_provider(self._client, request),
            context="restore address provider settings",
        )

    def pin_provider(self, ctx: PostalCodeContext, provider: str) -> None:
        """Pin one address provider to weight 1.0 and the others to 0."""
        enum = PROVIDER_ENUMS.get(provider)
        if enum is None:
            raise ValueError(f"unknown postal-code provider {provider!r}")
        ensure_ok(
            post_admin_kyc_settings_address_provider(
                self._client, _pin_provider_request(enum)
            ),
            context=f"pin address provider {provider}",
        )
        ctx.provider = provider

    def inquire_valid(self, ctx: PostalCodeContext) -> None:
        """GET the configured valid postal code (expect success)."""
        ctx.last_inquiry = ensure_ok(
            self._inquire(self.secrets.postal_code),
            context="postal-code inquiry",
        )
        ctx.live_journal = self._read_latest_journal(self.secrets.postal_code)

    def inquire_unknown(self, ctx: PostalCodeContext) -> None:
        """GET a well-formed postal code that has no address."""
        ctx.last_inquiry = self._inquire(self.secrets.unknown_postal_code)
        ctx.live_journal = self._read_latest_journal(self.secrets.unknown_postal_code)

    def inquire_invalid(self, ctx: PostalCodeContext) -> None:
        """GET a malformed postal code (expect 422, no journal)."""
        ctx.last_inquiry = self._inquire(self.secrets.invalid_postal_code)
        ctx.live_journal = self._read_latest_journal(self.secrets.invalid_postal_code)

    def inquire_valid_twice(self, ctx: PostalCodeContext) -> None:
        """GET twice; capture the live journal then wait for a cache hit."""
        self.inquire_valid(ctx)
        ctx.first_journal = ctx.live_journal
        ctx.last_inquiry = ensure_ok(
            self._inquire(self.secrets.postal_code),
            context="postal-code cache inquiry",
        )
        ctx.cached_journal = self._wait_until_cached_journal(self.secrets.postal_code)

    def submit_invalid_weights(self, ctx: PostalCodeContext, rule: str) -> None:
        """POST an invalid address-provider weight payload."""
        request = _weight_rule_request(rule)
        ctx.last_settings = post_admin_kyc_settings_address_provider(
            self._client, request
        )

    def _fetch_live_setting_detail(self) -> AddressSettingDetail:
        fetched = ensure_ok(
            get_admin_kyc_settings_address_provider(self._client),
            context="get address provider settings",
        )
        body = fetched.get("body")
        if isinstance(body, AddressSettingsBody):
            return body.setting_detail
        raise RuntimeError(
            mask_pii(f"address settings GET missing settingDetail: {body!r}")
        )

    def _clear_journals(self, postal_code: str) -> None:
        result = self._mongo.delete_many(
            POSTAL_DB,
            POSTAL_COLLECTION,
            {"postalCode": str(postal_code)},
        )
        if result.get("status_code") != 0:
            raise RuntimeError(mask_pii(f"clear postal-code journals failed: {result}"))

    def _inquire(self, postal_code: str) -> dict[str, Any]:
        return get_addresses_postal_code(
            self._client,
            self.secrets.requester_app_name,
            self.secrets.user_id,
            postal_code,
        )

    def _read_latest_journal(self, postal_code: str) -> PostalJournal | None:
        result = self._mongo.find_one(
            POSTAL_DB,
            POSTAL_COLLECTION,
            {"postalCode": str(postal_code)},
            sort=[("date", -1)],
        )
        if result.get("status_code") != 0:
            raise RuntimeError(mask_pii(f"read postal-code journal failed: {result}"))
        body = result.get("body")
        if not isinstance(body, dict) or not body.get("_id"):
            return None
        try:
            return PostalJournal.model_validate(body)
        except ValidationError as exc:
            raise RuntimeError(
                mask_pii(f"postal-code journal shape invalid: {exc}")
            ) from exc

    def _wait_until_cached_journal(self, postal_code: str) -> PostalJournal:
        deadline = time.monotonic() + CACHE_POLL_TIMEOUT_S
        last: PostalJournal | None = None
        while time.monotonic() < deadline:
            last = self._read_latest_journal(postal_code)
            if last is not None and last.fetched_from_cache is True:
                return last
            time.sleep(CACHE_POLL_INTERVAL_S)
        raise TimeoutError(
            mask_pii(
                f"postal-code journal was not served from cache within "
                f"{CACHE_POLL_TIMEOUT_S}s; last={last!r}"
            )
        )


def _pin_provider_request(provider_enum: int) -> AddressProviderSettingsRequest:
    rows = [
        AddressProviderSetting.model_validate(
            {
                "provider_name": index,
                "weight": 1.0 if index == provider_enum else 0.0,
            }
        )
        for index in range(PROVIDER_SLOT_COUNT)
    ]
    return AddressProviderSettingsRequest.model_validate(
        {"setting_detail": {"provider_settings": rows}}
    )


def _uniform_weights(weight: float) -> AddressProviderSettingsRequest:
    rows = [
        AddressProviderSetting.model_validate(
            {"provider_name": index, "weight": weight}
        )
        for index in range(PROVIDER_SLOT_COUNT)
    ]
    return AddressProviderSettingsRequest.model_validate(
        {"setting_detail": {"provider_settings": rows}}
    )


def _listed_weights(weights: tuple[float, float, float]) -> AddressProviderSettingsRequest:
    rows = [
        AddressProviderSetting.model_validate(
            {"provider_name": index, "weight": weights[index]}
        )
        for index in range(PROVIDER_SLOT_COUNT)
    ]
    return AddressProviderSettingsRequest.model_validate(
        {"setting_detail": {"provider_settings": rows}}
    )


def _weight_rule_request(rule: str) -> AddressProviderSettingsRequest:
    mapping = {
        "a weight above one": lambda: _uniform_weights(1.1),
        "a weight below one": lambda: _uniform_weights(0.1),
        "a sum below one": lambda: _listed_weights((0.01, 0.02, 0.03)),
        "a sum above one": lambda: _listed_weights((0.2, 0.7, 0.4)),
        "all weights zero": lambda: _uniform_weights(0.0),
    }
    builder = mapping.get(rule)
    if builder is None:
        raise ValueError(f"unknown address weight rule {rule!r}")
    return builder()
