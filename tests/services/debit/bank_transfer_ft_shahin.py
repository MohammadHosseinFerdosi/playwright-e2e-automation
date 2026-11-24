"""ft_shahin CASH_OUT orchestration (internal, PAYA, SATNA, statement)."""

from __future__ import annotations

from typing import Any

from tests.api.debit.bank_transfer.provider_statements import (
    ProviderStatementsRequest,
    post_provider_statements,
)
from tests.config.constants import PLATFORM_VERSION_2023
from tests.services.debit import bank_transfer_statements as stmts
from tests.services.debit.bank_transfer import (
    QA_FT_SHAHIN_PREFIX,
    TYPE_ACH,
    TYPE_INTERNAL,
    TYPE_RTGS,
    BankTransferContext,
    BankTransferFlow,
    title_of,
)

INVALID_IBAN = "IR00INVALID"
HOSTILE_OWNERS = ("<script>alert(1)</script>", "{{7*7}}", "A" * 500)
CLIENT_CODE = "ft_shahin"
BANK_CODE = "019"
ACH_BATCH_CHUNKS = 2
ACH_TRIPLE_CHUNKS = 3
STATEMENT_PAGE = 0
STATEMENT_SIZE = 10
STATEMENT_WINDOWS_MS = (6, 12, 24, 168)


def store_internal(flow: BankTransferFlow, ctx: BankTransferContext, case: str) -> None:
    """Dispatch ft shahin INTERNAL When."""
    {
        "route": _internal_route,
        "bad iban": _internal_bad_iban,
        "hostile owners": _internal_xss,
        "marker": _internal_marker,
        "duplicate": _internal_duplicate,
        "zero amount": _internal_zero,
    }[case](flow, ctx)


def store_ach(flow: BankTransferFlow, ctx: BankTransferContext, case: str) -> None:
    """Dispatch ft shahin PAYA When."""
    {
        "route": _ach_route,
        "zero then pin": _ach_zero_then_pin,
        "zero amount": _ach_zero,
        "bad iban": _ach_bad_iban,
        "duplicate": _ach_duplicate,
        "same bank": _ach_same_bank,
        "batch": _ach_batch,
        "batch inquiry": _ach_batch_inquiry,
        "remainder": _ach_remainder,
        "triple": _ach_triple,
        "negative amount": _ach_negative,
        "missing iban": _ach_missing_iban,
        "missing tracking": _ach_missing_tracking,
    }[case](flow, ctx)


