"""Promissory-note orchestration (UAT APIs + Mongo seed/cleanup)."""

from __future__ import annotations

import logging
import secrets as py_secrets
import time
from copy import deepcopy
from dataclasses import dataclass, field
from functools import partial
from typing import Any

import httpx
from bson import Int64

from tests.api.client import ApiClient
from tests.api.kyc.paths import promissory_requester_headers
from tests.api.kyc.promissory_notes.admin_cancel import (
    post_admin_promissory_notes_cancel,
)
from tests.api.kyc.promissory_notes.admin_notify_generated_batch import (
    post_admin_promissory_notes_notify_generated_batch,
)
from tests.api.kyc.promissory_notes.admin_provider_success_rate_search import (
    post_admin_promissory_notes_provider_success_rate_search,
)
from tests.api.kyc.promissory_notes.admin_settings_provider_get import (
    get_admin_promissory_notes_settings_provider,
)
from tests.api.kyc.promissory_notes.admin_settings_provider_post import (
    post_admin_promissory_notes_settings_provider,
)
from tests.api.kyc.promissory_notes.admin_settings_search import (
    post_admin_promissory_notes_settings_search,
)
from tests.api.kyc.promissory_notes.admin_status_revert import (
    post_admin_promissory_notes_status_revert,
)
from tests.api.kyc.promissory_notes.admin_success_rate_stat import (
    get_admin_promissory_notes_success_rate_stat,
)
from tests.api.kyc.promissory_notes.init import post_promissory_notes_init
from tests.api.kyc.promissory_notes.init_raw import post_promissory_notes_init_raw
from tests.api.kyc.promissory_notes.inquiry import post_promissory_notes_inquiry
from tests.api.kyc.promissory_notes.models import (
    InitRequest,
    ProviderSettingsBody,
    ProviderSettingsRequest,
)
from tests.api.kyc.promissory_notes.payments_init import (
    post_promissory_notes_payments_init,
)
from tests.api.kyc.promissory_notes.refund import post_promissory_notes_refund
from tests.api.kyc.promissory_notes.route import post_promissory_notes_route
from tests.api.kyc.promissory_notes.route_raw import post_promissory_notes_route_raw
from tests.api.kyc.promissory_notes.seal import post_promissory_notes_seal
from tests.api.kyc.promissory_notes.sign_request_init import (
    post_promissory_notes_sign_request_init,
)
from tests.api.kyc.promissory_notes.user_cancel import post_promissory_notes_user_cancel
from tests.config.constants import (
    ANDROID_AGENT,
    PLATFORM_VERSION_2023,
    TEST_CALLBACK_URL,
    TEST_X_FORWARDED_FOR,
)
from tests.config.settings import Settings
from tests.services.api_assert import ensure_ok
from tests.services.assert_report import assert_truthy
from tests.services.db.mongo_client import MongoDbClient
from tests.services.kyc.promissory_concurrent import fire_concurrent_requests
from tests.services.kyc.promissory_note_secrets import (
    PromissoryNoteSecrets,
    PromissoryOwnerSecrets,
)

logger = logging.getLogger(__name__)

RECIPIENT_TEJARAT = 0
RECIPIENT_SADERAT = 5
PROVIDER_KUKNOS = 1
PROVIDER_SADERAT = 5
INVALID_RECIPIENT = 999

STATUS_PROVIDER_SELECTED = -10
STATUS_ROUTED = STATUS_PROVIDER_SELECTED
STATUS_GENERATED = 20
STATUS_PAID = 30
STATUS_SIGNED = 40
STATUS_SEALED = 50
STATUS_CONFIRMED = 60
STATUS_REJECTED = 70
STATUS_CANCELED = 80
RESTORE_POLL_TIMEOUT_S = 45.0
RESTORE_POLL_INTERVAL_S = 5.0
FORCE_STATUS_TRIES = 6
FORCE_STATUS_INTERVAL_S = 1.0
SETTINGS_COLLECTION = "settings"
HTTP_OK = 200

STATUS_BY_NAME = {
    "paid": STATUS_PAID,
    "signed": STATUS_SIGNED,
    "sealed": STATUS_SEALED,
    "confirmed": STATUS_CONFIRMED,
}

INJECTED_FIELDS = {
    "status": STATUS_CONFIRMED,
    "treasuryId": "INJECTED_TREASURY",
    "sealedPromissoryNoteFileId": "INJECTED_FILE",
    "signedPromissoryNoteFileId": "INJECTED_FILE",
    "sourcePromissoryNoteFileId": "INJECTED_FILE",
    "businessId": "INJECTED_BUSINESS",
    "initiator": "INJECTED_INITIATOR",
    "version": 999999,
}

