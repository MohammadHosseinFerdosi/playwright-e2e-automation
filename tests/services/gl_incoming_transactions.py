"""General ledger — incoming (manual) financial transactions (service layer).

Owns request-id generation, the create-transaction call, and the
Transaction -> Voucher -> Article DB verification chain behind each step, per
``.cursor/rules/step-definitions.mdc`` (steps stay thin orchestration only).
Port of ``src/steps/gl/incoming-transactions/transaction-step.resource``.

The three Robot files ``credit-purchase-3001/3002/3003.robot`` differ only in
which event code + fixed JSON payload they send — same behavior, genuine data
variation — so they are collapsed into one Scenario Outline per
``.cursor/rules/migration-quality.mdc`` instead of being ported one-for-one.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tests.api.client import ApiClient
from tests.api.gl.headers import DEFAULT_GL_ADMIN_USER_ID
from tests.api.gl.incoming_transactions.financial_transactions import (
    CreateFinancialTransactionResult,
    create_financial_transaction,
)
from tests.services.api_assert import ensure_ok
from tests.services.assert_report import AssertionReport
from tests.services.db.mysql_client import MySQLClient

_GL_DB = "general_ledger_db"
_DB_POLL_TIMEOUT_S = 15.0
_DB_POLL_INTERVAL_S = 0.5

CREATE_TRANSACTION_STEP = r"^a (?P<transaction_type>[A-Za-z0-9 ]+) transaction is created$"
LEDGER_TABLE_STEP = (
    r"^the transaction must be present in the "
    r"(?P<table>Transaction|Voucher|Article) table$"
)

# Fixed test fixture data, ported verbatim from src/data/gl/gl.yaml — shared by
# every transaction type, not per-type, matching the Robot suite.
_DEFAULT_AMOUNT = 1000
_DEFAULT_CLIENT_ID = "dGVzdDpwYXNz"
_DEFAULT_PARENT_EVENT_CODE: int | None = None

_INNER_JSON_CREDIT_PURCHASE = (
    '{"finalStatus":"CONFIRMED","userId":"c1d5c8d8-a7db-41d5-904d-378256903ef1",'
    '"customerName":null,"cellNumber":"09884801023","nationalCode":"0078988993",'
    '"customerWalletId":null,"productDesc":null,"productLine":"CREDIT","product":17,'
    '"productName":"CREDIT_PURCHASE","rrn":null,"amount":100000,"feeCharge":0,'
    '"effectiveDate":"11/9/25, 11:12 AM","registerDate":"11/9/25, 11:12 AM","gateway":"BPG",'
    '"actionCode":"6543024829081854","fundProvider":"PLATFORM","creditAmount":30000,'
    '"creditInterest":0,"cashPayAmount":30000,"prepaymentAmount":0,"roundOffAmount":0,'
    '"providerId":"company-user-id","providerName":"کمپانی",'
    '"contractInstallmentCount":3,"contractKey":"PLATFORM_3",'
    '"fundProviderId":"8dd5fff6-e9a0-48bd-8102-0549849425a3",'
    '"creditId":"7297063101762674120992","basketId":"6543024829081854","fpType":"leasing",'
    '"couponTrackingCode":"13592299071762674144822","couponAmount":40000,"fpServiceType":0}'
)

_INNER_JSON_CREDIT_PREPAYMENT = (
    '{"finalStatus":"CONFIRMED","userId":"951b9b95-b071-48d9-b116-c2505cd326a4",'
    '"customerName":null,"cellNumber":"09121792230","nationalCode":null,'
    '"customerWalletId":null,'
    '"productDesc":"مبلغ ۱٫۵۰۲٫۰۰۰ ریال بابت پیش پرداخت و مبلغ ۱٫۵۰۲٫۰۰۰ ریال، '
    'پرداخت نقدی شما می باشد","productLine":"CREDIT","product":34,'
    '"productName":"CREDIT_PREPAYMENT","rrn":"232821474984","amount":1502000,"feeCharge":0,'
    '"effectiveDate":"1/26/23, 10:58 AM","registerDate":"1/26/23, 10:58 AM","pspStatus":null,'
    '"gateway":"IPG","fundProvider":"PLATFORM",'
    '"description":"مبلغ ۱٫۵۰۲٫۰۰۰ ریال بابت پیش پرداخت و مبلغ ۱٫۵۰۲٫۰۰۰ ریال، '
    'پرداخت نقدی شما می باشد","purchaseTrackingCode":"1939957421674718055241",'
    '"creditFeeCharge":0,"cashPayAmount":1502000,"prepaymentAmount":0,'
    '"contractAmount":10000000,"contractInstallmentCount":1,'
    '"contractInterestPercentage":0.0,"providerId":"eec4d9b0-e5cb-4712-a896-a458f432c8d1",'
    '"providerName":"کمپانی","fundProviderId":"8dd5fff6-e9a0-48bd-8102-0549849425a3",'
    '"contractKey":"PLATFORM_10000000_1_0.0","creditId":"13047233081673104542352",'
    '"basketId":"235692546","fpType":"leasing","pspName":"MELLAT","pspId":"003"}'
)

_INNER_JSON_REFUND = (
    '{"finalStatus":"CONFIRMED","userId":"fea3d3c0-8e69-436b-b341-be206bed0718",'
    '"customerName":"علیرضا","cellNumber":"09186023036","nationalCode":"4072885363",'
    '"customerWalletId":null,"productDesc":"14511071351674149978852",'
    '"productLine":"CREDIT","product":12,"productName":"REFUND","rrn":"17530398741674716473620",'
    '"amount":194200,"feeCharge":0,"effectiveDate":"1/26/23, 10:59 AM",'
    '"registerDate":"1/26/23, 10:31 AM","target":null,"providerCode":"1",'
    '"providerName":null,"targetTypeName":"CREDIT","providerTypeName":"CREDIT",'
    '"businessId":"eec4d9b0-e5cb-4712-a896-a458f432c8d1","businessName":"کمپانی",'
    '"parentProviderId":null,"parentProviderName":null,"contractAmount":300000000,'
    '"contractInstallmentCount":18,"contractInterestPercentage":18.0,"fundProvider":"MELLAT",'
    '"fpType":"leasing","exactType":2,"exactTypeName":"CREDIT","cashAmount":0,"creditAmount":0}'
)

# Plain Gherkin Example wording -> (event code, fixed JSON payload). Mirrors
# the three Robot files collapsed into one Scenario Outline — see module docstring.
_TRANSACTION_TYPES: dict[str, tuple[int, str]] = {
    "credit purchase": (3001, _INNER_JSON_CREDIT_PURCHASE),
    "credit prepayment": (3002, _INNER_JSON_CREDIT_PREPAYMENT),
    "refund": (3003, _INNER_JSON_REFUND),
}


def known_transaction_types() -> tuple[str, ...]:
    """Gherkin transaction-type tails registered for incoming ledger creates."""
    return tuple(_TRANSACTION_TYPES)


@dataclass
class CreatedTransaction:
    """State carried across the When/Then chain for one scenario."""

    transaction_type: str
    result: CreateFinancialTransactionResult
    transaction_id: int | None = None
    voucher_id: int | None = None


def create_transaction(
    client: ApiClient,
    cookie: str,
    transaction_type: str,
) -> CreatedTransaction:
    """Create one manual financial transaction of ``transaction_type``."""
    event_code, inner_json = _require_transaction_type(transaction_type)
    result = ensure_ok(
        create_financial_transaction(
            client,
            event_code=event_code,
            inner_json=inner_json,
            request_id=uuid.uuid4().hex,
            parent_event_code=_DEFAULT_PARENT_EVENT_CODE,
            amount=_DEFAULT_AMOUNT,
            client_id=_DEFAULT_CLIENT_ID,
            user_id=DEFAULT_GL_ADMIN_USER_ID,
            cookie=cookie,
        ),
        context=f"GL create {transaction_type} transaction",
    )
    return CreatedTransaction(transaction_type=transaction_type, result=_as_result(result["body"]))


def assert_transaction_present_in_transaction_table(
    mysql_client: MySQLClient, created: CreatedTransaction
) -> None:
    """DB check #1 — also stashes the transaction's DB id for check #2."""
    row = _fetch_matching_row(
        mysql_client,
        table_label="Transaction",
        query="SELECT id FROM transaction_req WHERE request_id = %s",
        params=(_require_request_id(created),),
    )
    created.transaction_id = int(row["id"])


