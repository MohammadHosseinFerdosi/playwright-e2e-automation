"""Port of src/apis/tgs/post-tickets-business.resource."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_TGS_PATH


class TicketBusinessBody(BaseModel):
    """Success body for POST ``/tickets/business``."""

    model_config = ConfigDict(extra="ignore")

    ticket: str


def post_tickets_business(
    client: ApiClient,
    cell_number: str,
    amount: int,
    callback_url: str,
    provider_id: str,
    ticket_type: int,
    agent: str,
    platform_version: str,
    user_id: str = "",
    additional_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Port of POST Tickets Business."""
    path = client.ms_path("/tickets/business", MS_TGS_PATH)
    headers = {
        "Agent": agent,
        "Platform-Version": platform_version,
        "User-Id": user_id,
    }
    body = {
        "cellNumber": cell_number,
        "amount": amount,
        "callbackUrl": callback_url,
        "providerId": provider_id,
        "additionalInfo": additional_info or {},
    }
    result = client.post(
        path,
        headers=headers,
        params={"type": ticket_type},
        json=body,
    )
    response_body = result.get("body")
    if (
        result["status_code"] == 200
        and isinstance(response_body, dict)
        and response_body.get("ticket")
    ):
        return {
            "status_code": result["status_code"],
            "body": TicketBusinessBody.model_validate(response_body),
        }
    return result
