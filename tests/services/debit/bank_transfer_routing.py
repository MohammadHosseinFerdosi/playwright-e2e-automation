"""Mongo helpers for bank-transfer routing weights (CASH_OUT clients)."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from tests.services.debit.bank_transfer_secrets import BankTransferSecrets

# CASH_OUT gateways touched when zeroing layout.
ROUTING_GATEWAYS: dict[str, tuple[str, str, str]] = {
    "mellat": ("bn_mellat", "012", "INTERNAL_TRANSFER"),
    "mellat_ach": ("bn_mellat", "012", "ACH_TRANSFER"),
    "mellat_rtgs": ("bn_mellat", "012", "RTGS_TRANSFER"),
    "parsian": ("bn_parsian", "054", "ACH_TRANSFER"),
    "ft_shahin_internal": ("ft_shahin", "019", "INTERNAL_TRANSFER"),
    "ft_shahin_ach": ("ft_shahin", "019", "ACH_TRANSFER"),
    "ft_shahin_rtgs": ("ft_shahin", "019", "RTGS_TRANSFER"),
    "manual": ("bn_manual", "MANUAL", "ACH_TRANSFER"),
}

_MELLAT_SERVICE_TYPES = ("INTERNAL_TRANSFER", "ACH_TRANSFER", "RTGS_TRANSFER")
_MELLAT_CASH_OUT_CLIENT_IDS = {
    "ACH_TRANSFER": 110,
    "INTERNAL_TRANSFER": 52,
    "RTGS_TRANSFER": 111,
}
_MELLI_DIRECT_CLIENT_IDS = {
    "ACH_TRANSFER": 105,
    "INTERNAL_TRANSFER": 125,
    "RTGS_TRANSFER": 13,
}
_MELLAT_DIRECT_CLIENT_IDS = {
    "ACH_TRANSFER": 115,
    "INTERNAL_TRANSFER": 116,
    "RTGS_TRANSFER": 117,
}
_PARSIAN_CASH_OUT_CLIENT_IDS = {
    "ACH_TRANSFER": 3,
    "INTERNAL_TRANSFER": 2,
    "RTGS_TRANSFER": 1,
}
# CASH_OUT Switch clients (unique index). TREASURY 205-208 live on the same account.
_FT_SHAHIN_CASH_OUT_CLIENT_IDS = {
    "ACH_TRANSFER": 201,
    "INTERNAL_TRANSFER": 202,
    "RTGS_TRANSFER": 203,
}
_FT_SHAHIN_CASH_OUT_STATEMENT_ID = 204
_FT_SHAHIN_TREASURY_CLIENT_IDS = {
    "ACH_TRANSFER": 205,
    "RTGS_TRANSFER": 206,
    "INTERNAL_TRANSFER": 207,
}
_FT_SHAHIN_TREASURY_STATEMENT_ID = 208
_ACTIVE_TRUE = [True, "true"]
_POLL_INTERVAL_SEC = 0.25
TREASURY_AGENDA = "TREASURY"
SWITCH_SETUP_TITLES = frozenset(
    {
        "SWCH_BANK_SERVICE_NOT_AVAILABLE",
        "SWCH_BANK_CLIENT_NOT_FOUND",
    }
)
PIN_GATEWAY_ALIASES = {
    "Mellat internal": "mellat",
    "Mellat": "mellat",
    "Parsian PAYA": "parsian",
    "Mellat SATNA": "mellat_rtgs",
    "Manual ACH": "manual",
    "Manual": "manual",
    "Mellat PAYA": "mellat_ach",
    "ft shahin": "ft_shahin_internal",
    "ft shahin PAYA": "ft_shahin_ach",
    "ft shahin SATNA": "ft_shahin_rtgs",
}

logger = logging.getLogger(__name__)


def skip_if_switch_setup(title: str | None, *, reason: str = "Switch setup") -> None:
    """Skip instead of treating Switch titles as a product reject."""
    if title in SWITCH_SETUP_TITLES:
        pytest.skip(f"{reason}: {title}")


@contextmanager
def bank_transfer_routing_session(
    secrets: CHANGE_ME
) -> Iterator[BankTransferRoutingDb]:
    """Open Mongo, snapshot CASH_OUT weights, restore and close on exit."""
    routing = BankTransferRoutingDb(secrets)
    routing.open()
    snapshot = routing.snapshot_all_weights()
    try:
        yield routing
    finally:
        try:
            routing.restore_all_weights(snapshot)
        except PyMongoError as exc:
            logger.warning("bank-transfer routing restore failed: %s", exc)
        finally:
            routing.close()


class BankTransferRoutingDb:
    """Snapshot / pin / zero CASH_OUT routing weights for Debit QA."""

    def __init__(self, secrets: BankTransferSecrets) -> None:
        self._secrets = CHANGE_ME
        self._client: MongoClient[Any] | None = None
        self._db: Database[Any] | None = None

    def open(self) -> None:
        """Open Mongo using the secrets URI."""
        self.close()
        self._client = MongoClient(self._secrets.mongo_uri, directConnection=True)
        self._db = self._client[self._secrets.mongo_db_name]

    def close(self) -> None:
        """Close the client if open."""
        if self._client is not None:
            try:
                self._client.close()
            except PyMongoError:
                pass
            finally:
                self._client = None
                self._db = None

    @property
    def db(self) -> Database[Any]:
        """Active Mongo database (must call ``open`` first)."""
        if self._db is None:
            raise RuntimeError("BankTransferRoutingDb not open")
        return self._db

    def snapshot_all_weights(self, agenda: str = "CASH_OUT") -> list[dict[str, Any]]:
        """Capture client weight/active rows for restore."""
        return list(
            self.db.clients.find(
                {"agenda": agenda},
                {
                    "_id": 1,
                    "clientCode": 1,
                    "bankCode": 1,
                    "serviceType": 1,
                    "selectionWeight": 1,
                    "active": 1,
                },
            )
        )

    def snapshot_accounts(self, agenda: str = "CASH_OUT") -> list[dict[str, Any]]:
        """Capture account active/clientIds rows for restore."""
        return list(
            self.db.accounts.find(
                {"agenda": agenda},
                {"_id": 1, "active": 1, "clientIds": 1},
            )
        )

    def restore_all_weights(self, snapshot: list[dict[str, Any]]) -> None:
        """Restore previously snapshotted client weights."""
        for row in snapshot:
            self.db.clients.update_one(
                {"_id": row["_id"]},
                {
                    "$set": {
                        "selectionWeight": row["selectionWeight"],
                        "active": row["active"],
                    }
                },
            )
        self.repair_stale_weights()

    def restore_accounts(self, snapshot: list[dict[str, Any]]) -> None:
        """Restore previously snapshotted account active/clientIds."""
        for row in snapshot:
            fields: dict[str, Any] = {"active": row.get("active")}
            if "clientIds" in row:
                fields["clientIds"] = row["clientIds"]
            self.db.accounts.update_one({"_id": row["_id"]}, {"$set": fields})

    def repair_stale_weights(self, agenda: str = "CASH_OUT") -> None:
        """Zero weight on inactive clients."""
        self.db.clients.update_many(
            {"agenda": agenda, "active": False, "selectionWeight": {"$ne": 0}},
            {"$set": {"selectionWeight": 0}},
        )

    def zero_all_weights(self, agenda: str = "CASH_OUT") -> None:
        """Deactivate QA gateways and zero all CASH_OUT weights."""
        self._apply_routing_layout(agenda, active=set(), weights={})
        self.wait_until_internal_weight(None)

    def pin_mellat_internal(self, weight: int = 100, agenda: str = "CASH_OUT") -> None:
        """Pin bn_mellat INTERNAL_TRANSFER weight; zero other mellat service rows."""
        self._pin_mellat_service("INTERNAL_TRANSFER", weight=weight, agenda=agenda)

    def pin_mellat_ach(self, weight: int = 100, agenda: str = "CASH_OUT") -> None:
        """Pin bn_mellat ACH_TRANSFER weight; zero other mellat service rows."""
        self._pin_mellat_service("ACH_TRANSFER", weight=weight, agenda=agenda)

    def pin_mellat_rtgs(self, weight: int = 100, agenda: str = "CASH_OUT") -> None:
        """Pin bn_mellat RTGS_TRANSFER (SATNA) weight."""
        self._pin_mellat_service("RTGS_TRANSFER", weight=weight, agenda=agenda)

    def pin_parsian_ach(self, weight: int = 100, agenda: str = "CASH_OUT") -> None:
        """Pin bn_parsian ACH as the only weighted CASH_OUT gateway."""
        self._apply_routing_layout(agenda, active={"parsian"}, weights={"parsian": weight})
        self._ensure_parsian_cash_out_client_ids()
        self._wait_named_weight("parsian", weight)

    def pin_ft_shahin_internal(self, weight: int = 100, agenda: str = "CASH_OUT") -> None:
        """Pin ft_shahin INTERNAL as the only weighted CASH_OUT gateway."""
        self._pin_ft_shahin_service("ft_shahin_internal", weight=weight, agenda=agenda)

    def pin_shahin_internal(self, weight: int = 100, agenda: str = "CASH_OUT") -> None:
        """Deprecated name. Nemo still calls this; pin ft_shahin INTERNAL."""
        self.pin_ft_shahin_internal(weight=weight, agenda=agenda)

    def pin_ft_shahin_ach(self, weight: int = 100, agenda: str = "CASH_OUT") -> None:
        """Pin ft_shahin ACH / PAYA as the only weighted CASH_OUT gateway."""
        self._pin_ft_shahin_service("ft_shahin_ach", weight=weight, agenda=agenda)

    def pin_ft_shahin_rtgs(self, weight: int = 100, agenda: str = "CASH_OUT") -> None:
        """Pin ft_shahin RTGS / SATNA as the only weighted CASH_OUT gateway."""
        self._pin_ft_shahin_service("ft_shahin_rtgs", weight=weight, agenda=agenda)

    def _pin_ft_shahin_service(
        self, gateway: str, *, weight: int = 100, agenda: str = "CASH_OUT"
    ) -> None:
        """Pin one ft_shahin CASH_OUT service; keep ACH/INTERNAL/RTGS rows active."""
        service_type = ROUTING_GATEWAYS[gateway][2]
        self.db.clients.update_many({"agenda": agenda}, {"$set": {"selectionWeight": 0}})
        self._deactivate_deprecated_shahin(agenda)
        for st in (*_FT_SHAHIN_CASH_OUT_CLIENT_IDS, "STATEMENT"):
            self._activate_client("ft_shahin", "019", st, agenda, active=True)
        self._activate_account("ft_shahin", "019", agenda, active=True)
        for st in _FT_SHAHIN_CASH_OUT_CLIENT_IDS:
            self._set_weight(
                "ft_shahin",
                "019",
                st,
                weight if st == service_type else 0,
                agenda,
            )
        self.repair_stale_weights(agenda)
        self._ensure_ft_shahin_cash_out_client_ids()
        self._wait_named_weight(gateway, weight)

    def pin_manual_ach(self, weight: int = 100, agenda: str = "CASH_OUT") -> None:
        """Pin bn_manual ACH portal as the only weighted CASH_OUT gateway."""
        self._apply_routing_layout(agenda, active={"manual"}, weights={"manual": weight})
        self._wait_named_weight("manual", weight)

    def pin_named_gateway(self, gateway: str) -> None:
        """Pin a CASH_OUT gateway from a Gherkin name (e.g. ``ft shahin PAYA``)."""
        try:
            key = PIN_GATEWAY_ALIASES[gateway]
        except KeyError as exc:
            raise KeyError(
                f"No cash-out gateway for {gateway!r}; known: {sorted(PIN_GATEWAY_ALIASES)}"
            ) from exc
        {
            "mellat": self.pin_mellat_internal,
            "mellat_ach": self.pin_mellat_ach,
            "mellat_rtgs": self.pin_mellat_rtgs,
            "parsian": self.pin_parsian_ach,
            "ft_shahin_internal": self.pin_ft_shahin_internal,
            "ft_shahin_ach": self.pin_ft_shahin_ach,
            "ft_shahin_rtgs": self.pin_ft_shahin_rtgs,
            "manual": self.pin_manual_ach,
        }[key](100)

    def split_gateway_weights(self, weights: dict[str, int], agenda: str = "CASH_OUT") -> None:
        """Activate only listed gateways with the given weights."""
        self._apply_routing_layout(agenda, active=set(weights.keys()), weights=weights)
        for name, weight in weights.items():
            self._wait_named_weight(name, weight)

    def assert_routing_consistent(self, agenda: str = "CASH_OUT") -> None:
        """Inactive clients must not carry non-zero weight."""
        stale = list(
            self.db.clients.find(
                {"agenda": agenda, "active": False, "selectionWeight": {"$ne": 0}},
                {
                    "clientCode": 1,
                    "bankCode": 1,
                    "serviceType": 1,
                    "selectionWeight": 1,
                },
            )
        )
        if stale:
            raise AssertionError(f"inactive clients with non-zero weight: {stale}")

    def manual_rtgs_row(self, agenda: str = "CASH_OUT") -> dict[str, Any] | None:
        """bn_manual RTGS_TRANSFER client row (must stay inactive)."""
        return self.db.clients.find_one(
            {
                "agenda": agenda,
                "clientCode": "bn_manual",
                "bankCode": "MANUAL",
                "serviceType": "RTGS_TRANSFER",
            },
            {"active": 1, "selectionWeight": 1, "serviceType": 1},
        )

    def simulate_manual_settle(
        self,
        tracking_code: str,
        *,
        mongo_status: str = "DONE",
        tx_status: str = "ACCEPTED",
    ) -> dict[str, Any]:
        """Snapshot the row, then mark it DONE / ACCEPTED."""
        doc = self.find_transfer(tracking_code)
        if doc is None:
            raise AssertionError(f"{tracking_code} missing in ach_transfers")
        before = dict(doc)
        txs = [dict(doc["transactions"][0])] if doc.get("transactions") else []
        if txs:
            txs[0]["status"] = tx_status
        self.db.ach_transfers.update_one(
            {"trackingCode": tracking_code},
            {"$set": {"status": mongo_status, "transactions": txs}},
        )
        return before

    def qa_restore_transfer_doc(self, tracking_code: str, snapshot: dict[str, Any]) -> None:
        """Put the ach_transfers document back after a settle simulation."""
        self.db.ach_transfers.replace_one({"trackingCode": tracking_code}, snapshot)

    def _pin_mellat_service(
        self, service_type: str, *, weight: int = 100, agenda: str = "CASH_OUT"
    ) -> None:
        """Pin one Mellat service type; keep all Mellat rows active."""
        self.db.clients.update_many({"agenda": agenda}, {"$set": {"selectionWeight": 0}})
        for st in _MELLAT_SERVICE_TYPES:
            self._activate_client("bn_mellat", "012", st, agenda, active=True)
        self._activate_account("bn_mellat", "012", agenda, active=True)
        for st in _MELLAT_SERVICE_TYPES:
            self._set_weight(
                "bn_mellat",
                "012",
                st,
                weight if st == service_type else 0,
                agenda,
            )
        self.repair_stale_weights(agenda)
        self._ensure_mellat_cash_out_client_ids()
        self.wait_until_service_weight(service_type, weight)

    def layout_mellat_inactive_internal(self, agenda: str = "CASH_OUT") -> None:
        """Inactive mellat INTERNAL row with stale non-zero weight (negative route)."""
        self._apply_routing_layout(agenda, active=set(), weights={})
        self.db.clients.update_many(
            {
                "agenda": agenda,
                "clientCode": "bn_mellat",
                "bankCode": "012",
                "serviceType": "INTERNAL_TRANSFER",
            },
            {"$set": {"active": False, "selectionWeight": 100}},
        )
        self.wait_until_internal_weight(None)

    def find_transfer(self, tracking_code: str) -> dict[str, Any] | None:
        """Load ach_transfers row by tracking code."""
        return self.db.ach_transfers.find_one({"trackingCode": tracking_code}, {"_id": 0})

    def count_transfers(self, tracking_code: str) -> int:
        """Count ach_transfers rows for a tracking code."""
        return int(self.db.ach_transfers.count_documents({"trackingCode": tracking_code}))

    def mellat_internal_client_row(self) -> dict[str, Any] | None:
        """Active Mellat INTERNAL CASH_OUT client row."""
        return self.db.clients.find_one(
            {
                "agenda": "CASH_OUT",
                "clientCode": "bn_mellat",
                "bankCode": "012",
                "serviceType": "INTERNAL_TRANSFER",
                "active": True,
            },
            {"selectionWeight": 1, "active": 1, "clientCode": 1, "bankCode": 1},
        )

    def client_internal_weight(self) -> int | None:
        """Current active bn_mellat INTERNAL_TRANSFER selectionWeight."""
        return self.client_service_weight("INTERNAL_TRANSFER")

    def client_service_weight(self, service_type: str) -> int | None:
        """Active bn_mellat selectionWeight for a service type."""
        return self._active_client_weight("bn_mellat", "012", service_type)

    def wait_until_internal_weight(self, expected: int | None) -> None:
        """Poll until Mellat INTERNAL active weight matches ``expected``."""
        self.wait_until_service_weight("INTERNAL_TRANSFER", expected)

    def wait_until_service_weight(self, service_type: str, expected: int | None) -> None:
        """Poll until Mellat ``service_type`` weight matches ``expected`` (None=inactive)."""
        self.wait_until_client_weight("bn_mellat", "012", service_type, expected)

    def wait_until_client_weight(
        self,
        client_code: str,
        bank_code: str,
        service_type: str,
        expected: int | None,
        *,
        agenda: str = "CASH_OUT",
    ) -> None:
        """Poll until an active client weight matches ``expected`` (None=inactive)."""
        timeout = max(float(self._secrets.routing_settle_seconds) * 8.0, 4.0)
        deadline = time.monotonic() + timeout
        last: int | None = None
        while time.monotonic() < deadline:
            last = self._active_client_weight(client_code, bank_code, service_type, agenda)
            if expected is None and last is None:
                return
            if expected is not None and last == expected:
                return
            time.sleep(_POLL_INTERVAL_SEC)
        raise TimeoutError(
            f"{client_code} {service_type} weight did not become {expected!r} "
            f"within {timeout:.1f}s (last={last!r})"
        )

    def _wait_named_weight(self, name: str, weight: int) -> None:
        client_code, bank_code, service_type = ROUTING_GATEWAYS[name]
        self.wait_until_client_weight(client_code, bank_code, service_type, weight)

    def _active_client_weight(
        self,
        client_code: str,
        bank_code: str,
        service_type: str,
        agenda: str = "CASH_OUT",
    ) -> int | None:
        row = self.db.clients.find_one(
            {
                "agenda": agenda,
                "clientCode": client_code,
                "bankCode": bank_code,
                "serviceType": service_type,
                "active": {"$in": _ACTIVE_TRUE},
            },
            {"selectionWeight": 1},
        )
        if row is None:
            return None
        weight = row.get("selectionWeight")
        return int(weight) if weight is not None else None

    def _apply_routing_layout(
        self,
        agenda: str,
        *,
        active: set[str],
        weights: dict[str, int],
    ) -> None:
        self.db.clients.update_many({"agenda": agenda}, {"$set": {"selectionWeight": 0}})
        self._deactivate_deprecated_shahin(agenda)
        for name, (client_code, bank_code, service_type) in ROUTING_GATEWAYS.items():
            is_active = name in active
            self._activate_client(client_code, bank_code, service_type, agenda, active=is_active)
            if is_active:
                self._activate_account(client_code, bank_code, agenda, active=True)
        self._activate_client("bn_manual", "MANUAL", "RTGS_TRANSFER", agenda, active=False)
        for name, weight in weights.items():
            client_code, bank_code, service_type = ROUTING_GATEWAYS[name]
            self._set_weight(client_code, bank_code, service_type, weight, agenda)
        self.repair_stale_weights(agenda)

    def _activate_client(
        self,
        client_code: str,
        bank_code: str,
        service_type: str,
        agenda: str,
        *,
        active: bool,
    ) -> None:
        fields: dict[str, Any] = {"active": active}
        if not active:
            fields["selectionWeight"] = 0
        self.db.clients.update_many(
            {
                "agenda": agenda,
                "clientCode": client_code,
                "bankCode": bank_code,
                "serviceType": service_type,
            },
            {"$set": fields},
        )

    def _activate_account(
        self, client_code: str, bank_code: str, agenda: str, *, active: bool
    ) -> None:
        self.db.accounts.update_many(
            {"clientCode": client_code, "bankCode": bank_code, "agenda": agenda},
            {"$set": {"active": active}},
        )

    def _set_weight(
        self,
        client_code: str,
        bank_code: str,
        service_type: str,
        weight: int,
        agenda: str,
    ) -> None:
        filt: dict[str, Any] = {
            "agenda": agenda,
            "clientCode": client_code,
            "bankCode": bank_code,
            "serviceType": service_type,
        }
        if weight > 0:
            filt["active"] = {"$in": _ACTIVE_TRUE}
        self.db.clients.update_many(filt, {"$set": {"selectionWeight": weight}})

    def _ensure_mellat_cash_out_client_ids(self) -> None:
        account_number = self._secrets.mellat_account_number
        variants = {
            account_number,
            account_number.lstrip("0") or account_number,
            account_number.zfill(13),
        }
        acct = self.db.accounts.find_one(
            {
                "clientCode": "bn_mellat",
                "bankCode": "012",
                "agenda": "CASH_OUT",
                "accountNumber": {"$in": list(variants)},
            }
        )
        if acct is None:
            raise RuntimeError("no mellat CASH_OUT account for clientIds align")
        want = list(_MELLAT_CASH_OUT_CLIENT_IDS.values())
        have = list(acct.get("clientIds") or [])
        if sorted(have) != sorted(want):
            self.db.accounts.update_one({"_id": acct["_id"]}, {"$set": {"clientIds": want}})

    def _ensure_parsian_cash_out_client_ids(self) -> None:
        acct_no = self._secrets.parsian_account_number
        variants = {acct_no, acct_no.lstrip("0") or acct_no, acct_no.zfill(13)}
        acct = self.db.accounts.find_one(
            {
                "clientCode": "bn_parsian",
                "bankCode": "054",
                "agenda": "CASH_OUT",
                "accountNumber": {"$in": list(variants)},
            }
        )
        if acct is None:
            return
        want = list(_PARSIAN_CASH_OUT_CLIENT_IDS.values())
        if sorted(list(acct.get("clientIds") or [])) != sorted(want):
            self.db.accounts.update_one({"_id": acct["_id"]}, {"$set": {"clientIds": want}})

    def _deactivate_deprecated_shahin(self, agenda: str) -> None:
        """Zero the retired ``shahin`` client so it cannot steal CASH_OUT weight."""
        self.db.clients.update_many(
            {"agenda": agenda, "clientCode": "shahin"},
            {"$set": {"active": False, "selectionWeight": 0}},
        )
        self.db.accounts.update_many(
            {"agenda": agenda, "clientCode": "shahin"},
            {"$set": {"active": False}},
        )

    def _ensure_ft_shahin_cash_out_client_ids(self) -> None:
        """Set ft_shahin CASH_OUT account clientIds to ACH/INTERNAL/RTGS/STATEMENT."""
        acct = self.db.accounts.find_one(self._ft_shahin_cash_out_account_filter())
        if acct is None:
            raise RuntimeError(
                f"no ft_shahin CASH_OUT account {self._secrets.ft_shahin_account_number!r}"
            )
        want = [
            *_FT_SHAHIN_CASH_OUT_CLIENT_IDS.values(),
            _FT_SHAHIN_CASH_OUT_STATEMENT_ID,
            *_FT_SHAHIN_TREASURY_CLIENT_IDS.values(),
            _FT_SHAHIN_TREASURY_STATEMENT_ID,
        ]
        want = list(dict.fromkeys(want))
        if sorted(int(x) for x in (acct.get("clientIds") or [])) != sorted(want):
            self.db.accounts.update_one({"_id": acct["_id"]}, {"$set": {"clientIds": want}})
        self._wait_account_client_ids(
            self._ft_shahin_cash_out_account_filter(), want, "ft_shahin CASH_OUT"
        )

    def ensure_mellat_cash_out_client_ids(self) -> None:
        """Public alias to realign Mellat CASH_OUT account clientIds."""
        self._ensure_mellat_cash_out_client_ids()

    def snapshot_melli_direct_accounts(self) -> list[dict[str, Any]]:
        """Snapshot Melli TREASURY account docs for restore."""
        return list(self.db.accounts.find(self._melli_direct_account_filter()))

    def restore_account_docs(self, snap: list[dict[str, Any]]) -> None:
        """Replace account documents from a snapshot."""
        for doc in snap:
            self.db.accounts.replace_one({"_id": doc["_id"]}, doc)

    def snapshot_mellat_direct_accounts(self) -> list[dict[str, Any]]:
        """Snapshot Mellat CASH_OUT account docs (clientIds) for restore."""
        return list(self.db.accounts.find(self._mellat_cash_out_account_filter()))

    def ensure_melli_direct_ready(self) -> None:
        """Activate bn_melli TREASURY ACH/INTERNAL/RTGS; clientIds [105,125,13]."""
        for service_type in _MELLI_DIRECT_CLIENT_IDS:
            self._activate_client("bn_melli", "017", service_type, TREASURY_AGENDA, active=True)
        self._activate_account("bn_melli", "017", TREASURY_AGENDA, active=True)
        want = list(_MELLI_DIRECT_CLIENT_IDS.values())
        acct = self.db.accounts.find_one(self._melli_direct_account_filter())
        if acct is None:
            raise RuntimeError(
                "melli direct-route: no TREASURY account "
                f"{self._secrets.melli_direct_account_number!r}"
            )
        if sorted(list(acct.get("clientIds") or [])) != sorted(want):
            self.db.accounts.update_one({"_id": acct["_id"]}, {"$set": {"clientIds": want}})
        self._wait_account_client_ids(self._melli_direct_account_filter(), want, "melli TREASURY")

    def ensure_mellat_direct_ready(self) -> None:
        """Activate bn_mellat TREASURY clients; CASH_OUT account clientIds [115,116,117]."""
        for service_type in _MELLAT_DIRECT_CLIENT_IDS:
            self._activate_client("bn_mellat", "012", service_type, TREASURY_AGENDA, active=True)
        self._activate_account("bn_mellat", "012", "CASH_OUT", active=True)
        want = list(_MELLAT_DIRECT_CLIENT_IDS.values())
        acct = self.db.accounts.find_one(self._mellat_cash_out_account_filter())
        if acct is None:
            raise RuntimeError(
                f"mellat direct-route: no CASH_OUT account {self._secrets.mellat_account_number!r}"
            )
        if sorted(list(acct.get("clientIds") or [])) != sorted(want):
            self.db.accounts.update_one({"_id": acct["_id"]}, {"$set": {"clientIds": want}})
        self.wait_until_mellat_cash_out_client_ids(want)

    def set_melli_direct_client_ids(self, client_ids: list[int]) -> None:
        """Override Melli TREASURY account clientIds."""
        result = self.db.accounts.update_many(
            self._melli_direct_account_filter(),
            {"$set": {"clientIds": client_ids}},
        )
        if result.matched_count < 1:
            raise RuntimeError("melli direct-route account not found for clientIds set")

    def set_mellat_direct_client_ids(self, client_ids: list[int]) -> None:
        """Override Mellat CASH_OUT account clientIds (direct-route rails)."""
        result = self.db.accounts.update_many(
            self._mellat_cash_out_account_filter(),
            {"$set": {"clientIds": client_ids}},
        )
        if result.matched_count < 1:
            raise RuntimeError("mellat direct-route account not found for clientIds set")

    def wait_until_mellat_cash_out_client_ids(self, client_ids: list[int]) -> None:
        """Poll until Mellat CASH_OUT account clientIds match ``client_ids``."""
        self._wait_account_client_ids(
            self._mellat_cash_out_account_filter(),
            client_ids,
            "mellat CASH_OUT",
        )

    def _wait_account_client_ids(
        self,
        filt: dict[str, Any],
        client_ids: list[int],
        label: str,
    ) -> None:
        want = sorted(int(x) for x in client_ids)
        timeout = max(float(self._secrets.routing_settle_seconds) * 8.0, 4.0)
        deadline = time.monotonic() + timeout
        last: list[Any] = []
        while time.monotonic() < deadline:
            acct = self.db.accounts.find_one(filt)
            last = list((acct or {}).get("clientIds") or [])
            if sorted(int(x) for x in last) == want:
                return
            time.sleep(_POLL_INTERVAL_SEC)
        raise TimeoutError(
            f"{label} clientIds did not become {want} within {timeout:.1f}s (last={last!r})"
        )

    def deactivate_melli_treasury_ach(self) -> None:
        """Inactive Melli TREASURY ACH client (negative path)."""
        self._activate_client("bn_melli", "017", "ACH_TRANSFER", TREASURY_AGENDA, active=False)

    def _melli_direct_account_filter(self) -> dict[str, Any]:
        acct = self._secrets.melli_direct_account_number
        variants = {acct, acct.lstrip("0") or acct, acct.zfill(13)}
        return {
            "clientCode": "bn_melli",
            "bankCode": "017",
            "agenda": TREASURY_AGENDA,
            "accountNumber": {"$in": list(variants)},
        }

    def _mellat_cash_out_account_filter(self) -> dict[str, Any]:
        acct = self._secrets.mellat_account_number
        variants = {acct, acct.lstrip("0") or acct, acct.zfill(13)}
        return {
            "clientCode": "bn_mellat",
            "bankCode": "012",
            "agenda": "CASH_OUT",
            "accountNumber": {"$in": list(variants)},
        }

    def snapshot_saderat_direct_accounts(self) -> list[dict[str, Any]]:
        """Snapshot ft_shahin CASH_OUT account docs (treasury clientIds live here)."""
        return list(self.db.accounts.find(self._ft_shahin_cash_out_account_filter()))

    def ensure_saderat_direct_ready(self) -> None:
        """Activate TREASURY 205/206/207 on the CASH_OUT account (no TREASURY account)."""
        for service_type in _FT_SHAHIN_TREASURY_CLIENT_IDS:
            self._activate_client("ft_shahin", "019", service_type, TREASURY_AGENDA, active=True)
        self._activate_account("ft_shahin", "019", "CASH_OUT", active=True)
        want = [
            *_FT_SHAHIN_TREASURY_CLIENT_IDS.values(),
            _FT_SHAHIN_TREASURY_STATEMENT_ID,
        ]
        acct = self.db.accounts.find_one(self._ft_shahin_cash_out_account_filter())
        if acct is None:
            raise RuntimeError(
                "saderat direct-route: no CASH_OUT account "
                f"{self._secrets.ft_shahin_account_number!r}"
            )
        if sorted(list(acct.get("clientIds") or [])) != sorted(want):
            self.db.accounts.update_one({"_id": acct["_id"]}, {"$set": {"clientIds": want}})
        self._wait_account_client_ids(
            self._ft_shahin_cash_out_account_filter(), want, "ft_shahin CASH_OUT treasury ids"
        )

    def set_saderat_direct_client_ids(self, client_ids: list[int]) -> None:
        """Override ft_shahin CASH_OUT account clientIds for treasury negatives."""
        result = self.db.accounts.update_many(
            self._ft_shahin_cash_out_account_filter(),
            {"$set": {"clientIds": client_ids}},
        )
        if result.matched_count < 1:
            raise RuntimeError("saderat direct-route account not found for clientIds set")
        self._wait_account_client_ids(
            self._ft_shahin_cash_out_account_filter(),
            client_ids,
            "ft_shahin CASH_OUT treasury ids",
        )

    def deactivate_saderat_treasury_ach(self) -> None:
        """Inactive ft_shahin TREASURY ACH client (negative path)."""
        self._activate_client("ft_shahin", "019", "ACH_TRANSFER", TREASURY_AGENDA, active=False)

    def activate_ft_shahin_statement(self) -> None:
        """Activate ft_shahin STATEMENT client 204 on CASH_OUT."""
        self._activate_client("ft_shahin", "019", "STATEMENT", "CASH_OUT", active=True)

    def _ft_shahin_cash_out_account_filter(self) -> dict[str, Any]:
        acct = self._secrets.ft_shahin_account_number
        variants = {acct, acct.lstrip("0") or acct, acct.zfill(13)}
        return {
            "clientCode": "ft_shahin",
            "bankCode": "019",
            "agenda": "CASH_OUT",
            "accountNumber": {"$in": list(variants)},
        }
