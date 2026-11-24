"""Orchestrate identity registration inquiry: pin provider, inquire, restore."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.client import ApiClient
from tests.api.kyc.registration.admin_settings_provider import (
    post_admin_kyc_settings_registration_provider,
)
from tests.api.kyc.registration.admin_settings_provider_search import (
    post_admin_kyc_settings_registration_provider_search,
)
from tests.api.kyc.registration.identity_inquiry import (
    post_kyc_identity_registration_inquiry,
)
from tests.api.kyc.registration.models import (
    RegistrationInquiryRequest,
    RegistrationProviderSetting,
    RegistrationSettingsRequest,
    RegistrationSettingsSearchBody,
)
from tests.services.api_assert import ensure_ok
from tests.services.assert_report import mask_pii
from tests.services.db.mongo_client import MongoDbClient
from tests.services.kyc.registration_inquiry_secrets import (
    RegistrationInquirySecrets,
    RegistrationPerson,
)

REGISTRATION_DB = "kyc_db"
REGISTRATION_COLLECTION = "registration_inquiry_journals"
CACHE_POLL_TIMEOUT_S = 10.0
CACHE_POLL_INTERVAL_S = 0.5
INQUIRY_TYPES = {"basic": 0, "full": 10}
ENOVIN = 1
HAFEZSAMAN = 2
IT_SAAZ = 3
JIBIT_BASIC = 4
JIBIT_FULL = 5
BASIC_ENUMS = (ENOVIN, IT_SAAZ, JIBIT_BASIC)
PROVIDER_ENUMS = {
    ("basic", "jibit"): JIBIT_BASIC,
    ("full", "jibit"): JIBIT_FULL,
    ("full", "hafezsaman"): HAFEZSAMAN,
}


class RegistrationJournal(BaseModel):
    """Registration journal fields used by inquiry and cache checks."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(alias="_id")
    fetched_from_cache: bool | None = Field(default=None, alias="fetchedFromCache")
    national_code: str | None = Field(default=None, alias="nationalCode")
    birth_date: int | str | None = Field(default=None, alias="birthDate")
    status: str | None = None
    provider: str | None = None
    type: str | None = None
    gl_relay: bool | None = Field(default=None, alias="glRelay")
    strong_validation: bool | None = Field(default=None, alias="strongValidation")
    result_status: str | None = Field(default=None, alias="resultStatus")
    audit: dict[str, Any] = Field(default_factory=dict)


@dataclass
class RegistrationInquiryContext:
    """Per-scenario inquiry, settings, and journal envelopes."""

    secrets: CHANGE_ME
    inquiry_kind: str | None = None
    provider: str | None = None
    person: RegistrationPerson | None = None
    last_inquiry: dict[str, Any] = field(default_factory=dict)
    last_settings: dict[str, Any] = field(default_factory=dict)
    first_journal: RegistrationJournal | None = None
    cached_journal: RegistrationJournal | None = None
    live_journal: RegistrationJournal | None = None

    def __repr__(self) -> str:
        return (
            "RegistrationInquiryContext("
            f"kind={self.inquiry_kind!r}, provider={self.provider!r}, "
            f"last_status={self.last_inquiry.get('status_code')!r})"
        )

    def __str__(self) -> str:
        return repr(self)


