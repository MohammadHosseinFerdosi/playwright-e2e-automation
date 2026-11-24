"""TREASURY direct-route orchestration (Melli, Mellat, ft shahin)."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Literal

from pymongo.errors import PyMongoError

from tests.api.client import ApiClient
from tests.api.debit.bank_transfer.ach_scheduler import post_trigger_transfer_report
from tests.api.debit.bank_transfer.models import TransferDirectRouteRequest
from tests.api.debit.bank_transfer.transfer_direct_route import (
    post_bank_transfer_direct_route,
)
from tests.api.debit.bank_transfer.transfer_execute import (
    TransferExecuteRequest,
    post_bank_transfer_execute,
)
from tests.api.debit.bank_transfer.transfer_inquiry import get_bank_transfer_inquiry
from tests.config.constants import PLATFORM_VERSION_2023
from tests.services.debit.bank_transfer import (
    QA_FT_SHAHIN_PREFIX,
    TYPE_ACH,
    TYPE_INTERNAL,
    BankTransferContext,
    title_of,
)
from tests.services.debit.bank_transfer_routing import (
    BankTransferRoutingDb,
)
from tests.services.debit.bank_transfer_secrets import (
    BankTransferSecrets,
    require_live_transfer,
)

logger = logging.getLogger(__name__)

Rail = Literal["melli", "mellat", "ft_shahin"]
INQ_PENDING = 2
INQ_SUCCEED = 1
REJECT_TITLES = frozenset(
    {
        "INVALID_PARAMETER",
        "FAILURE",
        "BAD_REQUEST",
        "BANKPROXY_NO_GATEWAY",
    }
)
IDEMPOTENT = frozenset({"BANKPROXY_DUPLICATE_TRANSACTION", "INVALID_PARAMETER", "FAILURE"})


class DirectRouteFlow:
    """Prepare TREASURY rails, post direct-route, execute/inquiry helpers."""

    def __init__(
        self,
        client: ApiClient,
        routing: BankTransferRoutingDb,
        secrets: BankTransferSecrets,
        *,
        rail: Rail,
    ) -> None:
        self._client = client
        self._routing = routing
        self._secrets = secrets
        self.rail = rail
        self._account_snap: list[dict[str, Any]] | None = None
        self._ft_shahin_kind = "ACH"

    @property
    def secrets(self) -> BankTransferSecrets:
        """UAT secrets."""
        return self._secrets

    def prepare(self) -> None:
        """Open Mongo and snapshot account clientIds for this rail."""
        self._routing.open()
        if self.rail == "melli":
            self._account_snap = self._routing.snapshot_melli_direct_accounts()
            self._routing.ensure_melli_direct_ready()
        elif self.rail == "mellat":
            self._account_snap = self._routing.snapshot_mellat_direct_accounts()
            self._routing.ensure_mellat_direct_ready()
        else:
            self._account_snap = self._routing.snapshot_saderat_direct_accounts()
            self._routing.ensure_saderat_direct_ready()

    def assert_ready(self) -> None:
        """Confirm suite snapshot exists."""
        if not self._account_snap:
            raise RuntimeError(f"{self.rail} direct-route account was not snapshotted")

    def teardown(self) -> None:
        """Restore account docs and close Mongo."""
        try:
            if self._account_snap is not None:
                self._routing.restore_account_docs(self._account_snap)
                if self.rail == "mellat":
                    self._routing.ensure_mellat_cash_out_client_ids()
        except (PyMongoError, RuntimeError) as exc:
            logger.warning("%s direct-route restore failed: %s", self.rail, exc)
        finally:
            self._account_snap = None
            self._routing.close()

    def source_iban(self) -> str:
        """Rail source IBAN."""
        if self.rail == "melli":
            return self._secrets.melli_direct_source_iban
        if self.rail == "mellat":
            return self._secrets.mellat_direct_source_iban
        return self._secrets.ft_shahin_paya_source_iban

    def target_iban(self) -> str:
        """Cross-bank target IBAN."""
        if self.rail == "melli":
            return self._secrets.melli_direct_target_iban
        if self.rail == "mellat":
            return self._secrets.mellat_direct_target_iban
        return self._secrets.ft_shahin_paya_target_iban

    def client_code(self) -> str:
        """Expected clientCode."""
        return {"melli": "bn_melli", "mellat": "bn_mellat", "ft_shahin": "ft_shahin"}[self.rail]

    def bank_code(self) -> str:
        """Expected bankCode."""
        return {"melli": "017", "mellat": "012", "ft_shahin": "019"}[self.rail]

    def prefix(self) -> str:
        """Tracking-code prefix."""
        return {
            "melli": "QA-MLI",
            "mellat": "QA-MDR",
            "ft_shahin": QA_FT_SHAHIN_PREFIX,
        }[self.rail]

    def new_tracking_code(self, tag: str) -> str:
        """Build a unique tracking code."""
        slug = tag.upper().replace(" ", "-")[:24]
        return f"{self.prefix()}-{slug}-{uuid.uuid4().hex[:8].upper()}"

    def set_ft_shahin_kind(self, kind: str) -> None:
        """Select ACH or internal source/dest for ft shahin treasury."""
        self._ft_shahin_kind = kind.strip()

    def store_ft_shahin_kind_case(self, ctx: BankTransferContext, kind: str, case: str) -> None:
        """Set ft shahin rail kind then dispatch a direct-route case."""
        self.set_ft_shahin_kind(kind)
        self.store_case(ctx, case)

    def _ft_shahin_route_kwargs(self) -> dict[str, Any]:
        """Source IBAN, dest IBAN, type, and amount for the ft shahin rail."""
        secrets = self._secrets
        source = secrets.ft_shahin_paya_source_iban
        table: dict[str, tuple[str, str, str, int]] = {
            "ACH": (
                str(TYPE_ACH),
                source,
                secrets.ft_shahin_paya_target_iban,
                secrets.ach_probe_amount,
            ),
            "internal": (
                str(TYPE_INTERNAL),
                source,
                secrets.ft_shahin_internal_iban,
                secrets.safe_amount,
            ),
        }
        preferred, src, target, amount = table[self._ft_shahin_kind]
        return {
            "preferred_type": preferred,
            "source_iban": src,
            "target_iban": target,
            "amount": amount,
        }

    def _tag_kind(self, ctx: BankTransferContext) -> None:
        """Record the selected ft shahin rail on the scenario context."""
        ctx.flags["ft_shahin_kind"] = self._ft_shahin_kind

    def direct_route(
        self,
        tracking_code: str,
        *,
        source_iban: str | None = None,
        target_iban: str | None = None,
        amount: int | None = None,
        agenda: int | None = None,
        omit_source: bool = False,
        description: str | None = None,
        preferred_type: str | None = None,
    ) -> dict[str, Any]:
        """POST direct-route."""
        secrets = self._secrets
        defaults = self._ft_shahin_route_kwargs() if self.rail == "ft_shahin" else {}
        chosen_amount = (
            amount if amount is not None else defaults.get("amount", secrets.safe_amount)
        )
        request = TransferDirectRouteRequest.model_validate(
            {
                "trackingCode": tracking_code,
                "businessId": secrets.business_id,
                "sourceIban": None
                if omit_source
                else (source_iban or defaults.get("source_iban") or self.source_iban()),
                "targetIban": target_iban or defaults.get("target_iban") or self.target_iban(),
                "amount": chosen_amount,
                "ownerName": secrets.mellat_owner_name,
                "description": description or f"QA|{self.rail.upper()}|DIRECT|{tracking_code}",
                "preferredType": preferred_type or defaults.get("preferred_type") or str(TYPE_ACH),
                "agenda": (secrets.direct_route_agenda if agenda is None else agenda),
            }
        )
        result = self._post_direct(request)
        return result

    def _post_direct(self, request: TransferDirectRouteRequest) -> dict[str, Any]:
        secrets = self._secrets
        return post_bank_transfer_direct_route(
            self._client,
            request,
            user_id=secrets.user_id,
            forwarded_for=secrets.forwarded_for,
            platform_version=PLATFORM_VERSION_2023,
        )

    def execute(self, tracking_code: str) -> dict[str, Any]:
        """POST /transfer."""
        secrets = self._secrets
        return post_bank_transfer_execute(
            self._client,
            TransferExecuteRequest.model_validate({"trackingCode": tracking_code}),
            user_id=secrets.user_id,
            forwarded_for=secrets.forwarded_for,
            platform_version=PLATFORM_VERSION_2023,
        )

    def inquiry(self, tracking_code: str) -> dict[str, Any]:
        """GET inquiry."""
        secrets = self._secrets
        return get_bank_transfer_inquiry(
            self._client,
            tracking_code,
            user_id=secrets.user_id,
            forwarded_for=secrets.forwarded_for,
            platform_version=PLATFORM_VERSION_2023,
        )

    def find(self, tracking_code: str) -> dict[str, Any] | None:
        """Mongo ach_transfers lookup."""
        return self._routing.find_transfer(tracking_code)

    def count(self, tracking_code: str) -> int:
        """Mongo row count."""
        return self._routing.count_transfers(tracking_code)

    def store_case(self, ctx: BankTransferContext, case: str) -> None:
        """Dispatch When by case key."""
        dispatch = {
            "happy path": self._happy,
            "zero amount": self._zero,
            "invalid source iban": self._bad_source,
            "non home source": self._non_home_source,
            "same bank target": self._same_bank,
            "duplicate tracking": self._duplicate,
            "inactive client": self._inactive,
            "wrong agenda": self._wrong_agenda,
            "missing source": self._missing_source,
            "settle eventually": self._settle,
            "wrong client ids": self._wrong_ids,
        }
        dispatch[case](ctx)

    def _ensure(self) -> None:
        {
            "melli": self._routing.ensure_melli_direct_ready,
            "mellat": self._routing.ensure_mellat_direct_ready,
            "ft_shahin": self._routing.ensure_saderat_direct_ready,
        }[self.rail]()

    def _happy(self, ctx: BankTransferContext) -> None:
        require_live_transfer(self._secrets)
        self._ensure()
        self._tag_kind(ctx)
        tc = self.new_tracking_code("happy-path")
        ctx.tracking_code = tc
        ctx.route_result = self.direct_route(tc)
        ctx.last_result = ctx.route_result
        if ctx.route_result.get("status_code") != 200:
            return
        xfer = self.execute(tc)
        ctx.flags["xfer_status"] = xfer.get("status_code")
        ctx.second_result = self.execute(tc)
        ctx.mongo_count = self.count(tc)
        ctx.mongo_doc = self.find(tc)
        ctx.inquiry_result = self.inquiry(tc)
        ctx.flags.update(self._evidence(ctx.mongo_doc, ctx.inquiry_result, xfer))

    def _settle(self, ctx: BankTransferContext) -> None:
        require_live_transfer(self._secrets)
        self._ensure()
        self._tag_kind(ctx)
        tc = self.new_tracking_code("settle")
        ctx.tracking_code = tc
        ctx.route_result = self.direct_route(tc)
        if ctx.route_result.get("status_code") != 200:
            ctx.last_result = ctx.route_result
            return
        self.execute(tc)
        doc = self._poll_done(tc, timeout_sec=180.0)
        ctx.mongo_doc = doc
        ctx.inquiry_result = self.inquiry(tc)
        ctx.last_result = ctx.inquiry_result
        ctx.flags["mongo_status"] = (doc or {}).get("status")
        body = ctx.inquiry_result.get("body")
        status = getattr(body, "status", None)
        if status is None and isinstance(body, dict):
            status = body.get("status")
        ctx.flags["inquiry_status"] = status

    def _zero(self, ctx: BankTransferContext) -> None:
        self._neg(ctx, "zero-amount", amount=0)

    def _bad_source(self, ctx: BankTransferContext) -> None:
        bad = {
            "melli": "IR100170000000119061645099",
            "mellat": "IR100120000000119061645099",
            "ft_shahin": "IR100190000000119061645099",
        }[self.rail]
        self._neg(ctx, "bad-source", source_iban=bad)

    def _non_home_source(self, ctx: BankTransferContext) -> None:
        foreign = {
            "melli": self._secrets.mellat_target_iban,
            "mellat": self._secrets.melli_direct_source_iban,
            "ft_shahin": self._secrets.mellat_direct_source_iban,
        }[self.rail]
        self._neg(ctx, "non-home", source_iban=foreign)

    def _same_bank(self, ctx: BankTransferContext) -> None:
        self._ensure()
        self._tag_kind(ctx)
        tc = self.new_tracking_code("same-bank")
        ctx.tracking_code = tc
        same = (
            self._secrets.ft_shahin_internal_iban
            if self.rail == "ft_shahin"
            else self.source_iban()
        )
        ctx.last_result = self.direct_route(tc, target_iban=same)
        ctx.mongo_doc = self.find(tc)
        body = ctx.last_result.get("body")
        route_type = getattr(body, "type", None)
        if route_type is None and isinstance(body, dict):
            route_type = body.get("type")
        ctx.flags["route_type"] = route_type
        ctx.flags["mongo_type"] = (ctx.mongo_doc or {}).get("type")
        ctx.flags["title"] = title_of(ctx.last_result)

    def _duplicate(self, ctx: BankTransferContext) -> None:
        self._ensure()
        self._tag_kind(ctx)
        tc = self.new_tracking_code("duplicate")
        ctx.tracking_code = tc
        ctx.route_result = self.direct_route(tc)
        ctx.second_result = self.direct_route(tc)
        ctx.last_result = ctx.second_result
        ctx.mongo_count = self.count(tc)

    def _inactive(self, ctx: BankTransferContext) -> None:
        if self.rail == "mellat":
            self._wrong_ids(ctx)
            return
        self._ensure()
        if self.rail == "ft_shahin":
            self._routing.deactivate_saderat_treasury_ach()
        else:
            self._routing.deactivate_melli_treasury_ach()
        self._neg(ctx, "inactive", ensure=False)

    def _wrong_agenda(self, ctx: BankTransferContext) -> None:
        if self.rail != "melli":
            # Mellat suite has no wrong-agenda case — map unused.
            self._neg(ctx, "wrong-agenda", agenda=0)
            return
        self._ensure()
        tc = self.new_tracking_code("wrong-agenda")
        ctx.tracking_code = tc
        ctx.last_result = self.direct_route(tc, agenda=0)
        ctx.mongo_doc = self.find(tc)
        ctx.flags["title"] = title_of(ctx.last_result)
        ctx.flags["agenda"] = (ctx.mongo_doc or {}).get("agenda")
        ctx.flags["client"] = (ctx.mongo_doc or {}).get("clientCode")

    def _missing_source(self, ctx: BankTransferContext) -> None:
        self._neg(ctx, "missing-source", omit_source=True)

    def _wrong_ids(self, ctx: BankTransferContext) -> None:
        """Only INTERNAL client id on the treasury/cash-out account."""
        self._ensure()
        if self.rail == "ft_shahin":
            self._routing.set_saderat_direct_client_ids([207])
        else:
            self._routing.set_mellat_direct_client_ids([116])
            self._routing.wait_until_mellat_cash_out_client_ids([116])
        self._neg(ctx, "wrong-ids", ensure=False)

    def _neg(
        self,
        ctx: BankTransferContext,
        tag: str,
        *,
        amount: int | None = None,
        source_iban: str | None = None,
        agenda: int | None = None,
        omit_source: bool = False,
        ensure: bool = True,
    ) -> None:
        if ensure:
            self._ensure()
        self._tag_kind(ctx)
        tc = self.new_tracking_code(tag)
        ctx.tracking_code = tc
        ctx.last_result = self.direct_route(
            tc,
            amount=amount,
            source_iban=source_iban,
            agenda=agenda,
            omit_source=omit_source,
        )
        ctx.mongo_doc = self.find(tc)
        ctx.flags["title"] = title_of(ctx.last_result)
        ctx.flags["doc_missing"] = ctx.mongo_doc is None

    def _poll_done(self, tracking_code: str, *, timeout_sec: float) -> dict[str, Any] | None:
        deadline = time.time() + timeout_sec
        last: dict[str, Any] | None = None
        while time.time() < deadline:
            last = self.find(tracking_code)
            if last is not None and last.get("status") == "DONE":
                return last
            post_trigger_transfer_report(
                self._client,
                user_id=self._secrets.user_id,
                forwarded_for=self._secrets.forwarded_for,
                platform_version=PLATFORM_VERSION_2023,
            )
            time.sleep(5.0)
        return last

    def _evidence(
        self,
        doc: dict[str, Any] | None,
        inquiry: dict[str, Any],
        xfer: dict[str, Any],
    ) -> dict[str, Any]:
        body = inquiry.get("body")
        inq_status = getattr(body, "status", None)
        if inq_status is None and isinstance(body, dict):
            inq_status = body.get("status")
        xfer_body = xfer.get("body")
        bank_ref = None
        if isinstance(xfer_body, dict):
            bank_ref = (xfer_body.get("payResponse") or {}).get("bankTrackingCode")
        txs = (doc or {}).get("transactions") or []
        return {
            "mongo_status": (doc or {}).get("status"),
            "mongo_client": (doc or {}).get("clientCode"),
            "mongo_agenda": (doc or {}).get("agenda"),
            "mongo_type": (doc or {}).get("type"),
            "inquiry_status": inq_status,
            "bank_ref": bank_ref,
            "tx_count": len(txs),
            "tx_amount": txs[0].get("amount") if txs else None,
        }
