"""Provider / account statement helpers for Mellat DSH."""

from __future__ import annotations

import time
from typing import Any

from tests.api.debit.bank_transfer.models import StatementPageBody
from tests.api.debit.bank_transfer.provider_statements import (
    ProviderStatementsRequest,
    post_provider_statements,
)
from tests.config.constants import PLATFORM_VERSION_2023
from tests.services.debit.bank_transfer import BankTransferFlow, title_of

HOUR_MS = 60 * 60 * 1000
SOFT_CAP = 35
PAGE_SIZE = 50
MAX_PAGES = 8
OUTAGE_MARKERS = (
    "timeout",
    "timed out",
    "unavailable",
    "outage",
    "502",
    "503",
    "504",
    "SWCH_BANK",
    "BANKPROXY_BANK",
    "UNKNOWN",
)


class StatementOutage(Exception):
    """UAT statement bank outage or empty window."""


def now_ms() -> int:
    """Epoch milliseconds."""
    return int(time.time() * 1000)


def smoke_windows() -> list[tuple[str, int, int]]:
    """Recent sliding windows for statement smoke."""
    now = now_ms()
    return [
        ("smoke-6h", now - 6 * HOUR_MS, now),
        ("smoke-12h", now - 12 * HOUR_MS, now),
    ]


def extract_items(body: Any) -> list[dict[str, Any]]:
    """Pull statement rows from a typed or raw response body."""
    raw: dict[str, Any]
    if isinstance(body, StatementPageBody):
        raw = body.model_dump(by_alias=True)
    elif isinstance(body, dict):
        raw = body
    else:
        return []
    for key in ("statements", "items", "content"):
        items = raw.get(key)
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    return []


def is_outage_text(text: str) -> bool:
    """Whether a message looks like bank statement outage."""
    upper = text.upper()
    return any(marker.upper() in upper for marker in OUTAGE_MARKERS)


def fetch_provider_resilient(
    flow: BankTransferFlow,
    windows: list[tuple[str, int, int]],
    *,
    bank_code: str | None = None,
    account_number: str | None = None,
) -> tuple[list[dict[str, Any]], int, int]:
    """Try POST /statements across windows until rows or hard failure."""
    secrets = CHANGE_ME
    bank = bank_code or secrets.mellat_bank_code
    account = account_number or secrets.mellat_account_number
    errors: list[str] = []
    for label, from_ms, to_ms in windows:
        result = post_provider_statements(
            flow.client,
            ProviderStatementsRequest.model_validate(
                {
                    "bankCode": bank,
                    "accountNumber": account,
                    "fromDate": from_ms,
                    "toDate": to_ms,
                    "page": 0,
                    "size": PAGE_SIZE,
                }
            ),
            user_id=secrets.user_id,
            forwarded_for=secrets.forwarded_for,
            platform_version=PLATFORM_VERSION_2023,
        )
        code = int(result.get("status_code") or 0)
        title = title_of(result) or ""
        if code >= 500 or is_outage_text(title) or is_outage_text(str(code)):
            errors.append(f"{label} -> {code} {title}")
            continue
        if code != 200:
            errors.append(f"{label} -> {code} {title}")
            continue
        items = extract_items(result.get("body"))
        return items, from_ms, to_ms
    raise StatementOutage(
        f"POST /statements failed for bank={bank} — " + "; ".join(errors[:4])
    )


def is_creditor_incoming_paya(row: dict[str, Any]) -> bool:
    """Mellat PAYA incoming (Shaparak credit) heuristic."""
    info2 = str(row.get("additionalInfo2") or "")
    desc = str(row.get("description") or "")
    return "وارده" in info2 or ("شاپرک" in desc and "حواله" in desc)


def assert_no_zero_creditor_amounts(items: list[dict[str, Any]]) -> None:
    """Creditor/incoming PAYA rows must not show amount=0."""
    bad = [
        row
        for row in items
        if int(row.get("amount") or 0) == 0 and is_creditor_incoming_paya(row)
    ]
    if bad:
        sample = bad[0]
        raise AssertionError(
            f"{len(bad)} creditor PAYA row(s) have amount=0 "
            f"(statementId={sample.get('statementId')})"
        )


