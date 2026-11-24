"""Assertion helpers for the Platform internet bundle catalog (``POST /bundles/{operatorId}``)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from tests.api.super_app.internet.bundles import (
    CATEGORY_ALL,
    CATEGORY_POPULAR,
    BundlesBody,
    CellNumberType,
)
from tests.services.assert_report import AssertionReport, assert_isinstance, assert_status_ok


def _body(bundles_result: dict[str, Any]) -> BundlesBody:
    body = bundles_result["body"]
    assert_isinstance("Bundles response body", body, BundlesBody)
    return body


def assert_bundle_catalog_returned_successfully(bundles_result: dict[str, Any]) -> None:
    """HTTP 200 with a non-empty category list."""
    assert_status_ok("Bundles request", bundles_result)
    body = _body(bundles_result)
    AssertionReport("Bundle catalog is populated").truthy(
        "categories list is non-empty", body.categories
    ).assert_all()


def assert_category_present(bundles_result: dict[str, Any], title: str) -> None:
    """Category ``title`` is present in the response."""
    body = _body(bundles_result)
    AssertionReport(f'Category "{title}" is present').truthy(
        f'category "{title}" is present', body.category_named(title)
    ).assert_all()


def assert_every_package_has_bundle_id(bundles_result: dict[str, Any]) -> None:
    """Every internet package has a non-empty ``bundleId``."""
    body = _body(bundles_result)
    report = AssertionReport("Every internet package has a non-empty bundle id")
    for category in body.categories:
        for package in category.packages():
            report.check(
                f"{category.title}: package {package.description!r} has a bundle id",
                bool(package.bundle_id),
            )
    report.assert_all()


def assert_every_package_has_positive_amount(bundles_result: dict[str, Any]) -> None:
    """Every internet package's ``amount`` is greater than zero."""
    body = _body(bundles_result)
    report = AssertionReport("Every internet package has a positive amount")
    for category in body.categories:
        for package in category.packages():
            report.check(
                f"{category.title}: bundle {package.bundle_id} amount is positive",
                package.amount > 0,
                detail=f"amount={package.amount!r}",
            )
    report.assert_all()


def assert_every_package_raw_amount_within_amount(bundles_result: dict[str, Any]) -> None:
    """Every internet package's ``rawAmount`` is positive and does not exceed ``amount``."""
    body = _body(bundles_result)
    report = AssertionReport("Every internet package's raw amount is within its amount")
    for category in body.categories:
        for package in category.packages():
            report.check(
                f"{category.title}: bundle {package.bundle_id} raw amount is positive",
                package.raw_amount > 0,
                detail=f"raw_amount={package.raw_amount!r}",
            )
            report.check(
                f"{category.title}: bundle {package.bundle_id} amount >= raw amount",
                package.amount >= package.raw_amount,
                detail=f"amount={package.amount!r} raw_amount={package.raw_amount!r}",
            )
    report.assert_all()


def assert_every_package_has_description(bundles_result: dict[str, Any]) -> None:
    """Every internet package has a non-empty ``description``."""
    body = _body(bundles_result)
    report = AssertionReport("Every internet package has a non-empty description")
    for category in body.categories:
        for package in category.packages():
            report.check(
                f"{category.title}: bundle {package.bundle_id} has a description",
                bool(package.description),
            )
    report.assert_all()


def assert_every_package_has_positive_duration(bundles_result: dict[str, Any]) -> None:
    """Every internet package's ``duration`` is greater than zero."""
    body = _body(bundles_result)
    report = AssertionReport("Every internet package has a positive duration")
    for category in body.categories:
        for package in category.packages():
            report.check(
                f"{category.title}: bundle {package.bundle_id} duration is positive",
                package.duration > 0,
                detail=f"duration={package.duration!r}",
            )
    report.assert_all()


def assert_no_duplicate_package_in_section(bundles_result: dict[str, Any]) -> None:
    """No ``bundleId`` repeats within a single section."""
    body = _body(bundles_result)
    report = AssertionReport("No bundle section lists a duplicate package")
    for category in body.categories:
        for section in category.bundle_sections:
            counts = Counter(section.package_ids())
            duplicates = [pid for pid, count in counts.items() if count > 1]
            report.check(
                f"{category.title} / {section.title} has no duplicate package",
                not duplicates,
                detail=f"duplicates={duplicates!r}" if duplicates else "",
            )
    report.assert_all()


def assert_need_approval_implies_message(bundles_result: dict[str, Any]) -> None:
    """``needApproval is True`` if and only if ``approvalMessage`` is a non-empty string."""
    body = _body(bundles_result)
    report = AssertionReport("Approval-required packages carry an approval message")
    for category in body.categories:
        for package in category.packages():
            report.check(
                f"{category.title}: bundle {package.bundle_id} needApproval/approvalMessage "
                "are consistent",
                package.need_approval == bool(package.approval_message),
                detail=(
                    f"needApproval={package.need_approval!r} "
                    f"approvalMessage={package.approval_message!r}"
                ),
            )
    report.assert_all()


