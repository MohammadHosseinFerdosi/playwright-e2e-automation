"""POST /statements — provider bank statement pages."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient
from tests.api.debit.bank_transfer.models import parse_statement_body
from tests.api.debit.paths import MS_BANK_TRANSFER_PATH, bank_transfer_user_headers


class ProviderStatementsRequest(BaseModel):
    """Body for POST /statements."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    bank_code: str = Field(alias="bankCode")
    account_number: str = Field(alias="accountNumber")
    from_date: int = Field(alias="fromDate")
    to_date: int = Field(alias="toDate")
    page: int = 0
    size: int = 10

    def to_payload(self) -> dict[str, Any]:
        """Serialize for JSON body."""
        return self.model_dump(by_alias=True)


def post_provider_statements(
    client: ApiClient,
    request: ProviderStatementsRequest,
    *,
    user_id: str,
    forwarded_for: str,
    platform_version: str,
) -> dict[str, Any]:
    """Fetch a page of provider statements."""
    path = client.ms_path("/statements", MS_BANK_TRANSFER_PATH)
    result = client.post(
        path,
        headers=bank_transfer_user_headers(
            user_id,
            forwarded_for=forwarded_for,
            platform_version=platform_version,
        ),
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_statement_body(result.get("body")),
    }
