"""Step definitions for tests/bdd/features/bill/*.feature (validation / init).

Shared identity/config/rejection steps live in ``conftest.py`` (pytest-bdd reuse).
"""

from __future__ import annotations

from typing import Any

from pytest_bdd import parsers, scenarios, when

from tests.api.client import ApiClient
from tests.services.bill_ids import BillIdService
from tests.services.bill_inquiry_cases import run_init_case, run_inquiry_case

scenarios("../features/bill/bills_validation.feature")
scenarios("../features/bill/bills_config.feature")


@when(
    parsers.re(r"^the customer inquires a bill with (?P<bill_case>[A-Za-z0-9 -]+)$"),
    target_fixture="bill_inquiry_result",
)
def _(
    bill_case: str,
    bill_user_id: str,
    microservice_client: ApiClient,
    bill_id_service: BillIdService,
) -> dict[str, Any]:
    return run_inquiry_case(bill_case, microservice_client, bill_user_id, bill_id_service)


@when(
    parsers.re(r"^the customer starts bill payment with (?P<init_case>[A-Za-z0-9 -]+)$"),
    target_fixture="bill_init_result",
)
def _(
    init_case: str,
    bill_user_id: str,
    microservice_client: ApiClient,
) -> dict[str, Any]:
    return run_init_case(init_case, microservice_client, bill_user_id)
