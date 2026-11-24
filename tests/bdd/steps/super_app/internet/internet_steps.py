"""Step definitions for tests/bdd/features/super_app/internet/{operators,bundles}.feature."""

from __future__ import annotations

from typing import Any

from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient, ApiSide
from tests.api.super_app.internet.bundles import (
    CATEGORY_DAILY,
    CATEGORY_MIX,
    CATEGORY_MONTHLY,
    CATEGORY_POPULAR,
    CATEGORY_WEEKLY,
    CellNumberType,
    post_bundles,
)
from tests.api.super_app.internet.operators import get_top_up_operators
from tests.config.settings import Settings
from tests.services.assert_report import assert_status_ok, assert_truthy
from tests.services.fake_ids import fake_cell_number
from tests.services.super_app.internet.internet_bundles_asserts import (
    assert_all_category_is_union_of_others,
    assert_bundle_catalog_request_succeeds,
    assert_bundle_catalog_returned_successfully,
    assert_bundle_types_match_sim_card_type,
    assert_category_present,
    assert_every_package_has_bundle_id,
    assert_every_package_has_description,
    assert_every_package_has_positive_amount,
    assert_every_package_has_positive_duration,
    assert_every_package_raw_amount_within_amount,
    assert_need_approval_implies_message,
    assert_no_duplicate_package_in_section,
    assert_popular_category_is_subset_of_catalog,
    assert_request_handled_gracefully,
)
from tests.services.super_app.internet.internet_bundles_gherkin import request_bundle_catalog
from tests.services.super_app.internet.internet_operators_asserts import (
    assert_every_prefix_has_type,
    assert_every_prefix_is_nonempty_string,
    assert_every_prefix_length_4_or_5,
    assert_every_prefix_starts_with_09,
    assert_no_prefix_overlap_across_operators,
    assert_operator_exists,
    assert_operator_has_id,
    assert_operator_has_no_duplicate_prefix,
    assert_operator_has_nonempty_prefixes,
    assert_operator_includes_prefix,
    assert_operator_list_returned_successfully,
    assert_operator_prefixes_well_formed,
)
from tests.services.super_app.internet.internet_random_cell_number import (
    RandomCellNumber,
    random_cell_number_any_operator,
    random_cell_number_for_operator,
    random_cell_number_for_type,
)

scenarios("../features/super_app/internet/operators.feature")
scenarios("../features/super_app/internet/bundles.feature")

_BUNDLE_CATEGORY_TITLE_BY_KEY: dict[str, str] = {
    "DAILY": CATEGORY_DAILY,
    "WEEKLY": CATEGORY_WEEKLY,
    "MONTHLY": CATEGORY_MONTHLY,
    "MIX": CATEGORY_MIX,
    "POPULAR": CATEGORY_POPULAR,
}

# Verified live: SHATEL (operator id 4) returns an empty bundle catalog for any freshly
# generated, non-provisioned number — unlike MCI/MTN/RIGHTEL, which always return the
# standard duration categories. Excluded wherever a scenario needs a guaranteed catalog.
_OPERATORS_WITHOUT_DEFAULT_CATALOG = frozenset({"4"})


@given("no valid access token")
def _() -> None:
    """Precondition for the unauthenticated-request scenario — nothing to set up."""


@when("the top-up operators list is requested", target_fixture="operators_result")
def _(settings: Settings, access_token: str) -> dict[str, Any]:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return get_top_up_operators(client)


@when(
    "the top-up operators list is requested without a valid token",
    target_fixture="operators_result",
)
def _(settings: Settings) -> dict[str, Any]:
    with ApiClient(settings, ApiSide.GENERAL) as client:
        return get_top_up_operators(client)


@then("the operator list is returned successfully")
def _(operators_result: dict[str, Any]) -> None:
    assert_operator_list_returned_successfully(operators_result)


@then(
    parsers.parse('the operator list includes "{operator_name}" with operator id "{operator_id}"')
)
def _(operators_result: dict[str, Any], operator_name: str, operator_id: str) -> None:
    assert_operator_has_id(operators_result, operator_name, operator_id)


@then(parsers.parse('operator id "{operator_id}" includes prefix "{prefix}"'))
def _(operators_result: dict[str, Any], operator_id: str, prefix: str) -> None:
    assert_operator_includes_prefix(operators_result, operator_id, prefix)


