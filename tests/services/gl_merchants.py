"""General ledger — merchant Rahkaran-code integrity checks (service layer).

Owns the pagination loop and multi-check business logic behind each Then
step, per ``.cursor/rules/step-definitions.mdc`` (steps stay thin
orchestration only) — port of
``src/steps/gl/detailed-code-mangement/merchants-with-rahkaran-codes.resource``.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Any

from tests.api.client import ApiClient
from tests.api.gl.detailed_code_management.merchants_with_rahkaran_codes import (
    MerchantsWithRahkaranCodesPage,
    MerchantWithRahkaranCode,
    search_merchants_with_rahkaran_codes,
)
from tests.api.gl.detailed_code_management.merchants_without_rahkaran_codes import (
    MerchantsWithoutRahkaranCodesPage,
    MerchantWithoutRahkaranCode,
    search_merchants_without_rahkaran_codes,
    search_suspended_merchants,
)
from tests.services.api_assert import ensure_ok
from tests.services.assert_report import AssertionReport

_PAGE_SIZE = 250
_RAHKARAN_CODE_RE = re.compile(r"^[0-9]{6}$")

# Plain Gherkin Example wording -> API field name (mirrors the three Robot
# "Filter Merchants By ..." test cases, collapsed into one Scenario Outline —
# see .cursor/rules/migration-quality.mdc).
FILTER_FIELD_KEYS: dict[str, str] = {
    "business name": "businessName",
    "rahkaran code": "rahkaranCode",
    "account number": "accountNumber",
}

WITHOUT_RAHKARAN_FILTER_FIELDS: frozenset[str] = frozenset({"business name"})

FILTER_WITH_RAHKARAN_STEP = (
    r"^the merchants with Rahkaran codes are filtered by "
    r"(?P<filter_field>[A-Za-z0-9 ]+)$"
)
FILTERED_CONTAIN_WITH_STEP = (
    r"^the filtered merchants with Rahkaran codes must contain the "
    r"(?P<filter_field>[A-Za-z0-9 ]+)$"
)
FILTER_WITHOUT_RAHKARAN_STEP = (
    r"^the merchants without Rahkaran codes are filtered by "
    r"(?P<filter_field>[A-Za-z0-9 ]+)$"
)
FILTERED_CONTAIN_WITHOUT_STEP = (
    r"^the filtered merchants without Rahkaran codes must contain the "
    r"(?P<filter_field>[A-Za-z0-9 ]+)$"
)


def known_filter_fields() -> tuple[str, ...]:
    """Gherkin filter-field tails registered for merchants with Rahkaran codes."""
    return tuple(FILTER_FIELD_KEYS)


def known_without_rahkaran_filter_fields() -> tuple[str, ...]:
    """Gherkin filter-field tails registered for merchants without Rahkaran codes."""
    return tuple(sorted(WITHOUT_RAHKARAN_FILTER_FIELDS))


_ATTR_FOR_FIELD: dict[str, str] = {
    "businessName": "business_name",
    "rahkaranCode": "rahkaran_code",
    "accountNumber": "account_number",
    "nationalCode": "national_code",
}


@dataclass
class FilteredMerchants:
    """Result of filtering merchants by one field, held for the Then step."""

    merchants: list[MerchantWithRahkaranCode]
    selected: MerchantWithRahkaranCode
    field: str


def fetch_all_merchants_with_rahkaran_codes(
    client: ApiClient,
) -> list[MerchantWithRahkaranCode]:
    """Fetch every page of merchants with Rahkaran codes.

    Args:
        client: Microservice-side ``ApiClient``.

    Returns:
        All merchant records across every page.
    """
    first = ensure_ok(
        search_merchants_with_rahkaran_codes(client, page=0, size=_PAGE_SIZE),
        context="GL search merchants with Rahkaran codes (page 0)",
    )
    page_body = _as_page(first["body"])
    merchants = list(page_body.merchants)

    for page in range(1, page_body.total_pages):
        result = ensure_ok(
            search_merchants_with_rahkaran_codes(client, page=page, size=_PAGE_SIZE),
            context=f"GL search merchants with Rahkaran codes (page {page})",
        )
        merchants.extend(_as_page(result["body"]).merchants)

    return merchants


def assert_rahkaran_codes_are_six_digits(merchants: list[MerchantWithRahkaranCode]) -> None:
    """Every merchant's Rahkaran code must be exactly six digits."""
    report = AssertionReport("All Rahkaran codes are exactly six digits")
    for merchant in merchants:
        code = merchant.rahkaran_code or ""
        report.check(
            f"{merchant.business_name} rahkaran code",
            bool(_RAHKARAN_CODE_RE.match(code)),
            detail=f"got {code!r}",
        )
    report.assert_all()