def assert_transaction_present_in_voucher_table(
    mysql_client: MySQLClient, created: CreatedTransaction
) -> None:
    """DB check #2 — requires check #1 to have run first; stashes the voucher id."""
    row = _fetch_matching_row(
        mysql_client,
        table_label="Voucher",
        query="SELECT id FROM voucher WHERE f_transaction_req = %s",
        params=(_require_transaction_id(created),),
    )
    created.voucher_id = int(row["id"])


def assert_transaction_present_in_article_table(
    mysql_client: MySQLClient, created: CreatedTransaction
) -> None:
    """DB check #3 — requires check #2 to have run first."""
    _fetch_matching_row(
        mysql_client,
        table_label="Article",
        query="SELECT id FROM article WHERE f_voucher = %s",
        params=(_require_voucher_id(created),),
    )


_LEDGER_TABLE_CHECKS: dict[str, Callable[[MySQLClient, CreatedTransaction], None]] = {
    "Transaction": assert_transaction_present_in_transaction_table,
    "Voucher": assert_transaction_present_in_voucher_table,
    "Article": assert_transaction_present_in_article_table,
}


def known_ledger_tables() -> tuple[str, ...]:
    """Gherkin ledger-table tails for the shared Then family."""
    return tuple(_LEDGER_TABLE_CHECKS)


