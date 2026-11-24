"""Assertions for ft shahin CASH_OUT rails."""

from __future__ import annotations

from tests.api.debit.bank_transfer.models import StatementPageBody, TransferRouteBody
from tests.services.assert_report import AssertionReport, attach_api_result
from tests.services.debit import bank_transfer_statements as stmts
from tests.services.debit.bank_transfer import (
    ACH_TYPE_TOKENS,
    INTERNAL_TYPE_TOKENS,
    NO_GATEWAY_TITLES,
    RTGS_TYPE_TOKENS,
    BankTransferContext,
    route_body_fields,
    title_of,
)
from tests.services.debit.bank_transfer_ach_asserts import (
    assert_ach_batch_inquiry_lists_splits,
    assert_ach_batch_route,
)
from tests.services.debit.bank_transfer_ft_shahin import BANK_CODE, CLIENT_CODE
from tests.services.debit.bank_transfer_routing import SWITCH_SETUP_TITLES

INQ_ROUTED = 0
HTTP_SERVER_ERROR_MIN = 500
PLATFORM_REJECT = frozenset(
    {
        "INVALID_PARAMETER",
        "FAILURE",
        "BAD_REQUEST",
        "TRANSACTION_NOT_FOUND",
        "BANKPROXY_DUPLICATE_TRANSACTION",
        "BANKPROXY_NO_GATEWAY",
    }
)
MONGO_INTERNAL = INTERNAL_TYPE_TOKENS | {"INTERNAL", 2, "2"}
MONGO_ACH = ACH_TYPE_TOKENS | {"ACH", 0, "0"}
MONGO_RTGS = RTGS_TYPE_TOKENS | {"RTGS", "RTGS_TRANSFER", 1, "1"}


def assert_internal_route(ctx: BankTransferContext) -> None:
    """INTERNAL pin route via ft_shahin."""
    result = ctx.route_result or ctx.last_result
    attach_api_result("ft shahin internal route", result)
    title = title_of(result)
    report = AssertionReport("ft shahin INTERNAL route")
    report.equals("HTTP", actual=result.get("status_code"), expected=200)
    if result.get("status_code") != 200:
        report.note(f"route title={title!r}")
    body = route_body_fields(result)
    report.check("typed", isinstance(body, TransferRouteBody))
    if isinstance(body, TransferRouteBody):
        report.equals("client", actual=body.client_code, expected=CLIENT_CODE)
        report.equals("bank", actual=body.bank_code, expected=BANK_CODE)
        report.check("type INTERNAL", body.type in INTERNAL_TYPE_TOKENS)
        report.equals("fee", actual=body.fee, expected=0)
    doc = ctx.mongo_doc or {}
    report.truthy("transfer row", ctx.mongo_doc)
    report.check("mongo INTERNAL", doc.get("type") in MONGO_INTERNAL)
    report.equals("mongo client", actual=doc.get("clientCode"), expected=CLIENT_CODE)
    txs = doc.get("transactions") or []
    report.truthy("has tx", bool(txs))
    if txs:
        iban = txs[0].get("iban") or txs[0].get("targetIban")
        report.equals("iban", actual=iban, expected=ctx.secrets.ft_shahin_internal_iban)
    report.assert_all()


def assert_never_paya(ctx: BankTransferContext) -> None:
    """Same-bank PAYA is 422 (Platform or Switch wrap), or HTTP 200 with a non-ACH type."""
    result = ctx.route_result or ctx.last_result
    attach_api_result("ft shahin not PAYA", result)
    code = int(result.get("status_code") or 0)
    body = route_body_fields(result)
    report = AssertionReport("ft shahin not PAYA")
    if code == 200:
        report.check("typed", isinstance(body, TransferRouteBody))
        if isinstance(body, TransferRouteBody):
            report.check("not ACH", body.type not in ACH_TYPE_TOKENS)
    else:
        title = title_of(result)
        report.equals("HTTP", actual=code, expected=422)
        report.check(
            "title",
            title in PLATFORM_REJECT or title in SWITCH_SETUP_TITLES,
            detail=f"got {title!r}",
        )
    report.assert_all()


def _inquiry_stays_routed(ctx: BankTransferContext, label: str) -> None:
    attach_api_result("inquiry", ctx.inquiry_result)
    report = AssertionReport(label)
    report.equals("HTTP", actual=ctx.inquiry_result.get("status_code"), expected=200)
    body = route_body_fields(ctx.inquiry_result)
    report.check("typed", isinstance(body, TransferRouteBody))
    if isinstance(body, TransferRouteBody):
        report.equals("inquiry client", actual=body.client_code, expected=CLIENT_CODE)
        report.equals("inquiry bank", actual=body.bank_code, expected=BANK_CODE)
        report.equals("inquiry ROUTED", actual=body.status, expected=INQ_ROUTED)
    report.assert_all()


def assert_internal_inquiry(ctx: BankTransferContext) -> None:
    """Inquiry after INTERNAL route stays ROUTED on ft_shahin."""
    _inquiry_stays_routed(ctx, "ft shahin internal inquiry")


