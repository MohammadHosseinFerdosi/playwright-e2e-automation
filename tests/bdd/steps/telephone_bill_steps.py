"""Steps for Platform landline validate + TCI provider bill features."""

from __future__ import annotations

from typing import Any

from pytest_bdd import given, parsers, scenarios, then, when

from tests.api.client import ApiClient
from tests.api.tci.client import TciClient
from tests.services.landline_validate import (
    request_tci_inquiry,
    validate_landline_case,
    validate_pooled_landline,
)
from tests.services.landline_validate_asserts import (
    assert_bill_config_includes_active_landline,
    assert_every_landline_info_telephone_zero_fee,
    assert_landline_validate_outcome,
    assert_mid_final_share_bill_id_distinct_pay_ids,
    assert_tci_inquiry_outcome,
    assert_tci_tel_status,
)
from tests.services.telephone_pool import TelephoneBillPool, TelephoneCase

scenarios("../features/bill/tci/tci_inquiry.feature")
scenarios("../features/bill/tci/tci_provider_inquiry.feature")


@given("TCI provider credentials are available")
def _(
    telephone_bill_pool: TelephoneBillPool,
    required_tci_client: TciClient,
) -> None:
    telephone_bill_pool.require_tci()
    _ = required_tci_client


@when(
    "the customer validates the pooled landline",
    target_fixture="bill_inquiry_result",
)
def _(
    bill_user_id: str,
    microservice_client: ApiClient,
    telephone_case: TelephoneCase,
) -> dict[str, Any]:
    return validate_pooled_landline(microservice_client, bill_user_id, telephone_case)


@when(
    parsers.re(r"^the customer validates a landline with (?P<inquiry_case>[A-Za-z0-9 -]+)$"),
    target_fixture="bill_inquiry_result",
)
def _(
    inquiry_case: str,
    bill_user_id: str,
    microservice_client: ApiClient,
) -> dict[str, Any]:
    return validate_landline_case(microservice_client, bill_user_id, inquiry_case)


@when(
    parsers.re(r"^the operator requests a TCI (?P<mode>[A-Za-z0-9 -]+)$"),
    target_fixture="tci_inquiry_result",
)
def _(
    mode: str,
    telephone_case: TelephoneCase,
    required_tci_client: TciClient,
) -> dict[str, Any]:
    return request_tci_inquiry(required_tci_client, telephone_case, mode)


@then("the bill configuration includes active landline telephone")
def _(bill_config_result: dict[str, Any]) -> None:
    assert_bill_config_includes_active_landline(bill_config_result)


@then(parsers.re(r"^the landline validate (?P<outcome>[A-Za-z0-9 -]+)$"))
def _(bill_inquiry_result: dict[str, Any], outcome: str) -> None:
    assert_landline_validate_outcome(bill_inquiry_result, outcome)


@then("every landline bill info is telephone with zero fee")
def _(bill_inquiry_result: dict[str, Any]) -> None:
    assert_every_landline_info_telephone_zero_fee(bill_inquiry_result)


@then("mid and final terms share a bill id and have distinct pay ids")
def _(bill_inquiry_result: dict[str, Any]) -> None:
    assert_mid_final_share_bill_id_distinct_pay_ids(bill_inquiry_result)


@then(parsers.re(r"^the TCI inquiry reports tel status (?P<tel_status>-?\d+)$"))
def _(tci_inquiry_result: dict[str, Any], tel_status: str) -> None:
    assert_tci_tel_status(tci_inquiry_result, tel_status)


@then(parsers.re(r"^the TCI inquiry (?P<outcome>(?!reports tel status )[A-Za-z0-9 -]+)$"))
def _(tci_inquiry_result: dict[str, Any], outcome: str) -> None:
    assert_tci_inquiry_outcome(tci_inquiry_result, outcome)
