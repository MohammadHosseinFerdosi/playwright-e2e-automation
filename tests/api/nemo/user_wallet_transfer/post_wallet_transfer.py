"""Port of src/apis/nemo/user-wallet-transfer/post-wallet-transfer.resource."""

from __future__ import annotations

import secrets
import string
from typing import Any

from pydantic import BaseModel, ConfigDict

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_NEMO_PATH


class TransferTicketBody(BaseModel):
    """Success body for POST /wallets/transfer (ticket)."""

    model_config = ConfigDict(extra="ignore")

    ticket: str


def post_wallets_transfer(
    client: ApiClient,
    user_id: str,
    agent: str,
    amount: int | str,
    dest_cell_number: str,
    message: str | None = None,
) -> dict[str, Any]:
    """Port of POST Wallets Transfer — obtain a transfer ticket.

    APP side: path ``/wallets/transfer`` (gateway).
    MICROSERVICE side: ``MS_NEMO_PATH`` + ``/wallets/transfer``.
    """
    path = client.ms_path("/wallets/transfer", MS_NEMO_PATH)
    if message is None:
        alphabet = string.ascii_letters + string.digits
        message = "".join(secrets.choice(alphabet) for _ in range(20))

    headers = {
        "Agent": agent,
        "User-id": user_id,
    }
    body = {
        "amount": amount,
        "destCellNumber": dest_cell_number,
        "message": message,
    }
    result = client.post(path, headers=headers, json=body)
    response_body = result.get("body")
    if (
        result["status_code"] == 200
        and isinstance(response_body, dict)
        and response_body.get("ticket")
    ):
        return {
            "status_code": result["status_code"],
            "body": TransferTicketBody.model_validate(response_body),
        }
    return result
