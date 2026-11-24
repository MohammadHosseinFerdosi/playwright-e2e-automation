"""Assertions for Nemo app-gateway route-prediction / fee."""

from __future__ import annotations

from tests.services.assert_report import AssertionReport, attach_api_result
from tests.services.debit.nemo_gateway import NemoGatewayContext


def assert_gateway_case(ctx: NemoGatewayContext, case: str) -> None:
    """Dispatch gateway Then."""
    {
        "mellat pin prediction": assert_pinned,
        "shahin pin prediction": assert_pinned,
        "manual pin prediction": assert_pinned,
        "manual mellat split prediction": assert_split,
        "transfer route prediction": assert_pinned,
        "transfer fee": assert_fee,
        "gateway prep then mellat route": assert_prep_route,
    }[case](ctx)


def assert_pinned(ctx: NemoGatewayContext) -> None:
    """Pinned gateway prediction SUCCESS."""
    attach_api_result("route prediction", ctx.last_result)
    report = AssertionReport("nemo gateway pin prediction")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=200)
    report.equals("title", actual=ctx.flags.get("title"), expected="SUCCESS")
    got = ctx.flags.get("client_code")
    if got:
        report.equals(
            "client",
            actual=got,
            expected=ctx.flags.get("expected_client_code"),
        )
    bank = ctx.flags.get("bank_code")
    if bank:
        report.equals(
            "bank",
            actual=bank,
            expected=ctx.flags.get("expected_bank_code"),
        )
    report.assert_all()


def assert_split(ctx: NemoGatewayContext) -> None:
    """50/50 split prefers manual ACH."""
    attach_api_result("split prediction", ctx.last_result)
    report = AssertionReport("nemo manual/mellat split")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=200)
    report.equals("title", actual=ctx.flags.get("title"), expected="SUCCESS")
    report.equals(
        "client",
        actual=ctx.flags.get("client_code"),
        expected=ctx.flags.get("expected_client_code"),
    )
    report.assert_all()


def assert_fee(ctx: NemoGatewayContext) -> None:
    """Transfer fee SUCCESS."""
    attach_api_result("transfer fee", ctx.last_result)
    report = AssertionReport("nemo transfer fee")
    report.equals("HTTP", actual=ctx.flags.get("status_code"), expected=200)
    report.equals("title", actual=ctx.flags.get("title"), expected="SUCCESS")
    report.assert_all()


def assert_prep_route(ctx: NemoGatewayContext) -> None:
    """Predict+fee then Mellat BT route."""
    assert_fee(ctx)
    attach_api_result("bt route", ctx.route_result)
    report = AssertionReport("nemo prep then mellat route")
    report.equals("BT HTTP", actual=ctx.flags.get("bt_status"), expected=200)
    report.assert_all()
