"""POST bank-transfer/transfer.

Executes a previously routed transfer by tracking code.
Essential request field: trackingCode.
Response: HTTP status plus body with result.title (e.g. TRANSACTION_NOT_FOUND).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tests.api.client import ApiClient
from tests.api.debit.bank_transfer.models import parse_transfer_body
from tests.api.debit.paths import MS_BANK_TRANSFER_PATH, bank_transfer_user_headers


class TransferExecuteRequest(BaseModel):
    """POST /bank-transfer/transfer body."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tracking_code: str = Field(alias="trackingCode")

    def to_payload(self) -> dict[str, Any]:
        """Serialize for the execute JSON body."""
        return self.model_dump(by_alias=True, exclude_none=True)


def post_bank_transfer_execute(
    client: ApiClient,
    request: TransferExecuteRequest,
    *,
    user_id: str,
    forwarded_for: str,
    platform_version: str,
) -> dict[str, Any]:
    """Execute a routed bank transfer."""
    path = client.ms_path("/bank-transfer/transfer", MS_BANK_TRANSFER_PATH)
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
        "body": parse_transfer_body(result.get("body")),
    }
