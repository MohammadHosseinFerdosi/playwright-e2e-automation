"""POST promissory-notes/payments/init."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH
from tests.api.kyc.promissory_notes.models import (
    PaymentsInitRequest,
    parse_result_or_raw,
)


def post_promissory_notes_payments_init(
    client: ApiClient,
    user_id: str,
    amount: int,
    tracking_code: str,
    callback_url: str,
    client_id: str,
    agent: str,
    platform_version: str,
    x_forwarded_for: str,
) -> dict[str, Any]:
    """Start stamp-duty payment for a note.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/promissory-notes/payments/init``.
    Required headers: ``Client-Id``, ``Agent``, ``Platform-Version``,
    ``X-Forwarded-For``, ``User-Id``.
    Required body: ``userId``, ``amount``, ``promissoryNoteTrackingCode``,
    ``callbackUrl``.
    """
    path = client.ms_path("/promissory-notes/payments/init", MS_PROMISSORY_NOTE_PATH)
    request = PaymentsInitRequest.model_validate(
        {
            "userId": user_id,
            "amount": amount,
            "promissoryNoteTrackingCode": tracking_code,
            "callbackUrl": callback_url,
        }
    )
    headers = {
        "Client-Id": client_id,
        "Agent": agent,
        "Platform-Version": platform_version,
        "X-Forwarded-For": x_forwarded_for,
        "User-Id": user_id,
    }
    result = client.post(path, headers=headers, json=request.to_payload())
    return {
        "status_code": result["status_code"],
        "body": parse_result_or_raw(result.get("body")),
    }
