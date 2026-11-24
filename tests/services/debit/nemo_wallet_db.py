"""Nemo wallet_db helpers for cash-out register cleanup."""

from __future__ import annotations

import logging
import time
from typing import Any

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from tests.services.debit.nemo_secrets import NemoSecrets

logger = logging.getLogger(__name__)

OPEN_CASH_OUT_STATUSES = frozenset({0, 1, 2, 3, 4, 7})
OPEN_TRANSFER_STATUSES = frozenset({0, 1, 2, 21, 25})
QA_CLEANUP_CASH_OUT_STATUS = 22  # REJECTED
TERMINAL_TRANSFER_STATUS = 6
KYC_BLOCK_STATUSES = frozenset({2, 25})  # KYC_REQUIRED, KYC_REJECTED
CASH_OUT_SETTLED = 5
CASH_OUT_CONFIRMED = 21


class NemoWalletDb:
    """Class + fixture Mongo access to wallet_db cash_outs / transfers."""

    def __init__(self, secrets: NemoSecrets) -> None:
        self._secrets = CHANGE_ME
        self._client: MongoClient[Any] | None = None
        self._db: Database[Any] | None = None

    def open(self) -> None:
        """Connect to wallet Mongo."""
        uri = (self._secrets.mongo_uri or "").strip()
        if not uri:
            raise RuntimeError("nemo mongo_uri is required for wallet_db")
        self._client = MongoClient(uri, directConnection=True)
        self._db = self._client[self._secrets.mongo_db_name]

    def close(self) -> None:
        """Close Mongo client."""
        if self._client is not None:
            self._client.close()
        self._client = None
        self._db = None

    @property
    def db(self) -> Database[Any]:
        """Opened wallet database."""
        if self._db is None:
            raise RuntimeError("NemoWalletDb is not open")
        return self._db

    def find_cash_out(self, tracking_code: str) -> dict[str, Any] | None:
        """Load cash_outs row by tracking code."""
        return self.db.cash_outs.find_one({"trackingCode": tracking_code})

    def count_cash_outs_for_user(self, user_id: str | None = None) -> int:
        """Count cash_outs for the Nemo user."""
        uid = user_id or self._secrets.user_id
        return int(self.db.cash_outs.count_documents({"owner.userId": uid}))

    def count_open_cash_outs(self, user_id: str | None = None) -> int:
        """Count in-flight cash_outs that block new register."""
        uid = user_id or self._secrets.user_id
        return int(
            self.db.cash_outs.count_documents(
                {
                    "owner.userId": uid,
                    "status": {"$in": list(OPEN_CASH_OUT_STATUSES)},
                }
            )
        )

    def count_open_transfers(self, user_id: str | None = None) -> int:
        """Count open P2P transfers that block register."""
        uid = user_id or self._secrets.user_id
        return int(
            self.db.transfers.count_documents(
                {
                    "owner.userId": uid,
                    "status": {"$in": list(OPEN_TRANSFER_STATUSES)},
                }
            )
        )

    def close_open_settlements(self, user_id: str | None = None) -> dict[str, int]:
        """QA-reject open cash_outs and close open transfers."""
        uid = user_id or self._secrets.user_id
        now_ms = int(time.time() * 1000)
        message = "QA cleanup - closed open settlement for automated tests"
        try:
            co = self.db.cash_outs.update_many(
                {
                    "owner.userId": uid,
                    "status": {"$in": list(OPEN_CASH_OUT_STATUSES)},
                },
                {
                    "$set": {
                        "status": QA_CLEANUP_CASH_OUT_STATUS,
                        "statusChangeDate": now_ms,
                        "message": message,
                    }
                },
            )
            tr = self.db.transfers.update_many(
                {
                    "owner.userId": uid,
                    "status": {"$in": list(OPEN_TRANSFER_STATUSES)},
                },
                {
                    "$set": {
                        "status": TERMINAL_TRANSFER_STATUS,
                        "statusChangeDate": now_ms,
                        "message": message,
                    }
                },
            )
        except PyMongoError as exc:
            logger.warning("nemo wallet cleanup failed: %s", exc)
            return {"cash_outs": 0, "transfers": 0}
        return {
            "cash_outs": int(co.modified_count),
            "transfers": int(tr.modified_count),
        }

    def assert_no_blocking_settlement(self, user_id: str | None = None) -> None:
        """Fail fast when open settlements remain."""
        open_co = self.count_open_cash_outs(user_id)
        open_tr = self.count_open_transfers(user_id)
        if open_co or open_tr:
            raise AssertionError(
                f"{open_co} in-flight cash_out(s), {open_tr} open transfer(s) — "
                "register returns PEPE_CASHOUT_MULTIPLE_SETTLEMENT_NOT_ALLOWED"
            )

    def assert_cash_out_persisted(
        self,
        tracking_code: str,
        *,
        amount: int | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Require cash_outs row for tracking code."""
        doc = self.find_cash_out(tracking_code)
        if doc is None:
            raise AssertionError(
                f"cash_outs missing trackingCode={tracking_code} in "
                f"{self._secrets.mongo_db_name}"
            )
        uid = user_id or self._secrets.user_id
        owner = doc.get("owner") or {}
        if owner.get("userId") != uid:
            raise AssertionError(
                f"owner.userId mismatch: {owner.get('userId')} != {uid}"
            )
        if amount is not None and doc.get("amount") != amount:
            raise AssertionError(
                f"amount mismatch: {doc.get('amount')} != {amount}"
            )
        return doc

    def latest_cash_out_kyc_blocked(self, user_id: str | None = None) -> bool:
        """Whether the latest cash_out is KYC_REQUIRED / KYC_REJECTED."""
        uid = user_id or self._secrets.user_id
        latest = self.db.cash_outs.find_one(
            {"owner.userId": uid},
            sort=[("creationDate", -1)],
        )
        if latest is None:
            return False
        return latest.get("status") in KYC_BLOCK_STATUSES

    def assert_manual_settlement(self, tracking_code: str) -> dict[str, Any]:
        """Cash-out reached scheduler success after the portal row went DONE."""
        doc = self.find_cash_out(tracking_code)
        if doc is None:
            raise AssertionError(f"cash_outs missing trackingCode={tracking_code}")
        prev = doc.get("previousStatus")
        status = doc.get("status")
        if prev != CASH_OUT_SETTLED:
            raise AssertionError(
                f"{tracking_code}: previousStatus={prev} (want SETTLED={CASH_OUT_SETTLED})"
            )
        if status not in (CASH_OUT_CONFIRMED, CASH_OUT_SETTLED):
            raise AssertionError(
                f"{tracking_code}: cash_out.status={status} "
                f"(want CONFIRMED or SETTLED)"
            )
        return doc