def assert_popular_category_is_subset_of_catalog(bundles_result: dict[str, Any]) -> None:
    """When present, every "پرطرفدار" package also appears in some other category.

    Conditional: the popular category is driven by purchase history and is absent for
    users/operators with no prior purchases — a no-op pass with a note in that case.
    """
    body = _body(bundles_result)
    popular = body.category_named(CATEGORY_POPULAR)
    report = AssertionReport('"پرطرفدار" only lists packages that exist elsewhere')
    if popular is None:
        report.note('"پرطرفدار" category is absent from this response — nothing to check')
        report.assert_all()
        return
    catalog_ids = {
        pid
        for category in body.categories
        if category.title not in (CATEGORY_POPULAR, CATEGORY_ALL)
        for pid in category.package_ids()
    }
    for pid in popular.package_ids():
        report.check(f"popular bundle {pid} exists elsewhere in the catalog", pid in catalog_ids)
    report.assert_all()


def assert_all_category_is_union_of_others(bundles_result: dict[str, Any]) -> None:
    """When present, "همه" has no duplicates and equals the union of the other categories.

    Conditional: "همه" is absent from some operator responses (e.g. the sample payload for
    operator 1) — a no-op pass with a note in that case.
    """
    body = _body(bundles_result)
    all_category = body.category_named(CATEGORY_ALL)
    report = AssertionReport('"همه" is the deduplicated union of the other categories')
    if all_category is None:
        report.note('"همه" category is absent from this response — nothing to check')
        report.assert_all()
        return
    all_ids = all_category.package_ids()
    counts = Counter(all_ids)
    duplicates = [pid for pid, count in counts.items() if count > 1]
    report.check(
        '"همه" has no duplicate package',
        not duplicates,
        detail=f"duplicates={duplicates!r}" if duplicates else "",
    )
    expected_union = {
        pid
        for category in body.categories
        if category.title not in (CATEGORY_POPULAR, CATEGORY_ALL)
        for pid in category.package_ids()
    }
    report.check(
        '"همه" package set equals the union of the other categories',
        set(all_ids) == expected_union,
        detail=f"only_in_all={set(all_ids) - expected_union!r} "
        f"missing_from_all={expected_union - set(all_ids)!r}",
    )
    report.assert_all()


def assert_bundle_catalog_request_succeeds(bundles_result: dict[str, Any]) -> None:
    """HTTP 200 with a well-formed (parsed) catalog — categories may legitimately be empty.

    For a freshly generated random cell number, the operator may have no real subscriber
    behind it, so an empty catalog is a valid outcome, unlike ``assert_bundle_catalog_
    returned_successfully`` which is used with the known-good fixed test number.
    """
    assert_status_ok("Bundles request", bundles_result)
    _body(bundles_result)


def assert_request_handled_gracefully(bundles_result: dict[str, Any]) -> None:
    """The request never crashes the backend, whatever the input.

    Covers edge/negative inputs (mismatched operator id vs. cell number, malformed cell
    numbers, invalid ``cellNumberType`` values) whose exact contract isn't confirmed yet —
    see the "best-effort" note in ``bundles.feature``. Only asserts the response is well-
    formed: never a 5xx, and a 200 always carries a real, parsed catalog. A non-200 response
    is allowed to carry no body at all (confirmed live: some 400s return an empty body).
    """
    status_code = bundles_result.get("status_code")
    body = bundles_result.get("body")
    report = AssertionReport("Bundle catalog request is handled gracefully")
    report.check(
        "HTTP status is not a server error (5xx)",
        isinstance(status_code, int) and status_code < 500,
        detail=f"status_code={status_code!r}",
    )
    if status_code == 200:
        report.check("200 response body parses as a bundle catalog", isinstance(body, BundlesBody))
    report.assert_all()


def assert_bundle_types_match_sim_card_type(
    bundles_result: dict[str, Any], expected_type: CellNumberType
) -> None:
    """Every ``Bundle.type`` in the response equals the requested SIM card type."""
    body = _body(bundles_result)
    report = AssertionReport(f"Bundle type matches the requested SIM card type {expected_type!r}")
    for category in body.categories:
        for section in category.bundle_sections:
            for bundle in section.bundles:
                report.check(
                    f"{category.title} / {section.title}: bundle type matches",
                    bundle.type == expected_type.value,
                    detail=f"expected={expected_type.value!r} actual={bundle.type!r}",
                )
    report.assert_all()