def assert_transaction_present_in_ledger_table(
    mysql_client: MySQLClient, created: CreatedTransaction, table: str
) -> None:
    """Dispatch one Gherkin Then onto the matching ledger-table check.

    Raises:
        KeyError: If ``table`` is not Transaction, Voucher, or Article.
    """
    check = _LEDGER_TABLE_CHECKS.get(table)
    if check is None:
        raise KeyError(f"No GL ledger table check for {table!r}; known: {known_ledger_tables()}")
    check(mysql_client, created)


def assert_transaction_amount_is_correct(created: CreatedTransaction) -> None:
    """The created voucher's ``transactionRequest.amount`` must equal what was requested."""
    actual = None
    if created.result.voucher and created.result.voucher.transaction_request:
        actual = created.result.voucher.transaction_request.amount
    AssertionReport(f"{created.transaction_type} transaction amount is correct").equals(
        "voucher.transactionRequest.amount", actual=actual, expected=_DEFAULT_AMOUNT
    ).assert_all()


def _fetch_matching_row(
    mysql_client: MySQLClient,
    *,
    table_label: str,
    query: str,
    params: tuple[object, ...],
) -> dict[str, Any]:
    """Poll until a row appears, then return it (or fail via ``AssertionReport``)."""
    deadline = time.monotonic() + _DB_POLL_TIMEOUT_S
    last_status: object = None
    last_rows: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        result = mysql_client.fetch_all(_GL_DB, query, params)
        last_status = result["status_code"]
        last_rows = _as_row_dicts(result.get("body"))
        if last_status == 0 and last_rows:
            return last_rows[0]
        time.sleep(_DB_POLL_INTERVAL_S)
    report = AssertionReport(f"{table_label} table has a matching row")
    report.equals("DB status_code", actual=last_status, expected=0)
    report.truthy(f"{table_label} row present", last_rows)
    report.assert_all()
    return last_rows[0]


def _as_row_dicts(body: object) -> list[dict[str, Any]]:
    if not isinstance(body, list):
        return []
    return [row for row in body if isinstance(row, dict)]


def _require_transaction_type(transaction_type: str) -> tuple[int, str]:
    try:
        return _TRANSACTION_TYPES[transaction_type]
    except KeyError as exc:
        raise KeyError(
            f"No GL transaction type for {transaction_type!r}; known: {known_transaction_types()}"
        ) from exc


def _as_result(body: object) -> CreateFinancialTransactionResult:
    """Narrow the ``{status_code, body}`` envelope's body to a parsed result."""
    if isinstance(body, CreateFinancialTransactionResult):
        return body
    raise RuntimeError(f"Unexpected GL create-transaction response shape: {body!r}")


def _require_request_id(created: CreatedTransaction) -> str:
    if not created.result.response or not created.result.response.request_id:
        raise RuntimeError(f"No requestId in create-transaction response: {created.result!r}")
    return created.result.response.request_id


def _require_transaction_id(created: CreatedTransaction) -> int:
    if created.transaction_id is None:
        raise RuntimeError("Transaction table check has not run yet for this scenario")
    return created.transaction_id


def _require_voucher_id(created: CreatedTransaction) -> int:
    if created.voucher_id is None:
        raise RuntimeError("Voucher table check has not run yet for this scenario")
    return created.voucher_id
