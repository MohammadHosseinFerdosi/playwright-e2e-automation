"""Port of post-financial-transactions-manual.resource.

(src/apis/gl/incoming-transactions/)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tests.api.client import ApiClient
from tests.api.gl.headers import financial_transaction_headers
from tests.api.ms_paths import MS_GL_PATH

_CREATE_TRANSACTION_PATH = "/api/gl/admin/financial/transactions/manual"

# Robot built ``effectiveDate`` with ``Get Current Date result_format=%Y-%m-%dT%H:%M:%S+03:30``
# (Tehran offset, no DST) — reproduced with a fixed-offset tzinfo instead of the
# system clock's local timezone, so this is correct no matter where pytest runs.
_TEHRAN_OFFSET = timezone(timedelta(hours=3, minutes=30))


class TransactionRequestInfo(BaseModel):
    """The ``response.response`` object of a create-transaction reply."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    request_id: str | None = Field(default=None, alias="requestId")


class VoucherTransactionRequest(BaseModel):
    """The ``response.voucher.transactionRequest`` object."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    amount: int | None = None


class VoucherInfo(BaseModel):
    """The ``response.voucher`` object."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    transaction_request: VoucherTransactionRequest | None = Field(
        default=None, alias="transactionRequest"
    )


class CreateFinancialTransactionResult(BaseModel):
    """Parsed body of a successful manual financial-transaction create."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    response: TransactionRequestInfo | None = None
    voucher: VoucherInfo | None = None


class CreateFinancialTransactionRequest(BaseModel):
    """POST body for a manual financial transaction."""

    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(alias="requestId")
    event_code: int = Field(alias="eventCode")
    parent_event_code: int | None = Field(alias="parentEventCode")
    amount: int
    client_id: str = Field(alias="clientId")
    effective_date: str = Field(alias="effectiveDate")
    inner_json: str = Field(alias="json")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the create-transaction JSON body."""
        return self.model_dump(by_alias=True)


def create_financial_transaction(
    client: ApiClient,
    *,
    event_code: int,
    inner_json: str,
    request_id: str,
    parent_event_code: int | None,
    amount: int,
    client_id: str,
    user_id: str,
    cookie: str,
) -> dict[str, Any]:
    """POST a manual financial transaction (port of ``POST create Financial Transaction``)."""
    path = client.ms_path(_CREATE_TRANSACTION_PATH, MS_GL_PATH)
    headers = financial_transaction_headers(user_id=user_id, cookie=cookie)
    request = CreateFinancialTransactionRequest.model_validate(
        {
            "requestId": request_id,
            "eventCode": event_code,
            "parentEventCode": parent_event_code,
            "amount": amount,
            "clientId": client_id,
            "effectiveDate": datetime.now(_TEHRAN_OFFSET).strftime("%Y-%m-%dT%H:%M:%S+03:30"),
            "json": inner_json,
        }
    )
    result = client.post(path, json=request.to_payload(), headers=headers)
    return {
        "status_code": result["status_code"],
        "body": _parse_create_result(result.get("body")),
    }


def _parse_create_result(body: Any) -> Any:
    """Parse a create-transaction body; return the raw value on validation failure."""
    if not isinstance(body, dict):
        return body
    try:
        return CreateFinancialTransactionResult.model_validate(body)
    except ValidationError:
        return body
