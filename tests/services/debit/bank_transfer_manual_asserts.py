"""Assertions for Manual portal bank-transfer BDD."""

from __future__ import annotations

from tests.api.debit.bank_transfer.models import TransferRouteBody
from tests.services.assert_report import AssertionReport, attach_api_result
from tests.services.debit.bank_transfer import (
    ACH_TYPE_TOKENS,
    INTERNAL_TYPE_TOKENS,
    BankTransferContext,
    route_body_fields,
    title_of,
)
from tests.services.debit.bank_transfer_manual import (
    DSH_DONE_SCHEMA,
    DSH_SETTLE_DONE,
    INQ_PENDING,
    INQ_SUCCEED,
    MANUAL_BANK,
    MANUAL_CLIENT,
    PROVIDER_JOURNAL_ACTIONS,
)
from tests.services.debit.bank_transfer_routing import skip_if_switch_setup

PLATFORM_REJECT = frozenset(
    {
        "INVALID_PARAMETER",
        "FAILURE",
        "BAD_REQUEST",
        "BANKPROXY_NO_GATEWAY",
        "BANKPROXY_DUPLICATE_TRANSACTION",
    }
)
IDEMPOTENT = frozenset(
    {"BANKPROXY_DUPLICATE_TRANSACTION", "INVALID_PARAMETER", "FAILURE"}
)


def assert_manual_case(ctx: BankTransferContext, case: str) -> None:
    """Dispatch Then for a Manual case key."""
    dispatch = {
        "ach route pinned": assert_ach_route,
        "never internal type": assert_never_internal,
        "mongo row fields": assert_mongo_fields,
        "route transfer in progress": assert_in_progress,
        "inquiry preserves in progress": assert_status_preserved,
        "scheduler preserves in progress": assert_status_preserved,
        "routing consistency": assert_routing_ok,
        "mellat split fifty fifty": assert_ach_route,
        "cross bank blocked mellat only": assert_cross_bank_blocked,
        "rtgs inactive": assert_rtgs_inactive,
        "ach fee zero": assert_fee_zero,
        "accepts every bank iban": assert_every_bank,
        "route journal": assert_route_journal,
        "transfer journal": assert_transfer_journal,
        "inquiry matches mongo": assert_inquiry_matches,
        "tx accepted after transfer": assert_tx_accepted,
        "reconcile without statement": assert_reconcile,
        "duplicate route single row": assert_dup_route,
        "duplicate transfer rejected": assert_dup_transfer,
        "concurrent transfer race": assert_concurrent_race,
        "production crisis checklist": assert_crisis,
        DSH_SETTLE_DONE: assert_dsh_settle_done,
        DSH_DONE_SCHEMA: assert_done_schema,
        "nemo settlement reference": assert_nemo_ref,
    }
    dispatch[case](ctx)


def assert_ach_route(ctx: BankTransferContext) -> None:
    """Manual ACH route contract."""
    attach_api_result("manual route", ctx.route_result or ctx.last_result)
    result = ctx.route_result or ctx.last_result
    report = AssertionReport("manual ACH route")
    report.equals("HTTP", actual=result.get("status_code"), expected=200)
    body = route_body_fields(result)
    report.check("typed", isinstance(body, TransferRouteBody))
    if isinstance(body, TransferRouteBody):
        report.equals("clientCode", actual=body.client_code, expected=MANUAL_CLIENT)
        report.equals("bankCode", actual=body.bank_code, expected=MANUAL_BANK)
        report.check("type ACH", body.type in ACH_TYPE_TOKENS)
        report.equals("fee", actual=body.fee, expected=0)
    doc = ctx.mongo_doc or {}
    if doc:
        report.check("mongo type ACH", doc.get("type") in ACH_TYPE_TOKENS | {"ACH", 0, "0"})
    report.assert_all()


def assert_never_internal(ctx: BankTransferContext) -> None:
    """Type must not be INTERNAL."""
    assert_ach_route(ctx)
    report = AssertionReport("manual never INTERNAL")
    body = route_body_fields(ctx.route_result or ctx.last_result)
    if isinstance(body, TransferRouteBody):
        report.check("not INTERNAL", body.type not in INTERNAL_TYPE_TOKENS)
    doc = ctx.mongo_doc or {}
    report.check(
        "mongo not INTERNAL",
        doc.get("type") not in INTERNAL_TYPE_TOKENS | {"INTERNAL", 2, "2"},
    )
    report.assert_all()