def assert_marker(ctx: BankTransferContext) -> None:
    """Stored amount is the marker amount."""
    doc = ctx.mongo_doc or {}
    txs = doc.get("transactions") or []
    report = AssertionReport("ft shahin marker")
    report.check("has tx", bool(txs))
    if txs:
        report.equals("amount", actual=txs[0].get("amount"), expected=ctx.secrets.marker_amount)
        iban = txs[0].get("iban") or txs[0].get("targetIban")
        report.equals("iban", actual=iban, expected=ctx.secrets.ft_shahin_internal_iban)
    report.assert_all()


def assert_duplicate(ctx: BankTransferContext) -> None:
    """Duplicate route keeps a single row."""
    report = AssertionReport("ft shahin duplicate route")
    report.equals("first", actual=ctx.route_result.get("status_code"), expected=200)
    code2 = int(ctx.second_result.get("status_code") or 0)
    report.check("second ok-or-reject", code2 in (200, 422))
    report.equals("mongo count", actual=ctx.mongo_count, expected=1)
    report.assert_all()


def assert_ach_route(ctx: BankTransferContext) -> None:
    """PAYA / ACH pin route."""
    attach_api_result("ft shahin paya route", ctx.route_result)
    report = AssertionReport("ft shahin ACH route")
    report.equals("HTTP", actual=ctx.route_result.get("status_code"), expected=200)
    body = route_body_fields(ctx.route_result)
    report.check("typed", isinstance(body, TransferRouteBody))
    if isinstance(body, TransferRouteBody):
        report.equals("client", actual=body.client_code, expected=CLIENT_CODE)
        report.equals("bank", actual=body.bank_code, expected=BANK_CODE)
        report.check("type ACH", body.type in ACH_TYPE_TOKENS)
    doc = ctx.mongo_doc or {}
    report.check("mongo ACH", doc.get("type") in MONGO_ACH)
    report.equals("mongo client", actual=doc.get("clientCode"), expected=CLIENT_CODE)
    txs = doc.get("transactions") or []
    report.equals("tx count", actual=len(txs), expected=1)
    if txs:
        report.equals(
            "tx amount",
            actual=int(txs[0].get("amount") or 0),
            expected=ctx.secrets.safe_amount,
        )
        iban = txs[0].get("iban") or txs[0].get("targetIban")
        report.equals("iban", actual=iban, expected=ctx.secrets.ft_shahin_paya_target_iban)
    report.assert_all()


def assert_ach_inquiry(ctx: BankTransferContext) -> None:
    """Inquiry after PAYA route stays ROUTED on ft_shahin."""
    _inquiry_stays_routed(ctx, "ft shahin paya inquiry")


def assert_ach_fee(ctx: BankTransferContext) -> None:
    """PAYA route fee equals the mongo fee."""
    result = ctx.route_result or ctx.last_result
    attach_api_result("ft shahin paya fee", result)
    report = AssertionReport("ft shahin PAYA fee")
    report.equals("HTTP", actual=result.get("status_code"), expected=200)
    body = route_body_fields(result)
    report.check("typed", isinstance(body, TransferRouteBody))
    fee = None
    if isinstance(body, TransferRouteBody):
        report.check("type ACH", body.type in ACH_TYPE_TOKENS)
        fee = body.fee
        report.truthy("route fee", fee is not None)
    report.equals("mongo fee", actual=(ctx.mongo_doc or {}).get("fee"), expected=fee)
    report.assert_all()


def assert_ach_zero_pin(ctx: BankTransferContext) -> None:
    """Zero weights block then pin succeeds."""
    raw = ctx.flags.get("off_title")
    off_title = raw if isinstance(raw, str) else None
    report = AssertionReport("ft shahin paya zero then pin")
    report.equals("off HTTP", actual=ctx.flags.get("off_status"), expected=422)
    report.check(
        "off title",
        off_title in NO_GATEWAY_TITLES or off_title in SWITCH_SETUP_TITLES,
    )
    report.check("off no doc", ctx.flags.get("off_doc_missing") is True)
    report.assert_all()
    assert_ach_route(ctx)


def assert_ach_batch(ctx: BankTransferContext) -> None:
    """PAYA batch split + ft_shahin client."""
    assert_ach_batch_route(ctx)
    report = AssertionReport("ft shahin paya batch client")
    doc = ctx.mongo_doc or {}
    report.equals("mongo client", actual=doc.get("clientCode"), expected=CLIENT_CODE)
    txs = doc.get("transactions") or []
    if txs:
        iban = txs[0].get("iban") or txs[0].get("targetIban")
        report.equals("iban", actual=iban, expected=ctx.secrets.ft_shahin_paya_target_iban)
    report.assert_all()