PROVIDER_COUNT = 6
RACE_REQUESTS = 8
RACE_WORKERS = 8
_ONE_YEAR_MS = 31_536_000_000
_LONG_DESCRIPTION = "x" * 5000
_TEJARAT_DESCRIPTION = "automation test note"
_NOTE_READ_FIELDS = {
    "status": 1,
    "provider": 1,
    "recipientCode": 1,
    "retryRenewCount": 1,
    "retriedForRenew": 1,
    "renewRejected": 1,
    "signTrackingCode": 1,
    "generateDate": 1,
    "treasuryId": 1,
    "businessId": 1,
    "initiator": 1,
    "version": 1,
    "sealedPromissoryNoteFileId": 1,
    "signedPromissoryNoteFileId": 1,
    "sourcePromissoryNoteFileId": 1,
}

INIT_DETAIL_FIELDS = {
    "tracking code": "trackingCode",
    "owner": "owner",
    "iban": "iban",
    "amount": "amount",
}


def known_promissory_stages() -> list[str]:
    """Registered lifecycle stage keys, for the regex unit test."""
    return sorted(STATUS_BY_NAME)


def known_promissory_init_details() -> list[str]:
    """Registered missing-detail keys, for the regex unit test."""
    return sorted(INIT_DETAIL_FIELDS)


NON_NUMERIC_AMOUNT = "not-a-number"
_PIN_TARGETS: dict[str, tuple[int, int]] = {
    "Saderat": (RECIPIENT_SADERAT, PROVIDER_SADERAT),
    "Kuknos for Tejarat": (RECIPIENT_TEJARAT, PROVIDER_KUKNOS),
}
_ROUTE_BANKS: dict[str, int] = {
    "Saderat": RECIPIENT_SADERAT,
    "Tejarat": RECIPIENT_TEJARAT,
}


def _mongo_write_failure(action: str, result: dict[str, Any]) -> str:
    """Short error when a Mongo write failed, including not-writable-primary."""
    error = str((result.get("body") or {}).get("error") or "")
    if "NotWritablePrimary" in error or "not master" in error:
        return f"{action} failed: Mongo node is not writable"
    return f"{action} failed: {result}"


def note_generate_date(doc: dict[str, Any]) -> int | None:
    """Return ``generateDate`` as int milliseconds when the field is numeric."""
    raw = doc.get("generateDate")
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    return None


def capture_provider_settings(client: ApiClient) -> dict[str, Any]:
    """Snapshot recipient weights and ``activeAutoWeighting`` for suite restore."""
    result = get_admin_promissory_notes_settings_provider(client)
    ensure_ok(result, context="snapshot provider settings")
    body = result.get("body")
    if not isinstance(body, ProviderSettingsBody) or not body.setting_detail:
        raise RuntimeError(f"unexpected settings body: {body!r}")
    detail = body.setting_detail
    recipients = detail.get("recipientDtos") or []
    if not isinstance(recipients, list) or not recipients:
        raise RuntimeError("provider settings snapshot has no recipientDtos")
    return {
        "recipientDtos": recipients,
        "activeAutoWeighting": bool(detail.get("activeAutoWeighting")),
    }


def restore_provider_settings(client: ApiClient, snapshot: dict[str, Any]) -> None:
    """Restore snapshotted recipient weights and ``activeAutoWeighting``."""
    deadline = time.monotonic() + RESTORE_POLL_TIMEOUT_S
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            _restore_provider_settings_once(client, snapshot)
            return
        except (RuntimeError, httpx.HTTPError, OSError) as exc:
            last_error = exc
            time.sleep(RESTORE_POLL_INTERVAL_S)
    raise RuntimeError("provider settings restore failed") from last_error


def _restore_provider_settings_once(client: ApiClient, snapshot: dict[str, Any]) -> None:
    active = bool(snapshot.get("activeAutoWeighting"))
    recipients = snapshot.get("recipientDtos") or []
    if not isinstance(recipients, list) or not recipients:
        raise RuntimeError("provider settings snapshot has no recipientDtos")
    posted = 0
    for recipient in recipients:
        if not isinstance(recipient, dict):
            continue
        request = ProviderSettingsRequest.model_validate(
            {"recipientDto": recipient, "activeAutoWeighting": active}
        )
        result = post_admin_promissory_notes_settings_provider(client, request)
        ensure_ok(result, context="restore provider settings")
        posted += 1
    if posted == 0:
        raise RuntimeError("no recipientDtos restored")