def assert_mongo_fields(ctx: BankTransferContext) -> None:
    """INITIATED CASH_OUT row with tx traceId and matching IBAN."""
    attach_api_result("manual route", ctx.route_result)
    report = AssertionReport("manual mongo fields")
    report.equals("HTTP", actual=ctx.route_result.get("status_code"), expected=200)
    doc = ctx.mongo_doc or {}
    report.truthy("doc", bool(doc))
    report.equals("status", actual=doc.get("status"), expected="INITIATED")
    report.equals("agenda", actual=doc.get("agenda"), expected="CASH_OUT")
    report.equals("clientCode", actual=doc.get("clientCode"), expected=MANUAL_CLIENT)
    txs = doc.get("transactions") or []
    report.truthy("tx", bool(txs))
    if txs:
        report.truthy("traceId", txs[0].get("traceId"))
        stored = txs[0].get("iban") or txs[0].get("targetIban")
        report.equals(
            "iban",
            actual=stored,
            expected=ctx.secrets.melli_target_iban or ctx.secrets.mellat_cross_bank_iban,
        )
    report.assert_all()


def assert_in_progress(ctx: BankTransferContext) -> None:
    """After execute, mongo IN_PROGRESS."""
    attach_api_result("manual execute", ctx.last_result)
    report = AssertionReport("manual stays IN_PROGRESS")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=200)
    doc = ctx.mongo_doc or {}
    report.equals("status", actual=doc.get("status"), expected="IN_PROGRESS")
    report.assert_all()


def assert_status_preserved(ctx: BankTransferContext) -> None:
    """Status unchanged by inquiry/scheduler."""
    report = AssertionReport("manual status preserved")
    report.equals(
        "before",
        actual=ctx.flags.get("status_before"),
        expected="IN_PROGRESS",
    )
    report.equals(
        "after",
        actual=ctx.flags.get("status_after"),
        expected="IN_PROGRESS",
    )
    report.assert_all()


def assert_routing_ok(ctx: BankTransferContext) -> None:
    """Routing consistency flag set."""
    report = AssertionReport("manual routing consistent")
    report.check("ok", ctx.flags.get("routing_ok") is True)
    report.assert_all()


def assert_cross_bank_blocked(ctx: BankTransferContext) -> None:
    """Cross-bank rejected when only mellat INTERNAL is on."""
    attach_api_result("blocked route", ctx.last_result)
    title = title_of(ctx.last_result)
    skip_if_switch_setup(title, reason="manual cross-bank Switch setup")
    report = AssertionReport("cross-bank blocked mellat-only")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=422)
    report.check("title", title in PLATFORM_REJECT)
    report.assert_all()


def assert_rtgs_inactive(ctx: BankTransferContext) -> None:
    """Manual RTGS client inactive weight 0."""
    report = AssertionReport("manual RTGS inactive")
    row = ctx.client_row or {}
    report.truthy("row", bool(row))
    report.equals("active", actual=row.get("active"), expected=False)
    weight = row.get("selectionWeight")
    report.equals("weight", actual=0 if weight is None else int(weight), expected=0)
    report.assert_all()


def assert_fee_zero(ctx: BankTransferContext) -> None:
    """Fee zero on manual ACH."""
    assert_ach_route(ctx)


def assert_every_bank(ctx: BankTransferContext) -> None:
    """All four bank IBANs routed to bn_manual."""
    report = AssertionReport("manual accepts every bank IBAN")
    codes = ctx.flags.get("client_codes") or []
    report.equals("count", actual=len(codes), expected=4)
    report.check("all bn_manual", all(c == MANUAL_CLIENT for c in codes))
    report.check("all HTTP 200", all(c == 200 for c in ctx.probe_codes))
    report.assert_all()


def assert_route_journal(ctx: BankTransferContext) -> None:
    """ROUTE journal; no TRANSFER/provider."""
    report = AssertionReport("manual ROUTE journal")
    actions = ctx.flags.get("actions") or []
    report.check("ROUTE", "ROUTE" in actions)
    report.check("no TRANSFER", "TRANSFER" not in actions)
    report.check(
        "no provider",
        not PROVIDER_JOURNAL_ACTIONS.intersection(actions),
    )
    report.assert_all()


def assert_transfer_journal(ctx: BankTransferContext) -> None:
    """ROUTE + TRANSFER journals."""
    report = AssertionReport("manual TRANSFER journal")
    actions = ctx.flags.get("actions") or []
    report.check("ROUTE", "ROUTE" in actions)
    report.check("TRANSFER", "TRANSFER" in actions)
    report.check(
        "no provider",
        not PROVIDER_JOURNAL_ACTIONS.intersection(actions),
    )
    report.assert_all()


def assert_inquiry_matches(ctx: BankTransferContext) -> None:
    """Inquiry PENDING for mongo IN_PROGRESS."""
    attach_api_result("inquiry", ctx.inquiry_result)
    report = AssertionReport("manual inquiry matches mongo")
    report.equals("mongo", actual=ctx.flags.get("mongo_status"), expected="IN_PROGRESS")
    report.equals("inquiry", actual=ctx.flags.get("inquiry_status"), expected=INQ_PENDING)
    report.assert_all()