def assert_ach_remainder(ctx: BankTransferContext) -> None:
    """PAYA remainder is one full chunk plus 1, both on ft_shahin."""
    assert_ach_batch(ctx)
    chunk = ctx.secrets.ach_chunk
    txs = (ctx.mongo_doc or {}).get("transactions") or []
    amounts = sorted(int(tx.get("amount") or 0) for tx in txs if isinstance(tx, dict))
    report = AssertionReport("ft shahin paya remainder pieces")
    report.equals("remainder total", actual=int(ctx.flags["batch_total"]), expected=chunk + 1)
    report.equals("piece amounts", actual=amounts, expected=[1, chunk])
    report.assert_all()


def assert_ach_batch_inquiry(ctx: BankTransferContext) -> None:
    """PAYA batch inquiry lists the split chunks."""
    assert_ach_batch_inquiry_lists_splits(ctx)


def assert_rtgs_route(ctx: BankTransferContext) -> None:
    """SATNA route via ft_shahin, RTGS type, SATNA dest IBAN."""
    attach_api_result("ft shahin satna route", ctx.route_result)
    report = AssertionReport("ft shahin RTGS route")
    report.equals("HTTP", actual=ctx.route_result.get("status_code"), expected=200)
    if ctx.route_result.get("status_code") != 200:
        report.note(f"route title={title_of(ctx.route_result)!r}")
    body = route_body_fields(ctx.route_result)
    report.check("typed", isinstance(body, TransferRouteBody))
    if isinstance(body, TransferRouteBody):
        report.equals("client", actual=body.client_code, expected=CLIENT_CODE)
        report.equals("bank", actual=body.bank_code, expected=BANK_CODE)
        report.check("type RTGS", body.type in RTGS_TYPE_TOKENS)
    doc = ctx.mongo_doc or {}
    report.check("mongo RTGS", doc.get("type") in MONGO_RTGS)
    report.equals("mongo client", actual=doc.get("clientCode"), expected=CLIENT_CODE)
    txs = doc.get("transactions") or []
    if txs:
        iban = txs[0].get("iban") or txs[0].get("targetIban")
        report.equals("tx iban", actual=iban, expected=ctx.secrets.ft_shahin_rtgs_target_iban)
    report.assert_all()


def assert_reject_invalid(ctx: BankTransferContext) -> None:
    """422 INVALID_PARAMETER and no mongo row."""
    attach_api_result("reject", ctx.last_result)
    report = AssertionReport("ft_shahin invalid reject")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=422)
    report.equals("title", actual=title_of(ctx.last_result), expected="INVALID_PARAMETER")
    report.check("no mongo", ctx.flags.get("doc_missing") is True)
    report.assert_all()


def assert_xss(ctx: BankTransferContext) -> None:
    """Hostile owner-name probes stay below HTTP 500."""
    report = AssertionReport("ft_shahin owner XSS")
    report.check(
        "status below 500",
        int(ctx.flags.get("max_status") or 0) < HTTP_SERVER_ERROR_MIN,
    )
    for code, title in zip(ctx.probe_codes, ctx.probe_titles, strict=True):
        if 400 <= code < 500:
            report.check(
                f"title {code}",
                title in PLATFORM_REJECT,
                detail=f"got {title!r}",
            )
    report.assert_all()


def assert_statement_page(ctx: BankTransferContext) -> None:
    """POST /statements for the ft_shahin CASH_OUT account returns SUCCESS rows."""
    attach_api_result("ft_shahin statements", ctx.last_result)
    items = stmts.extract_items(ctx.last_result.get("body"))
    report = AssertionReport("ft_shahin statement page")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=200)
    report.equals("title", actual=title_of(ctx.last_result), expected="SUCCESS")
    report.check("typed page", isinstance(ctx.last_result.get("body"), StatementPageBody))
    report.check("has rows", bool(items), detail=f"rows={len(items)}")
    report.assert_all()


def assert_reconcile(ctx: BankTransferContext) -> None:
    """Route, inquiry, and mongo agree on the ft_shahin ledger row."""
    route = ctx.route_result or ctx.last_result
    doc = ctx.mongo_doc or {}
    txs = doc.get("transactions") or []
    report = AssertionReport("ft shahin reconcile")
    report.equals("route HTTP", actual=route.get("status_code"), expected=200)
    report.truthy("ledger row", ctx.mongo_doc)
    report.equals("mongo client", actual=doc.get("clientCode"), expected=CLIENT_CODE)
    report.equals("inquiry HTTP", actual=ctx.inquiry_result.get("status_code"), expected=200)
    inq = route_body_fields(ctx.inquiry_result)
    report.check("typed inquiry", isinstance(inq, TransferRouteBody))
    if isinstance(inq, TransferRouteBody):
        report.equals("inquiry client", actual=inq.client_code, expected=CLIENT_CODE)
        report.equals("inquiry bank", actual=inq.bank_code, expected=BANK_CODE)
        report.equals("inquiry ROUTED", actual=inq.status, expected=INQ_ROUTED)
        if inq.tracking_code is not None:
            report.equals("inquiry tracking", actual=inq.tracking_code, expected=ctx.tracking_code)
    if txs:
        report.equals(
            "ledger amount",
            actual=int(txs[0].get("amount") or 0),
            expected=ctx.secrets.safe_amount,
        )
    report.assert_all()