class RegistrationInquiryFlow:
    """Inquire Sabt-Ahval identity; pin a provider only when Gherkin selects one."""

    def __init__(
        self,
        client: ApiClient,
        mongo_client: MongoDbClient,
        secrets: CHANGE_ME
    ) -> None:
        self._client = client
        self._mongo = mongo_client
        self.secrets = CHANGE_ME
        self._snapshot: RegistrationSettingsSearchBody | None = None

    def prepare(self) -> None:
        """Snapshot live weights and drop journals for configured national codes."""
        self.record_live_weights()
        for national_code in self.secrets.journal_national_codes():
            self._clear_journals(national_code)

    def record_live_weights(self) -> None:
        """GET and keep the live registration-provider weights as the restore baseline."""
        self._snapshot = self._fetch_live_settings()

    def captured_registration_settings(self) -> RegistrationSettingsSearchBody:
        """Return the live snapshot taken in ``prepare``."""
        snapshot = self._snapshot
        if snapshot is None:
            raise RuntimeError("registration provider settings were not snapshotted")
        return snapshot

    def live_registration_settings(self) -> RegistrationSettingsSearchBody:
        """Search the current registration provider settings."""
        return self._fetch_live_settings()

    def registration_weight_fingerprint(
        self, body: RegistrationSettingsSearchBody
    ) -> list[tuple[int, float, bool | None]]:
        """Comparable provider rows from a settings search body."""
        return sorted(
            (row.provider_name, float(row.weight), row.active)
            for row in _provider_rows(body)
        )

    def teardown(self) -> None:
        """Restore live provider weights."""
        if self._snapshot is None:
            return
        ensure_ok(
            post_admin_kyc_settings_registration_provider(
                self._client,
                _restore_request(self._snapshot, self.secrets.min_weight_auto_weighting),
            ),
            context="restore registration provider settings",
        )

    def pin_provider(self, ctx: RegistrationInquiryContext, provider: str, kind: str) -> None:
        """Pin one registration provider to weight 1.0 for the inquiry kind."""
        enum = PROVIDER_ENUMS.get((kind, provider))
        if enum is None:
            raise ValueError(f"unknown registration provider {kind}/{provider}")
        if self._snapshot is None:
            raise RuntimeError("registration provider settings were not snapshotted")
        ensure_ok(
            post_admin_kyc_settings_registration_provider(
                self._client,
                _pin_request(
                    self._snapshot, enum, self.secrets.min_weight_auto_weighting
                ),
            ),
            context=f"pin registration provider {kind}/{provider}",
        )
        ctx.inquiry_kind = kind
        ctx.provider = provider

    def inquire_live(
        self,
        ctx: RegistrationInquiryContext,
        kind: str,
        force: str,
        strong: str,
    ) -> None:
        """POST a live-person inquiry (expect HTTP 200)."""
        ctx.last_inquiry = ensure_ok(
            self._inquire(ctx, self.secrets.valid_person, kind, force, strong),
            context="registration inquiry",
        )
        ctx.live_journal = self._read_latest_journal(self.secrets.valid_person.national_code)

    def inquire_live_twice(
        self,
        ctx: RegistrationInquiryContext,
        kind: str,
        force: str,
        strong: str,
    ) -> None:
        """POST twice; capture the live journal then wait for a cache hit."""
        self.inquire_live(ctx, kind, force, strong)
        ctx.first_journal = ctx.live_journal
        ctx.last_inquiry = ensure_ok(
            self._inquire(ctx, self.secrets.valid_person, kind, force, strong),
            context="registration cache inquiry",
        )
        ctx.cached_journal = self._wait_until_cached_journal(
            self.secrets.valid_person.national_code
        )

    def inquire_dead(self, ctx: RegistrationInquiryContext, kind: str) -> None:
        """POST a deceased-person inquiry (expect HTTP 200)."""
        ctx.last_inquiry = ensure_ok(
            self._inquire(ctx, self.secrets.dead_person, kind, "true", "true"),
            context="registration dead-person inquiry",
        )
        ctx.live_journal = self._read_latest_journal(self.secrets.dead_person.national_code)

    def inquire_alternate(
        self,
        ctx: RegistrationInquiryContext,
        kind: str,
        force: str,
        strong: str,
    ) -> None:
        """POST the second live-person fixture (expect HTTP 200)."""
        person = self.secrets.alternate_person
        if person.national_code == self.secrets.valid_person.national_code:
            raise RuntimeError("alternate live person must differ from valid_person")
        ctx.last_inquiry = ensure_ok(
            self._inquire(ctx, person, kind, force, strong),
            context="registration alternate-person inquiry",
        )
        ctx.live_journal = self._read_latest_journal(person.national_code)

    def inquire_fault(self, ctx: RegistrationInquiryContext, kind: str, fault: str) -> None:
        """POST an unknown or malformed identity (expect a business error)."""
        national_code, birth_date = _identity_for_fault(fault, ctx.secrets)
        person = RegistrationPerson(national_code=national_code, birth_date=birth_date)
        ctx.last_inquiry = self._inquire(ctx, person, kind, "true", "true")
        ctx.live_journal = self._read_latest_journal(national_code)

    def submit_invalid_weights(self, ctx: RegistrationInquiryContext, rule: str) -> None:
        """POST an invalid registration-provider weight payload."""
        ctx.last_settings = post_admin_kyc_settings_registration_provider(
            self._client,
            _weight_rule_request(rule, self.secrets.min_weight_auto_weighting),
        )

    def _inquire(
        self,
        ctx: RegistrationInquiryContext,
        person: RegistrationPerson,
        kind: str,
        force: str,
        strong: str,
    ) -> dict[str, Any]:
        ctx.inquiry_kind = kind
        ctx.person = person
        request = RegistrationInquiryRequest.model_validate(
            {
                "national_code": person.national_code,
                "birth_date": person.birth_date,
                "force_inquiry": _as_bool(force),
                "inquiry_type": _inquiry_type(kind),
                "strong_validation": _as_bool(strong),
            }
        )
        return post_kyc_identity_registration_inquiry(
            self._client,
            self.secrets.requester_app_name,
            request,
        )

    def _fetch_live_settings(self) -> RegistrationSettingsSearchBody:
        searched = ensure_ok(
            post_admin_kyc_settings_registration_provider_search(self._client),
            context="search registration provider settings",
        )
        body = searched.get("body")
        if isinstance(body, RegistrationSettingsSearchBody):
            return body
        raise RuntimeError(
            mask_pii(f"registration settings search missing providers: {body!r}")
        )

    def _clear_journals(self, national_code: str) -> None:
        result = self._mongo.delete_many(
            REGISTRATION_DB,
            REGISTRATION_COLLECTION,
            {"nationalCode": str(national_code)},
        )
        if result.get("status_code") != 0:
            raise RuntimeError(
                mask_pii(f"clear registration journals failed: {result}")
            )

    def _read_latest_journal(self, national_code: str) -> RegistrationJournal | None:
        result = self._mongo.find_one(
            REGISTRATION_DB,
            REGISTRATION_COLLECTION,
            {"nationalCode": str(national_code)},
            sort=[("date", -1)],
        )
        if result.get("status_code") != 0:
            raise RuntimeError(mask_pii(f"read registration journal failed: {result}"))
        body = result.get("body")
        if not isinstance(body, dict) or not body.get("_id"):
            return None
        try:
            return RegistrationJournal.model_validate(body)
        except ValidationError as exc:
            raise RuntimeError(
                mask_pii(f"registration journal shape invalid: {exc}")
            ) from exc

    def _wait_until_cached_journal(self, national_code: str) -> RegistrationJournal:
        deadline = time.monotonic() + CACHE_POLL_TIMEOUT_S
        last: RegistrationJournal | None = None
        while time.monotonic() < deadline:
            last = self._read_latest_journal(national_code)
            if last is not None and last.fetched_from_cache is True:
                return last
            time.sleep(CACHE_POLL_INTERVAL_S)
        raise TimeoutError(
            mask_pii(
                f"registration journal was not served from cache within "
                f"{CACHE_POLL_TIMEOUT_S}s; last={last!r}"
            )
        )


