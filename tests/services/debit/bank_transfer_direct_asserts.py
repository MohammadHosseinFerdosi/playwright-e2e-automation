"""Assertions for TREASURY direct-route (Melli, Mellat, ft shahin)."""

from __future__ import annotations

from tests.api.debit.bank_transfer.models import TransferRouteBody
from tests.services.assert_report import AssertionReport, attach_api_result
from tests.services.debit.bank_transfer import (
    ACH_TYPE_TOKENS,
    INTERNAL_TYPE_TOKENS,
    RTGS_TYPE_TOKENS,
    BankTransferContext,
    route_body_fields,
    title_of,
)
from tests.services.debit.bank_transfer_direct import (
    IDEMPOTENT,
    INQ_PENDING,
    INQ_SUCCEED,
    REJECT_TITLES,
    DirectRouteFlow,
)
from tests.services.debit.bank_transfer_routing import skip_if_switch_setup

_KIND_TYPE = {
    "ACH": ACH_TYPE_TOKENS | {"ACH", 0, "0"},
    "internal": INTERNAL_TYPE_TOKENS | {"INTERNAL", 2, "2"},
    "SATNA": RTGS_TYPE_TOKENS | {"RTGS", "RTGS_TRANSFER", 1, "1"},
}


def assert_direct_case(flow: DirectRouteFlow, ctx: BankTransferContext, case: str) -> None:
    """Dispatch Then for a direct-route case."""
    dispatch = {
        "happy path": assert_happy,
        "zero amount": assert_hard_reject,
        "invalid source iban": assert_hard_reject,
        "non home source": assert_non_home,
        "same bank target": assert_same_bank,
        "duplicate tracking": assert_duplicate,
        "inactive client": assert_hard_reject,
        "wrong agenda": assert_wrong_agenda,
        "missing source": assert_hard_reject,
        "settle eventually": assert_settle,
        "wrong client ids": assert_hard_reject,
    }
    dispatch[case](flow, ctx)


def assert_happy(flow: DirectRouteFlow, ctx: BankTransferContext) -> None:
    """Happy path: route+execute+inquiry contract."""
    attach_api_result("direct-route", ctx.route_result)
    report = AssertionReport(f"{flow.rail} direct-route happy")
    report.equals("route HTTP", actual=ctx.route_result.get("status_code"), expected=200)
    body = route_body_fields(ctx.route_result)
    report.check("typed", isinstance(body, TransferRouteBody))
    kind = str(ctx.flags.get("ft_shahin_kind") or "ACH")
    tokens = _KIND_TYPE[kind]
    if isinstance(body, TransferRouteBody):
        report.equals("client", actual=body.client_code, expected=flow.client_code())
        report.equals("bank", actual=body.bank_code, expected=flow.bank_code())
        report.check(f"type {kind}", body.type in tokens)
        if flow.rail == "mellat":
            report.equals("fee", actual=body.fee, expected=0)
    report.equals("mongo count", actual=ctx.mongo_count, expected=1)
    code2 = int((ctx.second_result or {}).get("status_code") or 0)
    report.check("2nd execute ok-or-reject", code2 in (200, 422))
    if code2 == 422:
        report.check(
            "2nd title",
            title_of(ctx.second_result) in IDEMPOTENT | REJECT_TITLES,
        )
    inq = ctx.flags.get("inquiry_status")
    report.check("inquiry status", inq in (INQ_PENDING, INQ_SUCCEED))
    report.equals("mongo client", actual=ctx.flags.get("mongo_client"), expected=flow.client_code())
    report.equals("mongo agenda", actual=ctx.flags.get("mongo_agenda"), expected="TREASURY")
    report.check(f"mongo type {kind}", ctx.flags.get("mongo_type") in tokens)
    report.assert_all()


def assert_hard_reject(flow: DirectRouteFlow, ctx: BankTransferContext) -> None:
    """422 Platform title and no mongo row."""
    attach_api_result("direct-route reject", ctx.last_result)
    title = ctx.flags.get("title")
    if isinstance(title, str) or title is None:
        skip_if_switch_setup(title, reason="direct-route Switch setup")
    report = AssertionReport(f"{flow.rail} direct-route reject")
    report.equals("HTTP", actual=ctx.last_result.get("status_code"), expected=422)
    report.check("title", title in REJECT_TITLES)
    report.check("no mongo", ctx.flags.get("doc_missing") is True)
    report.assert_all()