@then("every operator prefix has at least one type")
def _(operators_result: dict[str, Any]) -> None:
    assert_every_prefix_has_type(operators_result)


@then(parsers.parse('operator id "{operator_id}" exists'))
def _(operators_result: dict[str, Any], operator_id: str) -> None:
    assert_operator_exists(operators_result, operator_id)


@then(parsers.parse('operator id "{operator_id}" has a non-empty prefix list'))
def _(operators_result: dict[str, Any], operator_id: str) -> None:
    assert_operator_has_nonempty_prefixes(operators_result, operator_id)


@then(parsers.parse('every prefix of operator id "{operator_id}" is a well-formed mobile prefix'))
def _(operators_result: dict[str, Any], operator_id: str) -> None:
    assert_operator_prefixes_well_formed(operators_result, operator_id)


@then('every operator prefix starts with "09"')
def _(operators_result: dict[str, Any]) -> None:
    assert_every_prefix_starts_with_09(operators_result)


@then("every operator prefix is 4 or 5 characters long")
def _(operators_result: dict[str, Any]) -> None:
    assert_every_prefix_length_4_or_5(operators_result)


@then("every operator prefix value is a non-empty string")
def _(operators_result: dict[str, Any]) -> None:
    assert_every_prefix_is_nonempty_string(operators_result)


@then(parsers.parse('operator id "{operator_id}" lists no duplicate prefix'))
def _(operators_result: dict[str, Any], operator_id: str) -> None:
    assert_operator_has_no_duplicate_prefix(operators_result, operator_id)


@then("no prefix is listed under more than one operator")
def _(operators_result: dict[str, Any]) -> None:
    assert_no_prefix_overlap_across_operators(operators_result)


@then("the request is rejected as unauthorized")
def _(operators_result: dict[str, Any]) -> None:
    assert_status_ok("Top-up operators request", operators_result, expected=401)


# --- Internet bundle catalog (tests/bdd/features/super_app/internet/bundles.feature) --


@when(
    parsers.re(
        r'^the bundle catalog is requested for operator id "(?P<operator_id>[^"]*)" '
        r'cell "(?P<cell_number>[^"]*)"'
        r'(?: SIM type "(?P<sim_card_type>[^"]*)")?$'
    ),
    target_fixture="bundles_result",
)
def _(
    settings: Settings,
    access_token: str,
    operator_id: str,
    cell_number: str,
    sim_card_type: str | None,
) -> dict[str, Any]:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return request_bundle_catalog(client, operator_id, cell_number, sim_card_type)


@given(
    parsers.parse('a random cell number for operator id "{operator_id}"'),
    target_fixture="random_cell_number",
)
def _(settings: Settings, access_token: str, operator_id: str) -> RandomCellNumber:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return random_cell_number_for_operator(client, operator_id)


@given(
    parsers.parse(
        'a random cell number for operator id "{operator_id}" and SIM type "{sim_card_type}"'
    ),
    target_fixture="random_cell_number",
)
def _(
    settings: Settings, access_token: str, operator_id: str, sim_card_type: str
) -> RandomCellNumber:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return random_cell_number_for_operator(
            client, operator_id, cell_number_type=CellNumberType[sim_card_type]
        )


@given(
    parsers.parse('a random cell number for SIM type "{sim_card_type}"'),
    target_fixture="random_cell_number",
)
def _(settings: Settings, access_token: str, sim_card_type: str) -> RandomCellNumber:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return random_cell_number_for_type(client, CellNumberType[sim_card_type])


@given("a random cell number for any operator", target_fixture="random_cell_number")
def _(settings: Settings, access_token: str) -> RandomCellNumber:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return random_cell_number_any_operator(client)


@given(
    "a random cell number for any operator with a default catalog",
    target_fixture="random_cell_number",
)
def _(settings: Settings, access_token: str) -> RandomCellNumber:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return random_cell_number_any_operator(
            client, exclude_operator_ids=_OPERATORS_WITHOUT_DEFAULT_CATALOG
        )


@given("a random cell number", target_fixture="random_cell_number")
def _() -> str:
    """Locally generated number for the unauthenticated-request scenario — no live call."""
    return fake_cell_number()


@when(
    parsers.parse(
        'the bundle catalog is requested for operator id "{operator_id}" '
        "using the random cell number"
    ),
    target_fixture="bundles_result",
)
def _(
    settings: Settings, access_token: str, operator_id: str, random_cell_number: RandomCellNumber
) -> dict[str, Any]:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return post_bundles(
            client,
            operator_id,
            random_cell_number.cell_number,
            cell_number_type=random_cell_number.cell_number_type,
        )