def _as_bool(token: str) -> bool:
    mapping = {"true": True, "false": False}
    value = mapping.get(token)
    if value is None:
        raise ValueError(f"unknown boolean token {token!r}")
    return value


def _inquiry_type(kind: str) -> int:
    inquiry_type = INQUIRY_TYPES.get(kind)
    if inquiry_type is None:
        raise ValueError(f"unknown registration inquiry kind {kind!r}")
    return inquiry_type


def _weight_rows(
    weights: tuple[float, float, float], *, active: bool
) -> list[RegistrationProviderSetting]:
    return [
        RegistrationProviderSetting.model_validate(
            {
                "provider_name": BASIC_ENUMS[index],
                "priority": 1,
                "weight": weights[index],
                "active": active,
            }
        )
        for index in range(3)
    ]


def _weight_rule_request(rule: str, min_weight: float) -> RegistrationSettingsRequest:
    mapping = {
        "a weight above one": ((1.1, 1.1, 1.1), True),
        "a weight below one": ((0.1, 0.1, 0.1), True),
        "a sum below one": ((0.01, 0.005, 0.002), True),
        "a sum above one": ((0.5, 0.6, 0.43), True),
        "all weights zero": ((0.0, 0.0, 0.0), True),
        "all providers inactive": ((0.1, 0.1, 0.1), False),
    }
    payload = mapping.get(rule)
    if payload is None:
        raise ValueError(f"unknown registration weight rule {rule!r}")
    weights, active = payload
    return RegistrationSettingsRequest.model_validate(
        {
            "inquiry_type": 0,
            "provider_settings": _weight_rows(weights, active=active),
            "active_auto_weighting": False,
            "min_weight_auto_weighting": min_weight,
        }
    )


def _pin_request(
    snapshot: RegistrationSettingsSearchBody,
    provider_enum: int,
    min_weight: float,
) -> RegistrationSettingsRequest:
    rows = [
        RegistrationProviderSetting.model_validate(
            {
                "provider_name": row.provider_name,
                "priority": row.priority or 1,
                "weight": 1.0 if row.provider_name == provider_enum else 0.0,
                "active": row.provider_name == provider_enum,
            }
        )
        for row in _provider_rows(snapshot)
    ]
    return RegistrationSettingsRequest.model_validate(
        {
            "provider_settings": rows,
            "active_auto_weighting": False,
            "min_weight_auto_weighting": min_weight,
        }
    )


def _restore_request(
    snapshot: RegistrationSettingsSearchBody,
    fallback_min_weight: float,
) -> RegistrationSettingsRequest:
    min_weight = snapshot.min_weight_auto_weighting or fallback_min_weight
    return RegistrationSettingsRequest.model_validate(
        {
            "provider_settings": _provider_rows(snapshot),
            "active_auto_weighting": bool(snapshot.active_auto_weighting),
            "min_weight_auto_weighting": min_weight,
        }
    )


def _provider_rows(
    snapshot: RegistrationSettingsSearchBody,
) -> list[RegistrationProviderSetting]:
    rows = snapshot.providers
    if not rows:
        raise RuntimeError("registration settings search had no provider rows")
    return rows


def _identity_for_fault(
    fault: str, secrets: RegistrationInquirySecrets
) -> tuple[str, str]:
    mapping = {
        "an unknown national code": (
            secrets.invalid_person.national_code,
            secrets.valid_person.birth_date,
        ),
        "an unknown birth date": (
            secrets.valid_person.national_code,
            secrets.invalid_person.birth_date,
        ),
        "a malformed national code": (
            secrets.wrong_national_code,
            secrets.valid_person.birth_date,
        ),
    }
    identity = mapping.get(fault)
    if identity is None:
        raise ValueError(f"unknown registration identity fault {fault!r}")
    return identity