def assert_same_national_code_shares_rahkaran_code(
    merchants: list[MerchantWithRahkaranCode],
) -> None:
    """Merchants sharing a national code must share the same Rahkaran code."""
    report = AssertionReport("Same national code implies same Rahkaran code")
    seen: dict[str, str] = {}
    for merchant in merchants:
        national = (merchant.national_code or "").strip()
        rahkaran = (merchant.rahkaran_code or "").strip()
        if not national:
            continue
        expected = seen.setdefault(national, rahkaran)
        report.equals(f"national code {national} rahkaran code", actual=rahkaran, expected=expected)
    report.assert_all()


def assert_all_have_national_code(merchants: list[MerchantWithRahkaranCode]) -> None:
    """Every merchant with a Rahkaran code must also have a national code."""
    report = AssertionReport("Every merchant has a national code")
    for merchant in merchants:
        report.truthy(f"{merchant.business_name} national code", merchant.national_code)
    report.assert_all()


def filter_merchants_by_field(
    client: ApiClient,
    merchants: list[MerchantWithRahkaranCode],
    field_label: str,
) -> FilteredMerchants:
    """Pick a random merchant and re-query filtered by its value for ``field_label``.

    Args:
        client: Microservice-side ``ApiClient``.
        merchants: Full merchant list to pick the random sample from.
        field_label: Plain Gherkin Example wording — resolved via
            ``FILTER_FIELD_KEYS``.

    Returns:
        The filtered merchant list plus the merchant/field used to filter.
    """
    field = _require_filter_field(field_label)
    attr = _ATTR_FOR_FIELD[field]
    candidates = [m for m in merchants if getattr(m, attr, None)]
    if not candidates:
        raise RuntimeError(f"No merchant has a value for field {field!r} to filter by.")
    selected = random.choice(candidates)
    value = getattr(selected, attr)

    payload = {
        "restrictions": [{"type": "simple", "field": field, "value": value, "operation": "eq"}],
        "orders": [{"field": "creationDate", "order": "desc"}],
    }
    result = ensure_ok(
        search_merchants_with_rahkaran_codes(client, page=0, size=_PAGE_SIZE, payload=payload),
        context=f"GL filter merchants by {field}",
    )
    return FilteredMerchants(
        merchants=_as_page(result["body"]).merchants,
        selected=selected,
        field=field,
    )


def assert_filtered_merchants_match_field(
    filtered: FilteredMerchants, filter_field_label: str
) -> None:
    """Every filtered merchant's value for ``field`` must match the selected merchant's.

    Args:
        filtered: Result of ``filter_merchants_by_field``.
        filter_field_label: Plain Gherkin Example wording for the field that was
            filtered on — cross-checked against ``filtered.field`` so a mismatch
            between the When/Then Outline placeholders fails loudly.
    """
    expected_field = _require_filter_field(filter_field_label)
    attr = _ATTR_FOR_FIELD[expected_field]
    expected = getattr(filtered.selected, attr)
    report = AssertionReport(f"Filtered merchants match selected {expected_field}")
    report.equals("Filter field used", actual=filtered.field, expected=expected_field)
    for merchant in filtered.merchants:
        actual = getattr(merchant, attr, None)
        report.check(
            f"{merchant.business_name} {expected_field}",
            actual is not None and str(expected) in str(actual),
            detail=f"expected to contain {expected!r}, got {actual!r}",
        )
    report.assert_all()


def _as_page(body: object) -> MerchantsWithRahkaranCodesPage:
    """Narrow the ``{status_code, body}`` envelope's body to a parsed page."""
    if isinstance(body, MerchantsWithRahkaranCodesPage):
        return body
    raise RuntimeError(f"Unexpected GL search response shape: {body!r}")


# --- Merchants WITHOUT a Rahkaran code -------------------------------------
#
# Port of merchants-without-rahkaran-codes.resource. Separate search endpoint
# and JSON shape from the "with codes" search above, so it gets its own
# fetch/filter/assert functions rather than being force-fit into the same
# ones (see MerchantsWithoutRahkaranCodesPage docstring).


@dataclass
class FilteredMerchantsWithoutCode:
    """Result of filtering "without Rahkaran code" merchants by business name."""

    merchants: list[MerchantWithoutRahkaranCode]
    selected: MerchantWithoutRahkaranCode


def fetch_all_merchants_without_rahkaran_codes(
    client: ApiClient,
) -> list[MerchantWithoutRahkaranCode]:
    """Fetch every page of merchants that have no Rahkaran code yet."""
    first = ensure_ok(
        search_merchants_without_rahkaran_codes(client, page=0, size=_PAGE_SIZE),
        context="GL search merchants without Rahkaran codes (page 0)",
    )
    page_body = _as_page_without(first["body"])
    merchants = list(page_body.merchants)

    for page in range(1, page_body.total_pages):
        result = ensure_ok(
            search_merchants_without_rahkaran_codes(client, page=page, size=_PAGE_SIZE),
            context=f"GL search merchants without Rahkaran codes (page {page})",
        )
        merchants.extend(_as_page_without(result["body"]).merchants)

    return merchants