def assert_non_home(flow: DirectRouteFlow, ctx: BankTransferContext) -> None:
    """Non-home source: Melli hard reject; Mellat reject or not-mellat client."""
    attach_api_result("non-home source", ctx.last_result)
    code = int(ctx.last_result.get("status_code") or 0)
    title = ctx.flags.get("title")
    if code == 422 and (isinstance(title, str) or title is None):
        skip_if_switch_setup(title, reason="direct-route Switch setup")
    report = AssertionReport(f"{flow.rail} non-home source")
    if flow.rail == "melli":
        report.equals("HTTP", actual=code, expected=422)
        report.check("title", title in REJECT_TITLES)
        report.check("no mongo", ctx.flags.get("doc_missing") is True)
    elif code == 422:
        report.check("title", ctx.flags.get("title") in REJECT_TITLES)
        report.check("no mongo", ctx.flags.get("doc_missing") is True)
    else:
        report.equals("HTTP", actual=code, expected=200)
        body = route_body_fields(ctx.last_result)
        if isinstance(body, TransferRouteBody):
            report.check(
                "not home rail",
                body.client_code != flow.client_code() or body.bank_code != flow.bank_code(),
            )
    report.assert_all()


def assert_same_bank(flow: DirectRouteFlow, ctx: BankTransferContext) -> None:
    """Same-bank target: 422 or INTERNAL (not ACH)."""
    attach_api_result("same-bank", ctx.last_result)
    code = int(ctx.last_result.get("status_code") or 0)
    title = ctx.flags.get("title")
    if code == 422 and (isinstance(title, str) or title is None):
        skip_if_switch_setup(title, reason="direct-route Switch setup")
    report = AssertionReport(f"{flow.rail} same-bank target")
    if code == 422:
        report.check("title", title in REJECT_TITLES)
        report.check("no mongo", ctx.mongo_doc is None)
    else:
        report.equals("HTTP", actual=code, expected=200)
        route_type = ctx.flags.get("route_type")
        mongo_type = ctx.flags.get("mongo_type")
        report.check(
            "not ACH",
            route_type not in ACH_TYPE_TOKENS
            or mongo_type in INTERNAL_TYPE_TOKENS | {"INTERNAL", 2, "2"},
        )
    report.assert_all()


def assert_duplicate(flow: DirectRouteFlow, ctx: BankTransferContext) -> None:
    """Duplicate tracking keeps one mongo row."""
    attach_api_result("first", ctx.route_result)
    attach_api_result("second", ctx.second_result)
    report = AssertionReport(f"{flow.rail} duplicate direct-route")
    report.equals("first", actual=ctx.route_result.get("status_code"), expected=200)
    code2 = int(ctx.second_result.get("status_code") or 0)
    report.check("second ok-or-reject", code2 in (200, 422))
    report.equals("mongo count", actual=ctx.mongo_count, expected=1)
    report.assert_all()


def assert_wrong_agenda(flow: DirectRouteFlow, ctx: BankTransferContext) -> None:
    """Wrong agenda is not TREASURY+bn_melli path."""
    attach_api_result("wrong agenda", ctx.last_result)
    code = int(ctx.last_result.get("status_code") or 0)
    title = ctx.flags.get("title")
    if code == 422 and (isinstance(title, str) or title is None):
        skip_if_switch_setup(title, reason="direct-route Switch setup")
    report = AssertionReport(f"{flow.rail} wrong agenda")
    if code == 422:
        report.check("title", title in REJECT_TITLES)
    else:
        report.equals("HTTP", actual=code, expected=200)
        report.check(
            "not treasury melli",
            not (ctx.flags.get("agenda") == "TREASURY" and ctx.flags.get("client") == "bn_melli"),
        )
    report.assert_all()


def assert_settle(flow: DirectRouteFlow, ctx: BankTransferContext) -> None:
    """Long-poll settle to DONE + inquiry SUCCEED."""
    attach_api_result("inquiry", ctx.inquiry_result)
    report = AssertionReport(f"{flow.rail} direct-route settle")
    report.equals("mongo DONE", actual=ctx.flags.get("mongo_status"), expected="DONE")
    report.equals(
        "inquiry SUCCEED",
        actual=ctx.flags.get("inquiry_status"),
        expected=INQ_SUCCEED,
    )
    report.assert_all()
