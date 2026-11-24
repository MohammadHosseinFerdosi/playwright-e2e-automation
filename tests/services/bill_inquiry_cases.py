"""Payload catalog for Platform bill inquiry / init Scenario Outline cases."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tests.api.bill_mng.bills.bills_init import post_bills_init
from tests.api.bill_mng.bills.inquiry import get_bills_inquiry_by_cell, post_bills_inquiry
from tests.api.client import ApiClient
from tests.services.bill_ids import BillIdService

# Guidance-book fixtures (docs/bill-mng-sdet) — Platform-valid or known-invalid pairs.
TYPE_MISMATCH_PAIR = ("9635001104126", "109572658")
AMOUNT_TOO_LOW_PAIR = ("2664034900143", "1099157")


def _inquiry_short_identifiers(
    client: ApiClient, user_id: str, _bill_ids: BillIdService
) -> dict[str, Any]:
    return post_bills_inquiry(client, user_id, bill_id="12345", pay_id="12345")


def _inquiry_long_identifiers(
    client: ApiClient, user_id: str, _bill_ids: BillIdService
) -> dict[str, Any]:
    return post_bills_inquiry(client, user_id, bill_id="12345678901234", pay_id="12345678901234")


def _inquiry_empty_pay_id(
    client: ApiClient, user_id: str, _bill_ids: BillIdService
) -> dict[str, Any]:
    return post_bills_inquiry(client, user_id, bill_id="2664034900143", pay_id="")


def _inquiry_broken_checksum(
    client: ApiClient, user_id: str, bill_ids: BillIdService
) -> dict[str, Any]:
    bill_id, pay_id = bill_ids.broken_checksum_pair()
    return post_bills_inquiry(client, user_id, bill_id=bill_id, pay_id=pay_id)


def _inquiry_type_mismatch(
    client: ApiClient, user_id: str, _bill_ids: BillIdService
) -> dict[str, Any]:
    bill_id, pay_id = TYPE_MISMATCH_PAIR
    return post_bills_inquiry(client, user_id, bill_id=bill_id, pay_id=pay_id)


def _inquiry_amount_too_low(
    client: ApiClient, user_id: str, _bill_ids: BillIdService
) -> dict[str, Any]:
    bill_id, pay_id = AMOUNT_TOO_LOW_PAIR
    return post_bills_inquiry(client, user_id, bill_id=bill_id, pay_id=pay_id)


def _inquiry_id_without_type(
    client: ApiClient, user_id: str, _bill_ids: BillIdService
) -> dict[str, Any]:
    return post_bills_inquiry(
        client,
        user_id,
        pay_method=3,
        inquiry_id="2029334804610",
    )


def _inquiry_invalid_cell(
    client: ApiClient, user_id: str, _bill_ids: BillIdService
) -> dict[str, Any]:
    return get_bills_inquiry_by_cell(client, user_id, "0917717147", operator=1)


_INQUIRY_CASES: dict[str, Callable[[ApiClient, str, BillIdService], dict[str, Any]]] = {
    "short identifiers": _inquiry_short_identifiers,
    "long identifiers": _inquiry_long_identifiers,
    "empty pay id": _inquiry_empty_pay_id,
    "broken checksum": _inquiry_broken_checksum,
    "type mismatch": _inquiry_type_mismatch,
    "amount too low": _inquiry_amount_too_low,
    "inquiry id without type": _inquiry_id_without_type,
    "invalid cell number": _inquiry_invalid_cell,
}

_INIT_PAYLOADS: dict[str, tuple[str, str]] = {
    "empty pay id": ("700880221142", ""),
    "amount too low": AMOUNT_TOO_LOW_PAIR,
}

BILL_INQUIRY_CASE_STEP = r"^the customer inquires a bill with (?P<bill_case>[A-Za-z0-9 -]+)$"
BILL_INIT_CASE_STEP = r"^the customer starts bill payment with (?P<init_case>[A-Za-z0-9 -]+)$"


def known_bill_inquiry_cases() -> list[str]:
    """Registered Outline bill-case keys, for the regex unit test."""
    return sorted(_INQUIRY_CASES)


def known_bill_init_cases() -> list[str]:
    """Registered Outline init-case keys, for the regex unit test."""
    return sorted(_INIT_PAYLOADS)


def run_inquiry_case(
    bill_case: str,
    client: ApiClient,
    user_id: str,
    bill_ids: BillIdService,
) -> dict[str, Any]:
    """Dispatch Outline ``bill case`` keys to inquiry / cell-inquiry calls."""
    key = bill_case.strip().lower()
    builder = _INQUIRY_CASES.get(key)
    if builder is None:
        raise KeyError(
            f"No bill inquiry case for {bill_case!r}; known cases: {known_bill_inquiry_cases()}"
        )
    return builder(client, user_id, bill_ids)


def run_init_case(
    init_case: str,
    client: ApiClient,
    user_id: str,
) -> dict[str, Any]:
    """Dispatch Outline ``init case`` keys to bill payment init."""
    key = init_case.strip().lower()
    pair = _INIT_PAYLOADS.get(key)
    if pair is None:
        raise KeyError(
            f"No bill init case for {init_case!r}; known cases: {known_bill_init_cases()}"
        )
    bill_id, pay_id = pair
    return post_bills_init(client, user_id, bill_id=bill_id, pay_id=pay_id)
