"""Assertion helpers for the Platform top-up operators list (``GET /top-ups/operators``)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from tests.api.super_app.internet.operators import TopUpOperator, TopUpOperatorsBody
from tests.services.assert_report import AssertionReport, assert_isinstance, assert_status_ok


def _body(operators_result: dict[str, Any]) -> TopUpOperatorsBody:
    body = operators_result["body"]
    assert_isinstance("Top-up operators response body", body, TopUpOperatorsBody)
    return body


def _operator_or_none(body: TopUpOperatorsBody, operator_id: str) -> TopUpOperator | None:
    return body.operator_with_id(operator_id)


def assert_operator_list_returned_successfully(operators_result: dict[str, Any]) -> None:
    """HTTP 200 with a non-empty operator list."""
    assert_status_ok("Top-up operators request", operators_result)
    body = _body(operators_result)
    AssertionReport("Top-up operator list is populated").truthy(
        "operators list is non-empty", body.operators
    ).assert_all()


def assert_operator_has_id(
    operators_result: dict[str, Any], operator_name: str, operator_id: str
) -> None:
    """``operator_name`` is present with the expected ``operatorId``."""
    body = _body(operators_result)
    operator = body.operator_named(operator_name)
    report = AssertionReport(f"Top-up operator {operator_name} has operator id {operator_id}")
    report.truthy(f"operator {operator_name} is present", operator)
    if operator is not None:
        report.equals("operator id", actual=operator.operator_id, expected=operator_id)
    report.assert_all()


def assert_operator_includes_prefix(
    operators_result: dict[str, Any], operator_id: str, prefix: str
) -> None:
    """Operator ``operator_id`` lists ``prefix`` among its prefixes."""
    body = _body(operators_result)
    operator = _operator_or_none(body, operator_id)
    report = AssertionReport(f"Operator id {operator_id} lists prefix {prefix}")
    report.truthy(f"operator id {operator_id} is present", operator)
    if operator is not None:
        report.check(
            f"operator id {operator_id} lists prefix {prefix}", operator.has_prefix(prefix)
        )
    report.assert_all()


def assert_every_prefix_has_type(operators_result: dict[str, Any]) -> None:
    """Every prefix, across every operator, declares at least one ``types`` entry."""
    body = _body(operators_result)
    report = AssertionReport("Every top-up operator prefix declares a type")
    for operator in body.operators:
        for prefix in operator.prefixes:
            report.check(
                f"{operator.name} prefix {prefix.value!r} has at least one type", bool(prefix.types)
            )
    report.assert_all()


def assert_operator_exists(operators_result: dict[str, Any], operator_id: str) -> None:
    """Operator ``operator_id`` is present in the response."""
    body = _body(operators_result)
    operator = _operator_or_none(body, operator_id)
    AssertionReport(f"Operator id {operator_id} exists").truthy(
        f"operator id {operator_id} is present", operator
    ).assert_all()


def assert_operator_has_nonempty_prefixes(
    operators_result: dict[str, Any], operator_id: str
) -> None:
    """Operator ``operator_id`` has a non-empty ``prefixes`` list."""
    body = _body(operators_result)
    operator = _operator_or_none(body, operator_id)
    report = AssertionReport(f"Operator id {operator_id} has a non-empty prefix list")
    report.truthy(f"operator id {operator_id} is present", operator)
    if operator is not None:
        report.truthy(f"operator id {operator_id} prefixes is non-empty", operator.prefixes)
    report.assert_all()


def assert_operator_prefixes_well_formed(
    operators_result: dict[str, Any], operator_id: str
) -> None:
    """Every prefix of operator ``operator_id`` starts with ``09``, 4-5 chars long."""
    body = _body(operators_result)
    operator = _operator_or_none(body, operator_id)
    report = AssertionReport(f"Every prefix of operator id {operator_id} is well-formed")
    report.truthy(f"operator id {operator_id} is present", operator)
    if operator is not None:
        for prefix in operator.prefixes:
            value = prefix.value
            is_str = isinstance(value, str)
            report.check(
                f"prefix {value!r} starts with '09' and is 4 or 5 characters long",
                is_str and value.startswith("09") and len(value) in (4, 5),
            )
    report.assert_all()


def assert_every_prefix_starts_with_09(operators_result: dict[str, Any]) -> None:
    """Every prefix value, across every operator, starts with ``09``."""
    body = _body(operators_result)
    report = AssertionReport('Every top-up operator prefix starts with "09"')
    for operator in body.operators:
        for prefix in operator.prefixes:
            value = prefix.value
            report.check(
                f"{operator.name} prefix {value!r} starts with '09'",
                isinstance(value, str) and value.startswith("09"),
            )
    report.assert_all()


def assert_every_prefix_length_4_or_5(operators_result: dict[str, Any]) -> None:
    """Every prefix value, across every operator, is 4 or 5 characters long."""
    body = _body(operators_result)
    report = AssertionReport("Every top-up operator prefix is 4 or 5 characters long")
    for operator in body.operators:
        for prefix in operator.prefixes:
            value = prefix.value
            report.check(
                f"{operator.name} prefix {value!r} is 4 or 5 characters long",
                isinstance(value, str) and len(value) in (4, 5),
            )
    report.assert_all()


def assert_every_prefix_is_nonempty_string(operators_result: dict[str, Any]) -> None:
    """Every prefix value, across every operator, is a non-empty string."""
    body = _body(operators_result)
    report = AssertionReport("Every top-up operator prefix value is a non-empty string")
    for operator in body.operators:
        for prefix in operator.prefixes:
            value = prefix.value
            report.check(
                f"{operator.name} prefix {value!r} is a non-empty string",
                isinstance(value, str) and value != "",
            )
    report.assert_all()


def assert_operator_has_no_duplicate_prefix(
    operators_result: dict[str, Any], operator_id: str
) -> None:
    """Operator ``operator_id`` lists each prefix value at most once."""
    body = _body(operators_result)
    operator = _operator_or_none(body, operator_id)
    report = AssertionReport(f"Operator id {operator_id} lists no duplicate prefix")
    report.truthy(f"operator id {operator_id} is present", operator)
    if operator is not None:
        counts = Counter(operator.prefix_values())
        duplicates = [value for value, count in counts.items() if count > 1]
        report.check(
            f"operator id {operator_id} has no duplicate prefixes",
            not duplicates,
            detail=f"duplicates={duplicates!r}" if duplicates else "",
        )
    report.assert_all()


def assert_no_prefix_overlap_across_operators(operators_result: dict[str, Any]) -> None:
    """No prefix value is listed under more than one operator."""
    body = _body(operators_result)
    owners: dict[Any, set[str]] = {}
    for operator in body.operators:
        for value in operator.prefix_values():
            owners.setdefault(value, set()).add(operator.name)
    overlapping = {value: names for value, names in owners.items() if len(names) > 1}
    AssertionReport("No prefix is listed under more than one operator").check(
        "no prefix value is owned by more than one operator",
        not overlapping,
        detail=f"overlaps={overlapping!r}" if overlapping else "",
    ).assert_all()