def assert_tx_accepted(ctx: BankTransferContext) -> None:
    """Tx ACCEPTED after transfer."""
    report = AssertionReport("manual tx ACCEPTED")
    report.equals("tx", actual=ctx.flags.get("tx_status"), expected="ACCEPTED")
    report.equals(
        "mongo",
        actual=(ctx.mongo_doc or {}).get("status"),
        expected="IN_PROGRESS",
    )
    report.assert_all()


def assert_reconcile(ctx: BankTransferContext) -> None:
    """Amount + IBAN reconcile without statement."""
    report = AssertionReport("manual reconcile")
    report.equals("mongo", actual=ctx.flags.get("mongo_status"), expected="IN_PROGRESS")
    report.check("amount", ctx.flags.get("amount_ok") is True)
    report.check("iban", ctx.flags.get("iban_ok") is True)
    report.assert_all()


def assert_dup_route(ctx: BankTransferContext) -> None:
    """Duplicate route keeps one row."""
    attach_api_result("first", ctx.route_result)
    attach_api_result("second", ctx.second_result)
    report = AssertionReport("manual duplicate route")
    report.equals("first", actual=ctx.route_result.get("status_code"), expected=200)
    code2 = int(ctx.second_result.get("status_code") or 0)
    report.check("second ok-or-reject", code2 in (200, 422))
    report.equals("mongo count", actual=ctx.mongo_count, expected=1)
    report.assert_all()


def assert_dup_transfer(ctx: BankTransferContext) -> None:
    """Second execute 422."""
    attach_api_result("second", ctx.second_result)
    report = AssertionReport("manual duplicate transfer")
    report.equals("second HTTP", actual=ctx.second_result.get("status_code"), expected=422)
    report.check("title", title_of(ctx.second_result) in IDEMPOTENT | PLATFORM_REJECT)
    report.equals(
        "still IP",
        actual=(ctx.mongo_doc or {}).get("status"),
        expected="IN_PROGRESS",
    )
    report.assert_all()


def assert_concurrent_race(ctx: BankTransferContext) -> None:
    """Exactly one concurrent execute succeeds."""
    report = AssertionReport("manual concurrent race")
    codes = ctx.probe_codes
    report.equals("one 200", actual=codes.count(200), expected=1)
    report.check(
        "journals",
        int(ctx.flags.get("transfer_journal_count") or 0) <= 1,
    )
    report.equals("mongo", actual=ctx.flags.get("mongo_status"), expected="IN_PROGRESS")
    report.assert_all()


def assert_crisis(ctx: BankTransferContext) -> None:
    """Crisis checklist evidence."""
    report = AssertionReport("manual crisis checklist")
    report.check("rtgs off", ctx.flags.get("rtgs_inactive") is True)
    report.equals("client", actual=ctx.flags.get("client_code"), expected=MANUAL_CLIENT)
    report.equals("fee", actual=ctx.flags.get("fee"), expected=0)
    report.check("type ACH", ctx.flags.get("type") in ACH_TYPE_TOKENS)
    report.equals("mongo", actual=ctx.flags.get("mongo_status"), expected="IN_PROGRESS")
    report.equals("tx", actual=ctx.flags.get("tx_status"), expected="ACCEPTED")
    report.assert_all()


def assert_dsh_settle_done(ctx: BankTransferContext) -> None:
    """DONE + ACCEPTED → inquiry SUCCEED."""
    attach_api_result("inquiry after settle", ctx.inquiry_result)
    report = AssertionReport("manual settle DONE")
    report.equals("mongo", actual=ctx.flags.get("mongo_status"), expected="DONE")
    report.equals("inquiry", actual=ctx.flags.get("inquiry_status"), expected=INQ_SUCCEED)
    report.assert_all()


def assert_done_schema(ctx: BankTransferContext) -> None:
    """DONE row schema for bn_manual."""
    report = AssertionReport("manual DONE row schema")
    doc = ctx.mongo_doc or {}
    report.equals("client", actual=doc.get("clientCode"), expected=MANUAL_CLIENT)
    report.equals("bank", actual=doc.get("bankCode"), expected=MANUAL_BANK)
    report.equals("status", actual=doc.get("status"), expected="DONE")
    report.check("type ACH", doc.get("type") in ACH_TYPE_TOKENS | {"ACH", 0, "0"})
    txs = doc.get("transactions") or []
    report.truthy("tx", bool(txs))
    if txs:
        report.equals("tx ACCEPTED", actual=txs[0].get("status"), expected="ACCEPTED")
    actions = ctx.flags.get("actions") or []
    report.check("ROUTE", "ROUTE" in actions)
    report.check("TRANSFER", "TRANSFER" in actions)
    report.assert_all()


def assert_nemo_ref(ctx: BankTransferContext) -> None:
    """Nemo reference — When always skips today."""
    report = AssertionReport("manual nemo reference")
    report.equals("client", actual=ctx.flags.get("client_code"), expected=MANUAL_CLIENT)
    report.equals("mongo", actual=ctx.flags.get("mongo_status"), expected="DONE")
    report.assert_all()