def assert_no_merchant_has_rahkaran_code(merchants: list[MerchantWithoutRahkaranCode]) -> None:
    """None of the "without Rahkaran code" merchants should actually have one."""
    report = AssertionReport("No merchant in the unassigned list has a Rahkaran code")
    for merchant in merchants:
        report.check(
            f"{merchant.business_name} has no rahkaran code",
            not merchant.rahkaran_code,
            detail=f"got {merchant.rahkaran_code!r}",
        )
    report.assert_all()


def pick_random_merchant_without_code(
    merchants: list[MerchantWithoutRahkaranCode],
) -> MerchantWithoutRahkaranCode:
    """Pick one merchant at random (used to seed the filter/suspend scenarios)."""
    candidates = [m for m in merchants if m.business_name]
    if not candidates:
        raise RuntimeError("No merchant with a business name to select from.")
    return random.choice(candidates)


def filter_merchants_without_rahkaran_by_name(
    client: ApiClient,
    merchants: list[MerchantWithoutRahkaranCode],
    filter_field: str,
) -> FilteredMerchantsWithoutCode:
    """Pick a random merchant and re-query filtered by ``filter_field``.

    Raises:
        KeyError: If ``filter_field`` is not a registered without-codes tail.
    """
    if filter_field not in WITHOUT_RAHKARAN_FILTER_FIELDS:
        raise KeyError(
            f"No without-Rahkaran filter for {filter_field!r}; "
            f"known: {known_without_rahkaran_filter_fields()}"
        )
    selected = pick_random_merchant_without_code(merchants)
    result = ensure_ok(
        search_merchants_without_rahkaran_codes(
            client, page=0, size=_PAGE_SIZE, payload=_name_filter_payload(selected.business_name)
        ),
        context="GL filter merchants without Rahkaran code by business name",
    )
    return FilteredMerchantsWithoutCode(
        merchants=_as_page_without(result["body"]).merchants, selected=selected
    )


def assert_filtered_merchants_without_code_match_name(
    filtered: FilteredMerchantsWithoutCode,
    filter_field: str,
) -> None:
    """Every filtered merchant's business name must contain the selected one's.

    Raises:
        KeyError: If ``filter_field`` is not a registered without-codes tail.
    """
    if filter_field not in WITHOUT_RAHKARAN_FILTER_FIELDS:
        raise KeyError(
            f"No without-Rahkaran filter for {filter_field!r}; "
            f"known: {known_without_rahkaran_filter_fields()}"
        )
    expected = filtered.selected.business_name
    report = AssertionReport("Filtered merchants (without Rahkaran code) match business name")
    for merchant in filtered.merchants:
        actual = merchant.business_name
        report.check(
            f"{actual} business name",
            actual is not None and str(expected) in str(actual),
            detail=f"expected to contain {expected!r}, got {actual!r}",
        )
    report.assert_all()


def assert_merchant_absent_from_unassigned(client: ApiClient, business_name: str) -> None:
    """The named merchant must no longer appear in the "without code" list."""
    result = ensure_ok(
        search_merchants_without_rahkaran_codes(
            client, page=0, size=_PAGE_SIZE, payload=_name_filter_payload(business_name)
        ),
        context="GL check merchant absent from unassigned list",
    )
    merchants = _as_page_without(result["body"]).merchants
    AssertionReport(f"{business_name} absent from unassigned merchants list").check(
        "not found", not merchants, detail=f"found {len(merchants)} match(es)"
    ).assert_all()


def assert_merchant_present_in_suspended(client: ApiClient, business_name: str) -> None:
    """The named merchant must appear in the suspended-merchants list."""
    result = ensure_ok(
        search_suspended_merchants(
            client, page=0, size=_PAGE_SIZE, payload=_name_filter_payload(business_name)
        ),
        context="GL check merchant present in suspended list",
    )
    merchants = _as_page_without(result["body"]).merchants
    AssertionReport(f"{business_name} present in suspended merchants list").check(
        "found", bool(merchants), detail=f"found {len(merchants)} match(es)"
    ).assert_all()


def _require_filter_field(field_label: str) -> str:
    try:
        return FILTER_FIELD_KEYS[field_label]
    except KeyError as exc:
        raise KeyError(
            f"No GL filter field for {field_label!r}; known: {known_filter_fields()}"
        ) from exc


def _name_filter_payload(business_name: str | None) -> dict[str, Any]:
    return {
        "restrictions": [
            {"type": "simple", "field": "businessName", "value": business_name, "operation": "eq"}
        ],
        "orders": [{"field": "creationDate", "order": "desc"}],
    }


def _as_page_without(body: object) -> MerchantsWithoutRahkaranCodesPage:
    """Narrow the ``{status_code, body}`` envelope's body to a parsed page."""
    if isinstance(body, MerchantsWithoutRahkaranCodesPage):
        return body
    raise RuntimeError(f"Unexpected GL search response shape: {body!r}")