@when(
    "the bundle catalog is requested using the random cell number",
    target_fixture="bundles_result",
)
def _(
    settings: Settings, access_token: str, random_cell_number: RandomCellNumber
) -> dict[str, Any]:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        return post_bundles(
            client,
            random_cell_number.operator_id,
            random_cell_number.cell_number,
            cell_number_type=random_cell_number.cell_number_type,
        )


@when(
    parsers.re(
        r'^the bundle catalog is requested with cellNumberType "(?P<cell_number_type>[^"]*)"$'
    ),
    target_fixture="bundles_result",
)
def _(settings: Settings, access_token: str, cell_number_type: str) -> dict[str, Any]:
    with ApiClient(settings, ApiSide.GENERAL, auth_header=f"Bearer {access_token}") as client:
        random_number = random_cell_number_any_operator(client)
        return post_bundles(
            client,
            random_number.operator_id,
            random_number.cell_number,
            cell_number_type=cell_number_type,
        )


@when(
    "the bundle catalog is requested without a valid token",
    target_fixture="bundles_result",
)
def _(settings: Settings, random_cell_number: str) -> dict[str, Any]:
    with ApiClient(settings, ApiSide.GENERAL) as client:
        return post_bundles(client, 1, random_cell_number)


@then("the bundle catalog is returned successfully")
def _(bundles_result: dict[str, Any]) -> None:
    assert_bundle_catalog_returned_successfully(bundles_result)


@then("the bundle catalog request succeeds for the random number")
def _(bundles_result: dict[str, Any]) -> None:
    assert_bundle_catalog_request_succeeds(bundles_result)


@then(parsers.parse('the bundle catalog includes the "{category_key}" category'))
def _(bundles_result: dict[str, Any], category_key: str) -> None:
    assert_category_present(bundles_result, _BUNDLE_CATEGORY_TITLE_BY_KEY[category_key])


@then("every internet package has a non-empty bundle id")
def _(bundles_result: dict[str, Any]) -> None:
    assert_every_package_has_bundle_id(bundles_result)


@then("every internet package has a positive amount")
def _(bundles_result: dict[str, Any]) -> None:
    assert_every_package_has_positive_amount(bundles_result)


@then("every internet package's raw amount is positive and does not exceed its amount")
def _(bundles_result: dict[str, Any]) -> None:
    assert_every_package_raw_amount_within_amount(bundles_result)


@then("every internet package has a non-empty description")
def _(bundles_result: dict[str, Any]) -> None:
    assert_every_package_has_description(bundles_result)


@then("every internet package has a positive duration")
def _(bundles_result: dict[str, Any]) -> None:
    assert_every_package_has_positive_duration(bundles_result)


@then("no bundle section lists a duplicate package")
def _(bundles_result: dict[str, Any]) -> None:
    assert_no_duplicate_package_in_section(bundles_result)


@then("every package that needs approval carries an approval message")
def _(bundles_result: dict[str, Any]) -> None:
    assert_need_approval_implies_message(bundles_result)


@then('the "POPULAR" category only lists packages that also exist in another category')
def _(bundles_result: dict[str, Any]) -> None:
    assert_popular_category_is_subset_of_catalog(bundles_result)


@then('the "ALL" category is the deduplicated union of the other categories')
def _(bundles_result: dict[str, Any]) -> None:
    assert_all_category_is_union_of_others(bundles_result)


@then("every bundle type matches the requested SIM type")
def _(bundles_result: dict[str, Any], random_cell_number: RandomCellNumber) -> None:
    assert_bundle_types_match_sim_card_type(bundles_result, random_cell_number.cell_number_type)


@then("the bundle catalog request is rejected as unauthorized")
def _(bundles_result: dict[str, Any]) -> None:
    assert_status_ok("Bundle catalog request", bundles_result, expected=401)


@then("the bundle catalog request does not succeed")
def _(bundles_result: dict[str, Any]) -> None:
    assert_truthy(
        "Bundle catalog request does not return HTTP 200 for an unsupported operator id",
        bundles_result.get("status_code") != 200,
    )


@then("the bundle catalog request is handled gracefully")
def _(bundles_result: dict[str, Any]) -> None:
    assert_request_handled_gracefully(bundles_result)
