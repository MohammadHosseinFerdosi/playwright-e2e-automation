"""Bank-transfer orchestration for Debit BDD (gateway-common + mellat-gateway)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from pymongo.errors import PyMongoError

from tests.api.client import ApiClient
from tests.api.debit.bank_transfer.ach_scheduler import (
    post_trigger_resume_suspend,
    post_trigger_transfer_report,
)
from tests.api.debit.bank_transfer.models import (
    TransferRouteBody,
    TransferRouteRequest,
    parse_transfer_body,
    result_title,
)
from tests.api.debit.bank_transfer.transfer_execute import (
    TransferExecuteRequest,
    post_bank_transfer_execute,
)
from tests.api.debit.bank_transfer.transfer_inquiry import get_bank_transfer_inquiry
from tests.api.debit.bank_transfer.transfer_route import post_bank_transfer_route
from tests.api.debit.paths import MS_BANK_TRANSFER_PATH, bank_transfer_user_headers
from tests.config.constants import PLATFORM_VERSION_2023
from tests.services.debit.bank_transfer_routing import BankTransferRoutingDb
from tests.services.debit.bank_transfer_secrets import BankTransferSecrets

logger = logging.getLogger(__name__)

NO_GATEWAY_TITLES = frozenset({"BANKPROXY_NO_GATEWAY"})
TYPE_ACH = 0
TYPE_RTGS = 1
TYPE_INTERNAL = 2
QA_FT_SHAHIN_PREFIX = "QA-FT-SHAHIN"
INTERNAL_TYPE_TOKENS = frozenset({TYPE_INTERNAL, "INTERNAL", "2"})
ACH_TYPE_TOKENS = frozenset({TYPE_ACH, "ACH", "0"})
RTGS_TYPE_TOKENS = frozenset({TYPE_RTGS, "RTGS", "1"})
MELLAT_INVALID_ROUTE_STEP = (
    r"^a customer routes a Mellat transfer with (?P<invalid_input>[A-Za-z0-9 ]+)$"
)


@dataclass
class BankTransferContext:
    """Per-scenario envelopes, mongo rows, and multi-call extras."""

    secrets: CHANGE_ME
    tracking_code: str | None = None
    last_result: dict[str, Any] = field(default_factory=dict)
    route_result: dict[str, Any] = field(default_factory=dict)
    second_result: dict[str, Any] = field(default_factory=dict)
    inquiry_result: dict[str, Any] = field(default_factory=dict)
    mongo_doc: dict[str, Any] | None = None
    mongo_count: int | None = None
    client_row: dict[str, Any] | None = None
    scheduler_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    route_types: list[Any] = field(default_factory=list)
    preflight_ok: bool = False
    # Mellat DSH probes / statements extras
    probe_codes: list[int] = field(default_factory=list)
    probe_titles: list[str | None] = field(default_factory=list)
    stored_amount: Any = None
    flags: dict[str, Any] = field(default_factory=dict)


class BankTransferFlow:
    """Route, inquiry, execute, and routing helpers for Debit bank-transfer BDD."""

    def __init__(
        self,
        client: ApiClient,
        routing: BankTransferRoutingDb,
        secrets: CHANGE_ME
    ) -> None:
        self._client = client
        self._routing = routing
        self._secrets = CHANGE_ME
        self._weight_snapshot: list[dict[str, Any]] | None = None
        self._account_snapshot: list[dict[str, Any]] | None = None

    @property
    def secrets(self) -> BankTransferSecrets:
        """UAT secrets for this flow."""
        return self._secrets

    def prepare(self) -> None:
        """Open Mongo and snapshot CASH_OUT client/account routing state."""
        self._routing.open()
        self._weight_snapshot = self._routing.snapshot_all_weights()
        self._account_snapshot = self._routing.snapshot_accounts()
        self.assert_routing_available()

    def assert_routing_available(self) -> None:
        """Confirm routing Mongo is open and the suite snapshot exists."""
        _ = self._routing.db
        if not self._weight_snapshot:
            raise RuntimeError("cash-out routing weights were not snapshotted")

    def teardown(self) -> None:
        """Restore weights/accounts and close Mongo."""
        try:
            if self._weight_snapshot is not None:
                self._routing.restore_all_weights(self._weight_snapshot)
            if self._account_snapshot is not None:
                self._routing.restore_accounts(self._account_snapshot)
        except PyMongoError as exc:
            logger.warning("bank-transfer routing restore failed: %s", exc)
        finally:
            self._weight_snapshot = None
            self._account_snapshot = None
            self._routing.close()

    def clear_all_gateway_weights(self) -> None:
        """Zero every CASH_OUT gateway weight."""
        self._routing.zero_all_weights()

    def pin_active_gateway(self) -> None:
        """Pin Mellat INTERNAL as the only weighted cash-out gateway."""
        self._routing.pin_mellat_internal(100)

    def pin_named_gateway(self, gateway: str) -> None:
        """Pin a CASH_OUT gateway named in Gherkin."""
        self._routing.pin_named_gateway(gateway)

    def pin_ach_gateway(self) -> None:
        """Pin Mellat ACH (PAYA) as the weighted cash-out gateway."""
        self._routing.pin_mellat_ach(100)

    def store_ach_route(
        self,
        ctx: BankTransferContext,
        *,
        amount: int | None = None,
        iban: str | None = None,
        preferred_type: str | None = None,
        tag: str = "ACH",
    ) -> None:
        """Pin ACH and route a cross-bank PAYA transfer."""
        self.pin_ach_gateway()
        tc = self._new_tracking_code(tag)
        ctx.tracking_code = tc
        amt = self._secrets.ach_probe_amount if amount is None else amount
        ctx.route_result = self._route(
            tc,
            amount=amt,
            iban=iban or self._secrets.mellat_cross_bank_iban,
            preferred_type=preferred_type or str(TYPE_ACH),
            description=f"QA|MELLAT|{tag}|{tc}",
        )
        ctx.last_result = ctx.route_result
        ctx.mongo_doc = self._routing.find_transfer(tc)

    def _ach_split_amount(self, ctx: BankTransferContext, chunks: int) -> int:
        """Remember the split total on the scenario context."""
        amount = self._secrets.ach_chunk * chunks
        ctx.flags["batch_total"] = amount
        return amount

    def store_ach_split(
        self,
        ctx: BankTransferContext,
        *,
        chunks: int,
        tag: str = "ACHBAT",
    ) -> None:
        """Route a PAYA amount that splits into ``chunks`` pieces."""
        self.store_ach_route(ctx, amount=self._ach_split_amount(ctx, chunks), tag=tag)

    def store_ach_remainder(self, ctx: BankTransferContext) -> None:
        """Route chunk-size + 1 so the remainder lands in a second piece."""
        amount = self._secrets.ach_chunk + 1
        ctx.flags["batch_total"] = amount
        self.store_ach_route(ctx, amount=amount, tag="ACHREM")

    def store_ach_split_then_inquiry(self, ctx: BankTransferContext, *, chunks: int) -> None:
        """Split PAYA route then inquiry."""
        self.store_ach_route_then_inquiry(ctx, amount=self._ach_split_amount(ctx, chunks))

    def store_ach_split_live_settle(self, ctx: BankTransferContext, *, chunks: int) -> None:
        """Split PAYA live execute; gated by allow_live_transfer."""
        self.store_ach_live_settle(ctx, amount=self._ach_split_amount(ctx, chunks))

    def store_ach_route_then_inquiry(
        self, ctx: BankTransferContext, *, amount: int | None = None
    ) -> None:
        """ACH route then inquiry (expect ROUTED)."""
        self.store_ach_route(ctx, amount=amount, tag="ACHINQ")
        self.store_inquiry(ctx)

    def store_ach_live_settle(self, ctx: BankTransferContext, *, amount: int | None = None) -> None:
        """ACH route + execute; gated by allow_live_transfer."""
        from tests.services.debit.bank_transfer_secrets import require_live_transfer

        require_live_transfer(self._secrets)
        self.store_ach_route(ctx, amount=amount or self._secrets.safe_amount, tag="ACHLIVE")
        if not ctx.tracking_code:
            raise RuntimeError("missing tracking for live ACH")
        ctx.last_result = self._execute(ctx.tracking_code)
        ctx.mongo_doc = self._routing.find_transfer(ctx.tracking_code)
        ctx.inquiry_result = self._inquiry(ctx.tracking_code)

    def store_ach_duplicate_route(self, ctx: BankTransferContext) -> None:
        """Duplicate ACH route same tracking."""
        self.pin_ach_gateway()
        tc = self._new_tracking_code("ACHDUP")
        ctx.tracking_code = tc
        kwargs = {
            "amount": self._secrets.ach_probe_amount,
            "iban": self._secrets.mellat_cross_bank_iban,
            "preferred_type": str(TYPE_ACH),
        }
        ctx.route_result = self._route(tc, description=f"QA|MELLAT|AD1|{tc}", **kwargs)
        ctx.second_result = self._route(tc, description=f"QA|MELLAT|AD2|{tc}", **kwargs)
        ctx.last_result = ctx.second_result
        ctx.mongo_count = self._routing.count_transfers(tc)

    def store_ach_concurrent_routes(self, ctx: BankTransferContext) -> None:
        """Two concurrent ACH routes with the same tracking code."""
        import concurrent.futures

        self.pin_ach_gateway()
        tc = self._new_tracking_code("ACHCON")
        ctx.tracking_code = tc

        def _one(label: str) -> dict[str, Any]:
            return self._route(
                tc,
                amount=self._secrets.ach_probe_amount,
                iban=self._secrets.mellat_cross_bank_iban,
                preferred_type=str(TYPE_ACH),
                description=f"QA|MELLAT|{label}|{tc}",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_one, "C1")
            f2 = pool.submit(_one, "C2")
            ctx.route_result = f1.result()
            ctx.second_result = f2.result()
        ctx.last_result = ctx.second_result
        ctx.mongo_count = self._routing.count_transfers(tc)

    def store_ach_zero_amount(self, ctx: BankTransferContext) -> None:
        """Zero-amount ACH route (expect reject)."""
        self.store_ach_route(ctx, amount=0, tag="ACH0")

    def store_ach_same_bank(self, ctx: BankTransferContext) -> None:
        """Same-bank IBAN while ACH pinned (must not be ACH)."""
        self.pin_ach_gateway()
        tc = self._new_tracking_code("ACHSAME")
        ctx.tracking_code = tc
        ctx.last_result = self._route(
            tc,
            amount=self._secrets.ach_probe_amount,
            iban=self._secrets.mellat_target_iban,
            preferred_type=str(TYPE_ACH),
            description=f"QA|MELLAT|ACHSAME|{tc}",
        )
        ctx.route_result = ctx.last_result
        ctx.mongo_doc = self._routing.find_transfer(tc)

    def store_recent_done_ach_inquiry(self, ctx: BankTransferContext) -> None:
        """Inquiry the newest QA DONE ACH transfer in mongo."""
        doc = self._routing.db.ach_transfers.find_one(
            {
                "trackingCode": {"$regex": "^QA-MEL"},
                "status": "DONE",
                "type": {"$in": [TYPE_ACH, "ACH", 0, "0"]},
            },
            sort=[("creationDate", -1)],
        )
        if doc is None:
            import pytest

            pytest.skip("No DONE QA Mellat ACH transfer in mongo for inquiry")
        tc = str(doc.get("trackingCode"))
        ctx.tracking_code = tc
        ctx.mongo_doc = doc
        ctx.inquiry_result = self._inquiry(tc)
        ctx.last_result = ctx.inquiry_result

    def deactivate_bank_client(self) -> None:
        """Mark Mellat INTERNAL inactive with a stale weight."""
        self._routing.layout_mellat_inactive_internal()

    def store_zero_weight_block_then_pin(self, ctx: BankTransferContext) -> None:
        """Zero all weights, record the reject, then pin Mellat and route."""
        self.clear_all_gateway_weights()
        self.store_route_attempt(ctx)
        ctx.flags["off_status"] = ctx.last_result.get("status_code")
        ctx.flags["off_title"] = title_of(ctx.last_result)
        ctx.flags["off_doc_missing"] = self._routing.find_transfer(ctx.tracking_code or "") is None
        self.pin_named_gateway("Mellat")
        self.store_route_success(ctx)

    def store_route_attempt(self, ctx: BankTransferContext) -> None:
        """Customer route attempt (expected rejection paths)."""
        tc = self._new_tracking_code("TRY")
        ctx.tracking_code = tc
        ctx.last_result = self._route(tc)

    def store_route_success(self, ctx: BankTransferContext) -> None:
        """Customer route expected to land on the pinned gateway."""
        tc = self._new_tracking_code("OK")
        ctx.tracking_code = tc
        ctx.route_result = self._route(tc, description=f"QA|MELLAT|ROUTE|{tc}")
        ctx.last_result = ctx.route_result
        ctx.mongo_doc = self._routing.find_transfer(tc)

    def store_inquiry(self, ctx: BankTransferContext) -> None:
        """Inquiry for the scenario tracking code."""
        if not ctx.tracking_code:
            raise RuntimeError("no tracking code to inquire")
        ctx.inquiry_result = self._inquiry(ctx.tracking_code)
        ctx.last_result = ctx.inquiry_result
        ctx.mongo_doc = self._routing.find_transfer(ctx.tracking_code)

    def run_environment_preflight(self, ctx: BankTransferContext) -> None:
        """Lightweight UAT preflight: Mongo reachable for CASH_OUT clients."""
        self.assert_routing_available()
        row = self._routing.db.clients.find_one({"agenda": "CASH_OUT"}, {"_id": 1})
        ctx.preflight_ok = row is not None
        ctx.client_row = self._routing.mellat_internal_client_row()

    def store_mellat_client_active(self, ctx: BankTransferContext) -> None:
        """Load active Mellat INTERNAL client row."""
        self.pin_active_gateway()
        ctx.client_row = self._routing.mellat_internal_client_row()

    def store_safe_route_contract(self, ctx: BankTransferContext) -> None:
        """Pin Mellat and route with safe amount; capture Mongo."""
        self.pin_active_gateway()
        tc = self._new_tracking_code("SMOKE")
        ctx.tracking_code = tc
        ctx.route_result = self._route(
            tc,
            amount=self._secrets.safe_amount,
            description=f"QA|MELLAT|ROUTE|{tc}",
        )
        ctx.last_result = ctx.route_result
        ctx.mongo_doc = self._routing.find_transfer(tc)

    def store_duplicate_route_same_payload(self, ctx: BankTransferContext) -> None:
        """Route twice with the same tracking code and body."""
        self.pin_active_gateway()
        tc = self._new_tracking_code("DUP")
        ctx.tracking_code = tc
        ctx.route_result = self._route(tc, description=f"QA|MELLAT|DUP1|{tc}")
        ctx.second_result = self._route(tc, description=f"QA|MELLAT|DUP2|{tc}")
        ctx.last_result = ctx.second_result
        ctx.mongo_count = self._routing.count_transfers(tc)
        ctx.mongo_doc = self._routing.find_transfer(tc)

    def store_marker_route_only(self, ctx: BankTransferContext) -> None:
        """Route marker amount only (stay INITIATED)."""
        self.pin_active_gateway()
        tc = self._new_tracking_code("MARK")
        ctx.tracking_code = tc
        ctx.route_result = self._route(
            tc, amount=self._secrets.marker_amount, description=f"QA|MELLAT|MARK|{tc}"
        )
        ctx.last_result = ctx.route_result
        ctx.mongo_doc = self._routing.find_transfer(tc)

    def store_invalid_route(
        self,
        ctx: BankTransferContext,
        *,
        case: str,
    ) -> None:
        """Route with an invalid input variant."""
        self.pin_active_gateway()
        dispatch = {
            "zero amount": self._invalid_zero_amount,
            "bad iban": self._invalid_bad_iban,
            "missing tracking": self._invalid_missing_tracking,
            "injection owner": self._invalid_injection_owner,
        }
        dispatch[case](ctx)

    def store_execute_without_route(self, ctx: BankTransferContext) -> None:
        """Execute transfer for a tracking code that was never routed."""
        tc = self._new_tracking_code("NOROUTE")
        ctx.tracking_code = tc
        ctx.last_result = self._execute(tc)

    def store_inquiry_unknown(self, ctx: BankTransferContext) -> None:
        """Inquiry a tracking code that does not exist."""
        ctx.tracking_code = "QA-NOT-FOUND-0001"
        ctx.inquiry_result = self._inquiry(ctx.tracking_code)
        ctx.last_result = ctx.inquiry_result

    def store_never_ach_under_pin(self, ctx: BankTransferContext) -> None:
        """Several routes while Mellat INTERNAL is pinned; collect types."""
        self.pin_active_gateway()
        types: list[int | None] = []
        for idx in range(3):
            tc = self._new_tracking_code(f"NACH{idx}")
            result = self._route(tc, description=f"QA|MELLAT|NACH|{tc}")
            body = route_body_fields(result)
            types.append(body.type if body is not None else None)
            doc = self._routing.find_transfer(tc)
            if doc is not None and doc.get("type") is not None:
                types.append(doc.get("type"))
        ctx.route_types = types
        ctx.last_result = result

    def store_duplicate_tracking_different_iban(self, ctx: BankTransferContext) -> None:
        """Second route reuses tracking with a tweaked same-bank IBAN."""
        self.pin_active_gateway()
        tc = self._new_tracking_code("DIBAN")
        ctx.tracking_code = tc
        ctx.route_result = self._route(tc, description=f"QA|MELLAT|IB1|{tc}")
        alt_iban = self._alternate_same_bank_iban()
        ctx.second_result = self._route(tc, iban=alt_iban, description=f"QA|MELLAT|IB2|{tc}")
        ctx.last_result = ctx.second_result
        ctx.mongo_doc = self._routing.find_transfer(tc)
        ctx.mongo_count = self._routing.count_transfers(tc)

    def store_scheduler_triggers(self, ctx: BankTransferContext) -> None:
        """Hit both ACH scheduler test triggers."""
        secrets = CHANGE_ME
        ctx.scheduler_results = {
            "batch-inquiry": post_trigger_transfer_report(
                self._client,
                user_id=secrets.user_id,
                forwarded_for=secrets.forwarded_for,
                platform_version=PLATFORM_VERSION_2023,
            ),
            "resume-suspend": post_trigger_resume_suspend(
                self._client,
                user_id=secrets.user_id,
                forwarded_for=secrets.forwarded_for,
                platform_version=PLATFORM_VERSION_2023,
            ),
        }

    def store_same_bank_internal_route(self, ctx: BankTransferContext) -> None:
        """Pin INTERNAL and route Mellat IBAN; expect INTERNAL type."""
        self.pin_active_gateway()
        tc = self._new_tracking_code("SAME")
        ctx.tracking_code = tc
        ctx.route_result = self._route(
            tc,
            amount=self._secrets.safe_amount,
            description=f"QA|MELLAT|SAME|{tc}",
        )
        ctx.last_result = ctx.route_result
        ctx.mongo_doc = self._routing.find_transfer(tc)

    def _invalid_zero_amount(self, ctx: BankTransferContext) -> None:
        tc = self._new_tracking_code("ZERO")
        ctx.tracking_code = tc
        ctx.last_result = self._route(tc, amount=0)

    def _invalid_bad_iban(self, ctx: BankTransferContext) -> None:
        tc = self._new_tracking_code("BADIBAN")
        ctx.tracking_code = tc
        ctx.last_result = self._route(tc, iban="IR00INVALID")

    def _invalid_missing_tracking(self, ctx: BankTransferContext) -> None:
        secrets = CHANGE_ME
        path = self._client.ms_path("/bank-transfer/transfer/route", MS_BANK_TRANSFER_PATH)
        payload = {
            "businessId": secrets.business_id,
            "targetIban": secrets.mellat_target_iban,
            "amount": secrets.safe_amount,
            "ownerName": secrets.mellat_owner_name,
            "description": "QA|NO-TRACKING",
            "preferredType": secrets.preferred_type,
            "agenda": secrets.agenda,
        }
        raw = self._client.post(
            path,
            headers=bank_transfer_user_headers(
                secrets.user_id,
                forwarded_for=secrets.forwarded_for,
                platform_version=PLATFORM_VERSION_2023,
            ),
            json=payload,
        )
        ctx.last_result = {
            "status_code": raw["status_code"],
            "body": parse_transfer_body(raw.get("body")),
        }

    def _invalid_injection_owner(self, ctx: BankTransferContext) -> None:
        tc = self._new_tracking_code("INJ")
        ctx.tracking_code = tc
        ctx.last_result = self._route(
            tc, owner_name="'; DROP TABLE--", description=f"QA|MELLAT|INJ|{tc}"
        )

    def _alternate_same_bank_iban(self) -> str:
        iban = self._secrets.mellat_target_iban
        if len(iban) < 4:
            return iban
        # Flip last digit within 0-9 for a different same-bank string.
        last = iban[-1]
        flip = "1" if last != "1" else "2"
        return iban[:-1] + flip

    def _new_tracking_code(self, scenario: str, *, prefix: str = "QA-MEL") -> str:
        slug = scenario.upper().replace(" ", "-")[:12]
        return f"{prefix}-{slug}-{uuid.uuid4().hex[:8].upper()}"

    def new_tracking_code(self, scenario: str, *, prefix: str = "QA-MEL") -> str:
        """Public tracking-code factory for suite helpers."""
        return self._new_tracking_code(scenario, prefix=prefix)

    def _route(
        self,
        tracking_code: str,
        *,
        description: str | None = None,
        amount: int | float | str | None = None,
        iban: str | None = None,
        owner_name: str | None = None,
        preferred_type: str | None = None,
    ) -> dict[str, Any]:
        secrets = CHANGE_ME
        request = TransferRouteRequest.model_validate(
            {
                "trackingCode": tracking_code,
                "businessId": secrets.business_id,
                "targetIban": iban or secrets.mellat_target_iban,
                "amount": secrets.marker_amount if amount is None else amount,
                "ownerName": owner_name or secrets.mellat_owner_name,
                "description": description or f"mellat {tracking_code}",
                "preferredType": (
                    secrets.preferred_type if preferred_type is None else preferred_type
                ),
                "agenda": secrets.agenda,
            }
        )
        return self._post_route(request)

    def _post_route(self, request: TransferRouteRequest) -> dict[str, Any]:
        secrets = CHANGE_ME
        return post_bank_transfer_route(
            self._client,
            request,
            user_id=secrets.user_id,
            forwarded_for=secrets.forwarded_for,
            platform_version=PLATFORM_VERSION_2023,
        )

    def route_raw(
        self,
        *,
        tracking_code: str | None,
        amount: Any,
        iban: str,
        owner_name: str,
        description: str,
        preferred_type: str | None = None,
    ) -> dict[str, Any]:
        """POST route with a possibly incomplete payload (DSH negatives)."""
        secrets = CHANGE_ME
        path = self._client.ms_path("/bank-transfer/transfer/route", MS_BANK_TRANSFER_PATH)
        payload: dict[str, Any] = {
            "businessId": secrets.business_id,
            "targetIban": iban,
            "amount": amount,
            "ownerName": owner_name,
            "description": description,
            "preferredType": secrets.preferred_type if preferred_type is None else preferred_type,
            "agenda": secrets.agenda,
        }
        if tracking_code is not None:
            payload["trackingCode"] = tracking_code
        raw = self._client.post(
            path,
            headers=bank_transfer_user_headers(
                secrets.user_id,
                forwarded_for=secrets.forwarded_for,
                platform_version=PLATFORM_VERSION_2023,
            ),
            json=payload,
        )
        return {
            "status_code": raw["status_code"],
            "body": parse_transfer_body(raw.get("body")),
        }

    def wait_mongo_settled(
        self, tracking_code: str, *, timeout_sec: float = 120.0
    ) -> dict[str, Any] | None:
        """Poll mongo until transfer leaves INITIATED / reaches DONE-like status."""
        import time

        deadline = time.time() + timeout_sec
        settled = frozenset({"DONE", "REJECT", "CANCEL"})
        last: dict[str, Any] | None = None
        while time.time() < deadline:
            last = self._routing.find_transfer(tracking_code)
            if last is not None and last.get("status") in settled:
                return last
            if last is not None and last.get("status") not in (
                None,
                "INITIATED",
            ):
                # IN_PROGRESS / SUCCEED may still complete — keep polling briefly
                if last.get("status") == "DONE":
                    return last
            time.sleep(2.0)
            post_trigger_transfer_report(
                self._client,
                user_id=self._secrets.user_id,
                forwarded_for=self._secrets.forwarded_for,
                platform_version=PLATFORM_VERSION_2023,
            )
        return last

    def _inquiry(self, tracking_code: str) -> dict[str, Any]:
        secrets = CHANGE_ME
        return get_bank_transfer_inquiry(
            self._client,
            tracking_code,
            user_id=secrets.user_id,
            forwarded_for=secrets.forwarded_for,
            platform_version=PLATFORM_VERSION_2023,
        )

    def _execute(self, tracking_code: str) -> dict[str, Any]:
        secrets = CHANGE_ME
        return post_bank_transfer_execute(
            self._client,
            TransferExecuteRequest.model_validate({"trackingCode": tracking_code}),
            user_id=secrets.user_id,
            forwarded_for=secrets.forwarded_for,
            platform_version=PLATFORM_VERSION_2023,
        )

    def route(
        self,
        tracking_code: str,
        *,
        description: str | None = None,
        amount: int | float | str | None = None,
        iban: str | None = None,
        owner_name: str | None = None,
        preferred_type: str | None = None,
    ) -> dict[str, Any]:
        """Public route helper."""
        return self._route(
            tracking_code,
            description=description,
            amount=amount,
            iban=iban,
            owner_name=owner_name,
            preferred_type=preferred_type,
        )

    def inquiry(self, tracking_code: str) -> dict[str, Any]:
        """Public inquiry helper."""
        return self._inquiry(tracking_code)

    def execute(self, tracking_code: str) -> dict[str, Any]:
        """Public execute helper."""
        return self._execute(tracking_code)

    def find_transfer(self, tracking_code: str) -> dict[str, Any] | None:
        """Lookup ach_transfers by tracking code."""
        return self._routing.find_transfer(tracking_code)

    def count_transfers(self, tracking_code: str) -> int:
        """Count ach_transfers rows for a tracking code."""
        return self._routing.count_transfers(tracking_code)

    @property
    def client(self) -> ApiClient:
        """HTTP client for statement APIs."""
        return self._client

    @property
    def routing(self) -> BankTransferRoutingDb:
        """Routing Mongo helper."""
        return self._routing


def route_body_fields(result: dict[str, Any]) -> TransferRouteBody | None:
    """Typed route/inquiry body when parse succeeded."""
    body = result.get("body")
    return body if isinstance(body, TransferRouteBody) else None


def title_of(result: dict[str, Any]) -> str | None:
    """result.title helper."""
    return result_title(result.get("body"))
