"""Builders for Platform landline validate + TCI provider inquiry actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tests.api.bill_mng.bill_types import BILL_TYPE_TELEPHONE, BILL_TYPE_WATER
from tests.api.bill_mng.bills.inquiry_models import BillInquiryByInquiryIdRequest
from tests.api.bill_mng.bills.validate import post_bills_validate
from tests.api.client import ApiClient
from tests.api.tci.client import TciClient
from tests.services.telephone_pool import TelephoneCase

_FALLBACK_TEL_FOR_BAD_CREDS = "2122137948"


def validate_pooled_landline(
    client: ApiClient,
    user_id: str,
    telephone_case: TelephoneCase,
) -> dict[str, Any]:
    """POST landline validate using the pool case inquiry id."""
    request = BillInquiryByInquiryIdRequest.model_validate(
        {
            "payMethod": 3,
            "type": BILL_TYPE_TELEPHONE,
            "inquiryId": telephone_case.require_inquiry_id(),
        }
    )
    payload = request.to_payload()
    return post_bills_validate(
        client,
        user_id,
        pay_method=payload.get("payMethod"),
        bill_type=payload.get("type"),
        inquiry_id=payload.get("inquiryId"),
    )


def _validate_missing_type(client: ApiClient, user_id: str) -> dict[str, Any]:
    return post_bills_validate(
        client,
        user_id,
        pay_method=3,
        inquiry_id="02122137948",
    )


def _validate_empty_inquiry_id(client: ApiClient, user_id: str) -> dict[str, Any]:
    return post_bills_validate(
        client,
        user_id,
        pay_method=3,
        bill_type=BILL_TYPE_TELEPHONE,
        inquiry_id="",
    )


def _validate_short_inquiry_id(client: ApiClient, user_id: str) -> dict[str, Any]:
    return post_bills_validate(
        client,
        user_id,
        pay_method=3,
        bill_type=BILL_TYPE_TELEPHONE,
        inquiry_id="02112",
    )


def _validate_wrong_type_water(client: ApiClient, user_id: str) -> dict[str, Any]:
    return post_bills_validate(
        client,
        user_id,
        pay_method=3,
        bill_type=BILL_TYPE_WATER,
        inquiry_id="02122137948",
    )


_VALIDATE_CASES: dict[str, Callable[[ApiClient, str], dict[str, Any]]] = {
    "missing type": _validate_missing_type,
    "empty inquiry id": _validate_empty_inquiry_id,
    "short inquiry id": _validate_short_inquiry_id,
    "wrong type water": _validate_wrong_type_water,
}

LANDLINE_VALIDATE_CASE_STEP = (
    r"^the customer validates a landline with (?P<inquiry_case>[A-Za-z0-9 -]+)$"
)
TCI_REQUEST_STEP = r"^the operator requests a TCI (?P<mode>[A-Za-z0-9 -]+)$"
TCI_TEL_STATUS_STEP = r"^the TCI inquiry reports tel status (?P<tel_status>-?\d+)$"


def known_landline_validate_cases() -> list[str]:
    """Registered Outline inquiry-case keys, for the regex unit test."""
    return sorted(_VALIDATE_CASES)


def known_tci_inquiry_terms() -> list[str]:
    """Registered TCI term keys, for the regex unit test."""
    return sorted(_TCI_TERM_HANDLERS)


def validate_landline_case(
    client: ApiClient,
    user_id: str,
    inquiry_case: str,
) -> dict[str, Any]:
    """Dispatch Outline ``inquiry case`` keys to landline validate payloads."""
    key = inquiry_case.strip().lower()
    builder = _VALIDATE_CASES.get(key)
    if builder is None:
        raise KeyError(
            f"No landline validate case for {inquiry_case!r}; "
            f"known cases: {known_landline_validate_cases()}"
        )
    return builder(client, user_id)


_TCI_TERM_HANDLERS: dict[str, Callable[[TciClient, str], dict[str, Any]]] = {
    "final": lambda client, tel: client.inquire_final(tel),
    "mid": lambda client, tel: client.inquire_mid(tel),
}


def inquire_tci_term(
    client: TciClient,
    telephone_case: TelephoneCase,
    term: str,
) -> dict[str, Any]:
    """Dispatch Outline ``term`` (final/mid) against the pool tel number."""
    tel = telephone_case.require_tel_number()
    handler = _TCI_TERM_HANDLERS.get(term.strip().lower())
    if handler is None:
        raise KeyError(f"No TCI term for {term!r}; known terms: {known_tci_inquiry_terms()}")
    return handler(client, tel)


def inquire_tci_final_invalid_credentials(
    client: TciClient,
    telephone_case: TelephoneCase,
) -> dict[str, Any]:
    """Final-term TCI inquiry with a deliberately wrong password."""
    tel = telephone_case.tel_number or _FALLBACK_TEL_FOR_BAD_CREDS
    return client.inquire_final_with_password(tel, password="WRONG_PASSWORD")


def inquire_tci_final_leading_zero(
    client: TciClient,
    telephone_case: TelephoneCase,
) -> dict[str, Any]:
    """Final-term TCI inquiry forcing a leading-zero tel number."""
    tel = telephone_case.require_tel_number()
    padded = tel if tel.startswith("0") else f"0{tel}"
    return client.inquire_final(padded)


_TCI_REQUESTS: dict[str, Callable[[TciClient, TelephoneCase], dict[str, Any]]] = {
    "mid inquiry for the pooled landline": lambda client, case: inquire_tci_term(
        client, case, "mid"
    ),
    "final inquiry for the pooled landline": lambda client, case: inquire_tci_term(
        client, case, "final"
    ),
    "final inquiry with invalid credentials": inquire_tci_final_invalid_credentials,
    "final inquiry with a leading zero": inquire_tci_final_leading_zero,
}


def known_tci_request_modes() -> list[str]:
    """Registered TCI When tails, for the regex unit test."""
    return sorted(_TCI_REQUESTS)


def request_tci_inquiry(
    client: TciClient,
    telephone_case: TelephoneCase,
    mode: str,
) -> dict[str, Any]:
    """Dispatch one TCI When from the captured Gherkin tail.

    Args:
        client: Authenticated TCI client (wrong-password path still uses it).
        telephone_case: Pooled landline.
        mode: Captured phrase after ``TCI``.

    Raises:
        KeyError: Unknown mode — lists registered tails.
    """
    handler = _TCI_REQUESTS.get(mode.strip())
    if handler is None:
        raise KeyError(f"No TCI request for {mode!r}; known modes: {known_tci_request_modes()}")
    return handler(client, telephone_case)