def store_rtgs(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Route one ft shahin SATNA cash-out."""
    flow.routing.pin_ft_shahin_rtgs(100)
    tc = flow.new_tracking_code("satna", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.route_result = flow.route(
        tc,
        amount=_rtgs_amount(flow),
        iban=_rtgs_iban(flow),
        preferred_type=str(TYPE_RTGS),
        description=f"QA|FT-SHAHIN|SATNA|{tc}",
    )
    ctx.last_result = ctx.route_result
    ctx.mongo_doc = flow.find_transfer(tc)


def store_statement(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """POST ft shahin provider statements."""
    flow.routing.activate_ft_shahin_statement()
    now = stmts.now_ms()
    chosen: dict[str, Any] | None = None
    for hours in STATEMENT_WINDOWS_MS:
        result = _post_statements(flow, now - hours * stmts.HOUR_MS, now)
        chosen = result
        items = stmts.extract_items(result.get("body"))
        if int(result.get("status_code") or 0) == 200 and items:
            ctx.last_result = result
            return
    ctx.last_result = chosen or {}


def store_inquiry(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    """Inquiry for the scenario tracking code."""
    tc = ctx.tracking_code or ""
    ctx.inquiry_result = flow.inquiry(tc)
    ctx.last_result = ctx.inquiry_result
    ctx.mongo_doc = flow.find_transfer(tc)


def _internal_iban(flow: BankTransferFlow) -> str:
    return flow.secrets.ft_shahin_internal_iban


def _paya_iban(flow: BankTransferFlow) -> str:
    return flow.secrets.ft_shahin_paya_target_iban


def _rtgs_iban(flow: BankTransferFlow) -> str:
    return flow.secrets.ft_shahin_rtgs_target_iban


def _rtgs_amount(flow: BankTransferFlow) -> int:
    return max(
        flow.secrets.ft_shahin_rtgs_probe_amount,
        flow.secrets.ft_shahin_rtgs_min_amount,
    )


def _paya_amount(flow: BankTransferFlow) -> int:
    return flow.secrets.safe_amount


def _split_total(flow: BankTransferFlow, ctx: BankTransferContext, chunks: int) -> int:
    amount = flow.secrets.ach_chunk * chunks
    ctx.flags["batch_total"] = amount
    return amount


def _batch_over_chunk(flow: BankTransferFlow, ctx: BankTransferContext, tag: str) -> None:
    amount = flow.secrets.ach_chunk + 1
    ctx.flags["batch_total"] = amount
    _ach_route_amount(flow, ctx, amount, tag)


def _ach_route_amount(
    flow: BankTransferFlow, ctx: BankTransferContext, amount: int, tag: str
) -> None:
    flow.routing.pin_ft_shahin_ach(100)
    tc = flow.new_tracking_code(tag, prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.route_result = flow.route(
        tc,
        amount=amount,
        iban=_paya_iban(flow),
        preferred_type=str(TYPE_ACH),
        description=f"QA|FT-SHAHIN|{tag.upper()}|{tc}",
    )
    ctx.last_result = ctx.route_result
    ctx.mongo_doc = flow.find_transfer(tc)


def _internal_route(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_internal(100)
    tc = flow.new_tracking_code("internal", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.route_result = flow.route(
        tc,
        amount=flow.secrets.safe_amount,
        iban=_internal_iban(flow),
        preferred_type=flow.secrets.preferred_type,
        description=f"QA|FT-SHAHIN|INTERNAL|{tc}",
    )
    ctx.last_result = ctx.route_result
    ctx.mongo_doc = flow.find_transfer(tc)


def _internal_bad_iban(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_internal(100)
    tc = flow.new_tracking_code("bad-iban", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.last_result = flow.route(tc, iban=INVALID_IBAN, preferred_type=str(TYPE_INTERNAL))
    ctx.flags["doc_missing"] = flow.find_transfer(tc) is None


def _internal_xss(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_internal(100)
    codes: list[int] = []
    titles: list[str | None] = []
    for owner in HOSTILE_OWNERS:
        tc = flow.new_tracking_code("hostile", prefix=QA_FT_SHAHIN_PREFIX)
        result = flow.route(
            tc,
            iban=_internal_iban(flow),
            owner_name=owner,
            preferred_type=str(TYPE_INTERNAL),
        )
        codes.append(int(result.get("status_code") or 0))
        titles.append(title_of(result))
    ctx.probe_codes = codes
    ctx.probe_titles = titles
    ctx.flags["max_status"] = max(codes) if codes else 0


def _internal_marker(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_internal(100)
    tc = flow.new_tracking_code("marker", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.route_result = flow.route(
        tc,
        amount=flow.secrets.marker_amount,
        iban=_internal_iban(flow),
        preferred_type=str(TYPE_INTERNAL),
    )
    ctx.last_result = ctx.route_result
    ctx.mongo_doc = flow.find_transfer(tc)


def _internal_duplicate(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_internal(100)
    tc = flow.new_tracking_code("duplicate", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    payload = {
        "amount": flow.secrets.safe_amount,
        "iban": _internal_iban(flow),
        "preferred_type": flow.secrets.preferred_type,
        "description": f"QA|FT-SHAHIN|DUPLICATE|{tc}",
    }
    ctx.route_result = flow.route(tc, **payload)
    ctx.second_result = flow.route(tc, **payload)
    ctx.last_result = ctx.second_result
    ctx.mongo_count = flow.count_transfers(tc)


def _internal_zero(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_internal(100)
    tc = flow.new_tracking_code("zero-amount", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.last_result = flow.route(
        tc, amount=0, iban=_internal_iban(flow), preferred_type=str(TYPE_INTERNAL)
    )
    ctx.flags["doc_missing"] = flow.find_transfer(tc) is None


def _ach_route(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    _ach_route_amount(flow, ctx, _paya_amount(flow), "paya")


def _ach_zero_then_pin(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.clear_all_gateway_weights()
    tc_off = flow.new_tracking_code("zero-weight", prefix=QA_FT_SHAHIN_PREFIX)
    off = flow.route(
        tc_off,
        amount=_paya_amount(flow),
        iban=_paya_iban(flow),
        preferred_type=str(TYPE_ACH),
    )
    ctx.flags["off_status"] = off.get("status_code")
    ctx.flags["off_title"] = title_of(off)
    ctx.flags["off_doc_missing"] = flow.find_transfer(tc_off) is None
    flow.routing.pin_ft_shahin_ach(100)
    tc = flow.new_tracking_code("pinned", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.route_result = flow.route(
        tc,
        amount=_paya_amount(flow),
        iban=_paya_iban(flow),
        preferred_type=str(TYPE_ACH),
        description=f"QA|FT-SHAHIN|PINNED|{tc}",
    )
    ctx.last_result = ctx.route_result
    ctx.mongo_doc = flow.find_transfer(tc)


def _ach_zero(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_ach(100)
    tc = flow.new_tracking_code("zero-amount", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.last_result = flow.route(tc, amount=0, iban=_paya_iban(flow), preferred_type=str(TYPE_ACH))
    ctx.flags["doc_missing"] = flow.find_transfer(tc) is None


def _ach_bad_iban(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_ach(100)
    tc = flow.new_tracking_code("bad-iban", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.last_result = flow.route(tc, iban=INVALID_IBAN, preferred_type=str(TYPE_ACH))
    ctx.flags["doc_missing"] = flow.find_transfer(tc) is None


def _ach_duplicate(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_ach(100)
    tc = flow.new_tracking_code("paya-duplicate", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    payload = {
        "amount": _paya_amount(flow),
        "iban": _paya_iban(flow),
        "preferred_type": str(TYPE_ACH),
        "description": f"QA|FT-SHAHIN|PAYA-DUPLICATE|{tc}",
    }
    ctx.route_result = flow.route(tc, **payload)
    ctx.second_result = flow.route(tc, **payload)
    ctx.last_result = ctx.second_result
    ctx.mongo_count = flow.count_transfers(tc)


def _ach_same_bank(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_ach(100)
    tc = flow.new_tracking_code("paya-same-bank", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.last_result = flow.route(
        tc,
        amount=flow.secrets.ach_probe_amount,
        iban=_internal_iban(flow),
        preferred_type=str(TYPE_ACH),
        description=f"QA|FT-SHAHIN|PAYA-SAME-BANK|{tc}",
    )
    ctx.route_result = ctx.last_result
    ctx.mongo_doc = flow.find_transfer(tc)


def _ach_batch(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    _ach_route_amount(flow, ctx, _split_total(flow, ctx, ACH_BATCH_CHUNKS), "paya-batch")


def _ach_batch_inquiry(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    _ach_batch(flow, ctx)
    store_inquiry(flow, ctx)


def _ach_remainder(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    _batch_over_chunk(flow, ctx, "paya-remainder")


def _ach_triple(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    _ach_route_amount(flow, ctx, _split_total(flow, ctx, ACH_TRIPLE_CHUNKS), "paya-triple")


def _ach_negative(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_ach(100)
    tc = flow.new_tracking_code("paya-negative", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.last_result = flow.route(tc, amount=-1, iban=_paya_iban(flow), preferred_type=str(TYPE_ACH))
    ctx.flags["doc_missing"] = flow.find_transfer(tc) is None


def _ach_missing_iban(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_ach(100)
    tc = flow.new_tracking_code("paya-no-iban", prefix=QA_FT_SHAHIN_PREFIX)
    ctx.tracking_code = tc
    ctx.last_result = flow.route_raw(
        tracking_code=tc,
        amount=flow.secrets.ach_probe_amount,
        iban="",
        owner_name=flow.secrets.mellat_owner_name,
        description=f"QA|FT-SHAHIN|PAYA-NO-IBAN|{tc}",
        preferred_type=str(TYPE_ACH),
    )
    ctx.flags["doc_missing"] = flow.find_transfer(tc) is None


def _ach_missing_tracking(flow: BankTransferFlow, ctx: BankTransferContext) -> None:
    flow.routing.pin_ft_shahin_ach(100)
    probe = flow.new_tracking_code("paya-no-tracking", prefix=QA_FT_SHAHIN_PREFIX)
    desc = f"QA|FT-SHAHIN|PAYA-NO-TRACKING|{probe}"
    ctx.last_result = flow.route_raw(
        tracking_code=None,
        amount=flow.secrets.ach_probe_amount,
        iban=_paya_iban(flow),
        owner_name=flow.secrets.mellat_owner_name,
        description=desc,
        preferred_type=str(TYPE_ACH),
    )
    by_probe = flow.find_transfer(probe)
    by_desc = flow.routing.db.ach_transfers.find_one({"description": desc}, {"_id": 0})
    ctx.flags["doc_missing"] = by_probe is None and by_desc is None


def _post_statements(flow: BankTransferFlow, from_ms: int, to_ms: int) -> dict[str, Any]:
    secrets = flow.secrets
    return post_provider_statements(
        flow.client,
        ProviderStatementsRequest.model_validate(
            {
                "bankCode": BANK_CODE,
                "accountNumber": secrets.ft_shahin_account_number,
                "fromDate": from_ms,
                "toDate": to_ms,
                "page": STATEMENT_PAGE,
                "size": STATEMENT_SIZE,
            }
        ),
        user_id=secrets.user_id,
        forwarded_for=secrets.forwarded_for,
        platform_version=PLATFORM_VERSION_2023,
    )