@dataclass
class PromissoryNoteContext:
    """Per-scenario tracking code and last API envelopes."""

    tracking_code: str | None = None
    last_result: dict[str, Any] = field(default_factory=dict)
    route_result: dict[str, Any] = field(default_factory=dict)
    init_result: dict[str, Any] = field(default_factory=dict)
    concurrent_out: dict[str, Any] = field(default_factory=dict)
    expected_inquiry_status: int | None = None
    recipient_code: int | None = None
    status_before: int | None = None
    retry_renew_before: int = 0
    generate_date_before: int | None = None


class PromissoryNoteFlow:
    """Promissory-note API + Mongo helpers for the KYC BDD slice."""

    def __init__(
        self,
        client: ApiClient,
        mongo: MongoDbClient,
        secrets: CHANGE_ME
        settings: Settings,
        settings_snapshot: dict[str, Any] | None = None,
    ) -> None:
        self._client = client
        self._mongo = mongo
        self._secrets = CHANGE_ME
        self._settings = settings
        self._settings_snapshot = settings_snapshot
        self._did_pin = False
        self._tracked: list[str] = []
        self._has_renew_restore: tuple[int, bool] | None = None

    def cleanup_tracked_notes(self) -> None:
        """Best-effort admin cancel + Mongo delete for notes created this scenario."""
        try:
            self._cleanup_tracked_best_effort()
        except (httpx.HTTPError, RuntimeError, TimeoutError, OSError) as exc:
            logger.warning("promissory note cleanup failed: %s", exc)

    def restore_pin_if_needed(self) -> None:
        """Restore snapshotted provider weights after a scenario that pinned."""
        if not self._did_pin or self._settings_snapshot is None:
            return
        restore_provider_settings(self._client, self._settings_snapshot)
        self._did_pin = False

    def restore_has_renew_if_needed(self) -> None:
        """Restore a provider ``hasRenew`` flag flipped by this scenario."""
        saved = self._has_renew_restore
        if saved is None:
            return
        provider, original_enabled = saved
        self._has_renew_restore = None
        self._write_provider_has_renew(provider, original_enabled)

    def new_tracking_code(self) -> str:
        """18-digit tracking code registered for cleanup."""
        code = "".join(py_secrets.choice("0123456789") for _ in range(18))
        self._track(code)
        return code

    # --- core ---

    def store_inquiry(self, ctx: PromissoryNoteContext) -> None:
        """Inquiry for ``ctx.tracking_code``."""
        assert_truthy("tracking code", ctx.tracking_code)
        ctx.last_result = post_promissory_notes_inquiry(self._client, ctx.tracking_code or "")

    def setup_generated_via_seed(self, ctx: PromissoryNoteContext) -> None:
        """Seed Mongo GENERATED note."""
        ctx.tracking_code = self.seed_note(STATUS_GENERATED)

    def setup_generated_forced_status(self, ctx: PromissoryNoteContext, status_name: str) -> None:
        """Seed GENERATED then force Mongo status by name (paid/signed/…)."""
        status = STATUS_BY_NAME[status_name.strip().lower()]
        self.setup_generated_via_seed(ctx)
        self.force_status(ctx.tracking_code or "", status)
        ctx.expected_inquiry_status = status

    def setup_generated_forced_paid(self, ctx: PromissoryNoteContext) -> None:
        """Seed GENERATED then force PAID with no payment row."""
        self.setup_generated_forced_status(ctx, "paid")

    def pin_provider(self, recipient_code: int, provider_enum: int) -> None:
        """Pin admin weights so route selects ``provider_enum``."""
        result = post_admin_promissory_notes_settings_provider(
            self._client,
            self._pin_request(recipient_code, provider_enum, False),
        )
        ensure_ok(result, context="pin provider settings")
        self._did_pin = True

    def pin_routing(self, target: str) -> None:
        """Pin admin weights for a Gherkin routing target."""
        recipient_code, provider_enum = _PIN_TARGETS[target]
        self.pin_provider(recipient_code, provider_enum)

    def setup_kuknos_rejected(self, ctx: PromissoryNoteContext) -> None:
        """Forced REJECTED Kuknos note (not PAID/SIGNED)."""
        self._setup_kuknos_forced_status(ctx, STATUS_REJECTED)

    def setup_kuknos_paid_renew_disabled(self, ctx: PromissoryNoteContext) -> None:
        """Forced PAID Kuknos note with renew disabled."""
        self._setup_kuknos_forced_status(ctx, STATUS_PAID)
        self.set_provider_has_renew(PROVIDER_KUKNOS, False)

    def set_provider_has_renew(self, provider: int, enabled: bool) -> None:
        """Set ``providersConfigs.hasRenew`` for ``provider``; restore on teardown."""
        if self._has_renew_restore is None:
            self._has_renew_restore = (provider, self._read_provider_has_renew(provider))
        self._write_provider_has_renew(provider, enabled)
        actual = self._read_provider_has_renew(provider)
        if actual != enabled:
            raise RuntimeError(f"hasRenew is {actual}, wanted {enabled}")

    def ensure_admin_settings_readable(self) -> None:
        """Fail setup unless admin provider settings return HTTP 200."""
        result = get_admin_promissory_notes_settings_provider(self._client)
        ensure_ok(result, context="promissory provider routing is configured")

    def store_route(self, ctx: PromissoryNoteContext, recipient_code: int) -> None:
        """Inquiry then route for ``recipient_code`` (weights already pinned)."""
        ctx.tracking_code = ctx.tracking_code or self.new_tracking_code()
        self._track(ctx.tracking_code)
        ctx.recipient_code = recipient_code
        post_promissory_notes_inquiry(self._client, ctx.tracking_code)
        route = post_promissory_notes_route(
            self._client,
            self._route_app(recipient_code),
            ctx.tracking_code,
            recipient_code,
        )
        ctx.route_result = route
        ctx.last_result = route

    def store_route_for_bank(self, ctx: PromissoryNoteContext, bank: str) -> None:
        """Route using the Gherkin bank name."""
        self.store_route(ctx, recipient_code=_ROUTE_BANKS[bank])

    def store_init_after_route(self, ctx: PromissoryNoteContext) -> None:
        """Init the routed note (does not wait for provider generate)."""
        assert_truthy("tracking code", ctx.tracking_code)
        recipient_code = self._require_recipient_code(ctx)
        init_req = self._init_request(
            ctx.tracking_code or "",
            recipient_code,
            use_seed_owner=recipient_code == RECIPIENT_TEJARAT,
        )
        init = post_promissory_notes_init(self._client, self._secrets.requester_app_name, init_req)
        ctx.init_result = init
        ctx.last_result = init

    def store_admin_cancel(self, ctx: PromissoryNoteContext) -> None:
        """Admin cancel current note."""
        assert_truthy("tracking code", ctx.tracking_code)
        ctx.last_result = post_admin_promissory_notes_cancel(self._client, ctx.tracking_code or "")

    def store_refund(self, ctx: PromissoryNoteContext) -> None:
        """Refund current note."""
        assert_truthy("tracking code", ctx.tracking_code)
        ctx.last_result = post_promissory_notes_refund(
            self._client,
            self._secrets.requester_app_name,
            ctx.tracking_code or "",
        )

    def store_payment_init(self, ctx: PromissoryNoteContext) -> None:
        """Payments/init for the current note."""
        assert_truthy("tracking code", ctx.tracking_code)
        owner = self._secrets.seed_owner
        ctx.last_result = post_promissory_notes_payments_init(
            self._client,
            user_id=owner.user_id,
            amount=int(self._secrets.amount),
            tracking_code=ctx.tracking_code or "",
            callback_url=TEST_CALLBACK_URL,
            client_id=self._secrets.requester_app_name,
            agent=ANDROID_AGENT,
            platform_version=PLATFORM_VERSION_2023,
            x_forwarded_for=TEST_X_FORWARDED_FOR,
        )

    def store_sign_request(self, ctx: PromissoryNoteContext) -> None:
        """Sign-request/init without ticket."""
        assert_truthy("tracking code", ctx.tracking_code)
        ctx.last_result = post_promissory_notes_sign_request_init(
            self._client, ctx.tracking_code or ""
        )

    # --- negatives ---

    def store_route_without_requester(self, ctx: PromissoryNoteContext) -> None:
        """Route with no Requester-App-Name header."""
        ctx.tracking_code = ctx.tracking_code or self.new_tracking_code()
        body = {
            "trackingCode": ctx.tracking_code,
            "recipientCode": RECIPIENT_TEJARAT,
        }
        ctx.last_result = post_promissory_notes_route_raw(self._client, body, headers={})

    def store_route_bad_recipient(self, ctx: PromissoryNoteContext) -> None:
        """Route with out-of-range recipient."""
        ctx.tracking_code = ctx.tracking_code or self.new_tracking_code()
        ctx.last_result = post_promissory_notes_route(
            self._client,
            self._secrets.requester_app_name,
            ctx.tracking_code or "",
            INVALID_RECIPIENT,
        )

    def store_init_missing_detail(self, ctx: PromissoryNoteContext, detail: str) -> None:
        """Init after omitting one required business detail."""
        self.store_init_missing_field(ctx, INIT_DETAIL_FIELDS[detail])

    def store_init_missing_field(self, ctx: PromissoryNoteContext, field: str) -> None:
        """Init after omitting one required field name."""
        code = ctx.tracking_code or self.new_tracking_code()
        ctx.tracking_code = code
        body = self._init_payload_dict(code, RECIPIENT_TEJARAT, use_seed_owner=True)
        body.pop(field, None)
        headers = promissory_requester_headers(self._secrets.requester_app_name)
        ctx.last_result = post_promissory_notes_init_raw(self._client, body, headers)

    def store_init_amount_value(self, ctx: PromissoryNoteContext, amount: str) -> None:
        """Init with overridden amount string."""
        ctx.tracking_code = ctx.tracking_code or self.new_tracking_code()
        body = self._init_payload_dict(ctx.tracking_code, RECIPIENT_TEJARAT, use_seed_owner=True)
        body["amount"] = amount
        headers = promissory_requester_headers(self._secrets.requester_app_name)
        ctx.last_result = post_promissory_notes_init_raw(self._client, body, headers)

    def store_init_non_numeric_amount(self, ctx: PromissoryNoteContext) -> None:
        """Init with the non-numeric amount constant."""
        self.store_init_amount_value(ctx, NON_NUMERIC_AMOUNT)

    def store_init_long_description(self, ctx: PromissoryNoteContext) -> None:
        """Init a routed note with an oversized description."""
        assert_truthy("tracking code", ctx.tracking_code)
        recipient = self._require_recipient_code(ctx)
        body = self._init_payload_dict(ctx.tracking_code or "", recipient, use_seed_owner=True)
        body["description"] = _LONG_DESCRIPTION
        headers = promissory_requester_headers(self._secrets.requester_app_name)
        ctx.last_result = post_promissory_notes_init_raw(self._client, body, headers)

    def store_user_cancel_unknown(self, ctx: PromissoryNoteContext) -> None:
        """User cancel on the scenario tracking code."""
        assert_truthy("tracking code", ctx.tracking_code)
        ctx.last_result = post_promissory_notes_user_cancel(self._client, ctx.tracking_code or "")

    def store_seal_without_sign_tc(self, ctx: PromissoryNoteContext) -> None:
        """Seal with empty sign tracking code."""
        ctx.tracking_code = ctx.tracking_code or self.new_tracking_code()
        ctx.last_result = post_promissory_notes_seal(
            self._client,
            tracking_code=ctx.tracking_code or "",
            sign_tracking_code="",
            check_expiration=True,
        )

    # --- mass assignment ---

    def store_route_with_injected(self, ctx: PromissoryNoteContext) -> None:
        """Route with injected server-owned fields."""
        ctx.tracking_code = ctx.tracking_code or self.new_tracking_code()
        body = {
            "trackingCode": ctx.tracking_code,
            "recipientCode": RECIPIENT_TEJARAT,
            **INJECTED_FIELDS,
        }
        headers = promissory_requester_headers(self._secrets.tejarat_route_requester_app_name)
        ctx.last_result = post_promissory_notes_route_raw(self._client, body, headers)
        ctx.route_result = ctx.last_result

    def store_init_with_injected(self, ctx: PromissoryNoteContext) -> None:
        """Init with injected server-owned fields on an already-routed note."""
        assert_truthy("tracking code", ctx.tracking_code)
        recipient_code = self._require_recipient_code(ctx)
        init_body = self._init_payload_dict(
            ctx.tracking_code or "", recipient_code, use_seed_owner=True
        )
        init_body.update(INJECTED_FIELDS)
        headers_init = promissory_requester_headers(self._secrets.requester_app_name)
        ctx.init_result = post_promissory_notes_init_raw(self._client, init_body, headers_init)
        ctx.last_result = ctx.init_result

    # --- concurrency ---

    def setup_routed_note(self, ctx: PromissoryNoteContext) -> None:
        """Inquiry + Tejarat route only."""
        ctx.tracking_code = self.new_tracking_code()
        ctx.recipient_code = RECIPIENT_TEJARAT
        post_promissory_notes_inquiry(self._client, ctx.tracking_code)
        ctx.route_result = post_promissory_notes_route(
            self._client,
            self._secrets.tejarat_route_requester_app_name,
            ctx.tracking_code,
            RECIPIENT_TEJARAT,
        )
        ctx.last_result = ctx.route_result
        ensure_ok(ctx.route_result, context="route promissory note")

    def store_concurrent_routes(self, ctx: PromissoryNoteContext) -> None:
        """Parallel route POSTs for one tracking code."""
        ctx.tracking_code = ctx.tracking_code or self.new_tracking_code()
        self._track(ctx.tracking_code)
        tracking_code = ctx.tracking_code or ""
        app_name = self._secrets.tejarat_route_requester_app_name
        ctx.concurrent_out = fire_concurrent_requests(
            self._settings,
            partial(
                post_promissory_notes_route,
                requester_app_name=app_name,
                tracking_code=tracking_code,
                recipient_code=RECIPIENT_TEJARAT,
            ),
            count=RACE_REQUESTS,
            workers=RACE_WORKERS,
        )

    def store_concurrent_admin_cancels(self, ctx: PromissoryNoteContext) -> None:
        """Parallel admin cancel POSTs."""
        assert_truthy("tracking code", ctx.tracking_code)
        tracking_code = ctx.tracking_code or ""
        ctx.concurrent_out = fire_concurrent_requests(
            self._settings,
            partial(post_admin_promissory_notes_cancel, tracking_code=tracking_code),
            count=RACE_REQUESTS,
            workers=RACE_WORKERS,
        )

    def store_concurrent_inquiries(self, ctx: PromissoryNoteContext) -> None:
        """Parallel inquiry POSTs."""
        assert_truthy("tracking code", ctx.tracking_code)
        tracking_code = ctx.tracking_code or ""
        ctx.concurrent_out = fire_concurrent_requests(
            self._settings,
            partial(post_promissory_notes_inquiry, tracking_code=tracking_code),
            count=RACE_REQUESTS,
            workers=RACE_WORKERS,
        )

    # --- admin ---

    def store_admin_settings_get(self, ctx: PromissoryNoteContext) -> None:
        """GET admin provider settings."""
        ctx.last_result = get_admin_promissory_notes_settings_provider(self._client)

    def store_admin_settings_search(self, ctx: PromissoryNoteContext) -> None:
        """POST settings search."""
        ctx.last_result = post_admin_promissory_notes_settings_search(self._client)

    def store_admin_success_rate(self, ctx: PromissoryNoteContext) -> None:
        """GET success-rate statistic."""
        ctx.last_result = get_admin_promissory_notes_success_rate_stat(self._client)

    def store_admin_success_rate_search(self, ctx: PromissoryNoteContext) -> None:
        """POST paginated provider success-rate search."""
        ctx.last_result = post_admin_promissory_notes_provider_success_rate_search(
            self._client, page=0, size=10
        )

    def store_admin_status_revert_unknown(self, ctx: PromissoryNoteContext) -> None:
        """Status revert for the scenario tracking code."""
        ctx.tracking_code = ctx.tracking_code or self.new_tracking_code()
        ctx.last_result = post_admin_promissory_notes_status_revert(
            self._client, ctx.tracking_code or ""
        )

    def store_admin_notify_unknown(self, ctx: PromissoryNoteContext) -> None:
        """Notify-generated batch for the scenario tracking code."""
        ctx.tracking_code = ctx.tracking_code or self.new_tracking_code()
        ctx.last_result = post_admin_promissory_notes_notify_generated_batch(
            self._client, [ctx.tracking_code or ""]
        )

    # --- mongo ---

    def seed_note(self, status: int) -> str:
        """Clone CONFIRMED template into ``status``."""
        code = self.new_tracking_code()
        template = self._mongo.find_one(
            self._secrets.mongo_db_name,
            self._secrets.notes_collection,
            {
                "owner.nationalCode": self._secrets.seed_template_national_code,
                "status": STATUS_CONFIRMED,
            },
        )
        body = template.get("body") or {}
        if not body or template.get("status_code") != 0:
            raise RuntimeError("No CONFIRMED promissory note template found for seed clone")
        doc = deepcopy(body)
        doc.pop("_id", None)
        now = int(time.time() * 1000)
        doc["trackingCode"] = code
        doc["status"] = status
        doc["owner"] = self._owner_payload(self._secrets.seed_owner)
        doc["iban"] = self._secrets.seed_iban
        doc["description"] = "AUTOMATION_SEEDED"
        doc["creationDate"] = Int64(now)
        doc["lastModificationDate"] = Int64(now)
        doc["exerciseDate"] = Int64(now + _ONE_YEAR_MS)
        if status < STATUS_SEALED:
            for key in (
                "sealedPromissoryNoteFileId",
                "signedPromissoryNoteFileId",
                "treasuryId",
                "sealDate",
                "generateDate",
            ):
                doc.pop(key, None)
        inserted = self._mongo.insert_one(
            self._secrets.mongo_db_name, self._secrets.notes_collection, doc
        )
        if inserted.get("status_code") != 0:
            raise RuntimeError(f"seed insert failed: {inserted}")
        return code

    def force_status(self, tracking_code: str, status: int) -> None:
        """Force Mongo status."""
        result = self._mongo.update_one(
            self._secrets.mongo_db_name,
            self._secrets.notes_collection,
            {"trackingCode": tracking_code},
            {"$set": {"status": status}},
        )
        if result.get("status_code") != 0:
            raise RuntimeError(_mongo_write_failure("force status", result))

    def get_note(self, tracking_code: str) -> dict[str, Any]:
        """Load assert fields for a note by tracking code (no owner/IBAN)."""
        result = self._mongo.find_one(
            self._secrets.mongo_db_name,
            self._secrets.notes_collection,
            {"trackingCode": tracking_code},
            projection=_NOTE_READ_FIELDS,
        )
        body = result.get("body") or {}
        if result.get("status_code") != 0 or not body:
            raise RuntimeError(f"note not found for {tracking_code}")
        return body

    def _setup_kuknos_started(self, ctx: PromissoryNoteContext) -> None:
        """Pin Kuknos for Tejarat, route, and init. Does not wait for generate."""
        self.pin_routing("Kuknos for Tejarat")
        ctx.tracking_code = ctx.tracking_code or self.new_tracking_code()
        self.store_route(ctx, RECIPIENT_TEJARAT)
        self.store_init_after_route(ctx)
        ensure_ok(ctx.init_result, context="kuknos tejarat init")

    def _setup_kuknos_forced_status(self, ctx: PromissoryNoteContext, status: int) -> None:
        """Init Kuknos and force Mongo status. Does not wait for generate."""
        self._setup_kuknos_started(ctx)
        tracking = ctx.tracking_code or ""
        self._force_status_with_retry(tracking, status)
        self._require_note_status(tracking, status)
        self._wait_inquiry_available(ctx)
        self._capture_renew_baseline(ctx)

    def _wait_inquiry_available(self, ctx: PromissoryNoteContext) -> None:
        """Poll inquiry until the MS sees the note (primary write / secondary read)."""
        assert_truthy("tracking code", ctx.tracking_code)
        deadline = time.monotonic() + (FORCE_STATUS_TRIES * FORCE_STATUS_INTERVAL_S)
        last_code: int | None = None
        while time.monotonic() < deadline:
            result = post_promissory_notes_inquiry(self._client, ctx.tracking_code or "")
            code = result.get("status_code")
            last_code = code if isinstance(code, int) else None
            if last_code == HTTP_OK:
                return
            time.sleep(FORCE_STATUS_INTERVAL_S)
        raise RuntimeError(f"inquiry did not see note after write (last http={last_code})")

    def _capture_renew_baseline(self, ctx: PromissoryNoteContext) -> None:
        """Store status / retry / generateDate for later renew asserts."""
        doc = self.get_note(ctx.tracking_code or "")
        ctx.status_before = int(doc.get("status", -999))
        ctx.retry_renew_before = int(doc.get("retryRenewCount") or 0)
        ctx.generate_date_before = note_generate_date(doc)

    def _force_status_with_retry(self, tracking_code: str, status: int) -> None:
        """Force Mongo status, retrying short replica-primary blips."""
        last: RuntimeError | None = None
        for _ in range(FORCE_STATUS_TRIES):
            try:
                self.force_status(tracking_code, status)
                return
            except RuntimeError as exc:
                last = exc
                time.sleep(FORCE_STATUS_INTERVAL_S)
        raise RuntimeError(f"force status failed after retries: {last}") from last

    def _require_note_status(self, tracking_code: str, expected: int) -> dict[str, Any]:
        """Poll Mongo until the note status matches ``expected``."""
        deadline = time.monotonic() + (FORCE_STATUS_TRIES * FORCE_STATUS_INTERVAL_S)
        last = self.get_note(tracking_code)
        while time.monotonic() < deadline:
            last = self.get_note(tracking_code)
            actual = int(last.get("status", -999))
            if actual == expected:
                return last
            time.sleep(FORCE_STATUS_INTERVAL_S)
        actual = int(last.get("status", -999))
        raise RuntimeError(f"note status {actual} != {expected}")

    def _read_provider_has_renew(self, provider: int) -> bool:
        """Current ``hasRenew`` for ``provider`` in settings.providersConfigs."""
        _index, enabled = self._provider_has_renew_row(provider)
        return enabled

    def _write_provider_has_renew(self, provider: int, enabled: bool) -> None:
        """Set ``hasRenew`` for ``provider`` in the settings document."""
        index, _current = self._provider_has_renew_row(provider)
        result = self._mongo.update_one(
            self._secrets.mongo_db_name,
            SETTINGS_COLLECTION,
            {"providersConfigs": {"$exists": True}},
            {"$set": {f"providersConfigs.{index}.hasRenew": enabled}},
        )
        body = result.get("body") or {}
        if result.get("status_code") != 0 or not body.get("matched_count"):
            raise RuntimeError(_mongo_write_failure("hasRenew update", result))

    def _provider_has_renew_row(self, provider: int) -> tuple[int, bool]:
        """Index and ``hasRenew`` for ``provider`` in settings.providersConfigs."""
        result = self._mongo.find_one(
            self._secrets.mongo_db_name,
            SETTINGS_COLLECTION,
            {"providersConfigs": {"$exists": True}},
            projection={"providersConfigs.provider": 1, "providersConfigs.hasRenew": 1},
        )
        body = result.get("body") or {}
        configs = body.get("providersConfigs")
        if result.get("status_code") != 0 or not isinstance(configs, list):
            raise RuntimeError("providersConfigs not found")
        for index, row in enumerate(configs):
            if isinstance(row, dict) and int(row.get("provider", -1)) == provider:
                return index, bool(row.get("hasRenew"))
        raise RuntimeError(f"provider {provider} missing from providersConfigs")

    def count_notes(self, tracking_code: str) -> int:
        """Count notes with tracking code."""
        result = self._mongo.count_documents(
            self._secrets.mongo_db_name,
            self._secrets.notes_collection,
            {"trackingCode": tracking_code},
        )
        body = result.get("body") or {}
        return int(body.get("count", 0))

    # --- internals ---

    def _require_recipient_code(self, ctx: PromissoryNoteContext) -> int:
        """Return the routed recipient; fail if this scenario never routed."""
        recipient = ctx.recipient_code
        assert_truthy("recipient code set", recipient is not None)
        if recipient is None:
            raise RuntimeError("recipient code missing; route the note first")
        return recipient

    def _route_app(self, recipient_code: int) -> str:
        if recipient_code == RECIPIENT_TEJARAT:
            return self._secrets.tejarat_route_requester_app_name
        return self._secrets.requester_app_name

    def _track(self, tracking_code: str) -> None:
        if tracking_code and tracking_code not in self._tracked:
            self._tracked.append(tracking_code)

    def _cleanup_tracked_best_effort(self) -> None:
        for code in list(self._tracked):
            try:
                post_admin_promissory_notes_cancel(self._client, code)
            except (httpx.HTTPError, RuntimeError, OSError) as exc:
                logger.debug("cancel cleanup %s: %s", code, exc)
            self._delete_related_docs(code)
        self._tracked.clear()

    def _delete_related_docs(self, tracking_code: str) -> None:
        db = self._secrets.mongo_db_name
        self._mongo.delete_many(db, self._secrets.notes_collection, {"trackingCode": tracking_code})
        self._mongo.delete_many(
            db,
            self._secrets.payments_collection,
            {"originalTrackingCode": tracking_code},
        )
        self._mongo.delete_many(
            db,
            self._secrets.refunds_collection,
            {"promissoryNoteTrackingCode": tracking_code},
        )

    def _pin_request(
        self, recipient_code: int, provider_enum: int, active_auto: bool
    ) -> ProviderSettingsRequest:
        return ProviderSettingsRequest.model_validate(
            {
                "recipientDto": {
                    "recipient": recipient_code,
                    "providersDto": [
                        {
                            "providerName": index,
                            "weight": 1.0 if index == provider_enum else 0.0,
                            "active": index == provider_enum,
                            "priority": 1,
                        }
                        for index in range(PROVIDER_COUNT)
                    ],
                },
                "activeAutoWeighting": active_auto,
            }
        )

    def _init_request(
        self, tracking_code: str, recipient_code: int, *, use_seed_owner: bool
    ) -> InitRequest:
        return InitRequest.model_validate(
            self._init_payload_dict(tracking_code, recipient_code, use_seed_owner=use_seed_owner)
        )

    def _init_payload_dict(
        self, tracking_code: str, recipient_code: int, *, use_seed_owner: bool
    ) -> dict[str, Any]:
        owner = self._secrets.seed_owner if use_seed_owner else self._secrets.owner
        iban = self._secrets.seed_iban if use_seed_owner else self._secrets.iban
        amount = self._secrets.tejarat_amount if use_seed_owner else self._secrets.amount
        description = _TEJARAT_DESCRIPTION if use_seed_owner else self._secrets.description
        return {
            "trackingCode": tracking_code,
            "owner": self._owner_payload(owner),
            "iban": iban,
            "amount": amount,
            "dueType": self._secrets.due_type,
            "dueOffsetInYears": self._secrets.due_offset_in_years,
            "recipientId": self._secrets.recipient_id,
            "recipientCode": recipient_code,
            "description": description,
        }

    @staticmethod
    def _owner_payload(owner: PromissoryOwnerSecrets) -> dict[str, str]:
        return {
            "userId": owner.user_id,
            "cellNumber": owner.cell_number,
            "nationalCode": owner.national_code,
            "birthDate": owner.birth_date,
            "postalCode": owner.postal_code,
            "city": owner.city,
            "address": owner.address,
        }