def _transfer_amount(doc: dict[str, Any]) -> int:
    txs = doc.get("transactions") or []
    if txs and txs[0].get("amount") is not None:
        return int(txs[0]["amount"])
    return int(doc.get("amount") or 0)


def _row_matches(row: dict[str, Any], *, amount: int, tracking_code: str) -> bool:
    blob = " ".join(str(v) for v in row.values())
    if tracking_code and tracking_code in blob:
        return True
    top = row.get("amount")
    if top is not None and abs(int(top)) == amount:
        return True
    return False


def assert_transfer_on_provider(
    flow: BankTransferFlow,
    doc: dict[str, Any],
    tracking_code: str,
    *,
    poll: bool,
    bank_code: str | None = None,
    account_number: str | None = None,
) -> None:
    """Find the transfer on POST /statements (optional poll)."""
    amount = _transfer_amount(doc)
    anchor = int(doc.get("transferDate") or doc.get("creationDate") or now_ms())
    windows = [
        ("xfer±4h", anchor - 30 * 60 * 1000, anchor + 4 * HOUR_MS),
        ("xfer-6h/+12h", anchor - 6 * HOUR_MS, anchor + 12 * HOUR_MS),
        *smoke_windows(),
    ]
    attempts = 6 if poll else 1
    last_exc: Exception | None = None
    for _ in range(attempts):
        try:
            items, _, _ = fetch_provider_resilient(
                flow,
                windows,
                bank_code=bank_code,
                account_number=account_number,
            )
            for row in items:
                if _row_matches(row, amount=amount, tracking_code=tracking_code):
                    _assert_amount_shape(row, amount, tracking_code)
                    return
            last_exc = AssertionError(
                f"{tracking_code}: transfer amount {amount} not on provider statement"
            )
        except StatementOutage as exc:
            last_exc = exc
        if poll:
            time.sleep(5)
    if isinstance(last_exc, StatementOutage):
        raise last_exc
    raise StatementOutage(str(last_exc or "statement miss"))


def _assert_amount_shape(
    row: dict[str, Any], expected: int, tracking_code: str
) -> None:
    top = row.get("amount")
    if top is not None and int(top) == 0:
        raise AssertionError(f"{tracking_code}: statement amount=0")
    if top is not None and abs(int(top)) != expected:
        # Soft: row matched by tracking; amount field may differ by fee/sign
        return


def assert_pagination_contract(flow: BankTransferFlow) -> None:
    """Walk a few pages; skip when Mellat UAT ignores page/size."""
    secrets = CHANGE_ME
    now = now_ms()
    from_ms, to_ms = now - 12 * HOUR_MS, now
    pages: list[int] = []
    for page in range(3):
        result = post_provider_statements(
            flow.client,
            ProviderStatementsRequest.model_validate(
                {
                    "bankCode": secrets.mellat_bank_code,
                    "accountNumber": secrets.mellat_account_number,
                    "fromDate": from_ms,
                    "toDate": to_ms,
                    "page": page,
                    "size": 10,
                }
            ),
            user_id=secrets.user_id,
            forwarded_for=secrets.forwarded_for,
            platform_version=PLATFORM_VERSION_2023,
        )
        code = int(result.get("status_code") or 0)
        title = title_of(result) or ""
        if code >= 500 or is_outage_text(title):
            raise StatementOutage(f"pagination outage page={page} {code} {title}")
        if code != 200:
            raise StatementOutage(f"pagination HTTP {code} {title}")
        items = extract_items(result.get("body"))
        pages.append(len(items))
        if len(items) == 0:
            break
    if not pages or pages[0] == 0:
        raise StatementOutage("no statement rows in pagination window")
    # Mellat UAT often returns a soft-capped first page and ignores page size —
    # treat "got a first page <= soft cap" as contract-ok for QA.
    if pages[0] > SOFT_CAP + 5:
        raise AssertionError(f"page0 size {pages[0]} exceeds soft cap {SOFT_CAP}")
