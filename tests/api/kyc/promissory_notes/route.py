"""POST promissory-notes/route."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_PROMISSORY_NOTE_PATH, promissory_requester_headers
from tests.api.kyc.promissory_notes.models import RouteRequest, parse_route_body


def post_promissory_notes_route(
    client: ApiClient,
    requester_app_name: str,
    tracking_code: str,
    recipient_code: int,
) -> dict[str, Any]:
    """Select a provider for a tracking code.

    Path: ``{MS_PROMISSORY_NOTE_PATH}/promissory-notes/route``.
    Required header: ``Requester-App-Name``.
    Required body: ``trackingCode``, ``recipientCode``.
    """
    path = client.ms_path("/promissory-notes/route", MS_PROMISSORY_NOTE_PATH)
    request = RouteRequest.model_validate(
        {"trackingCode": tracking_code, "recipientCode": recipient_code}
    )
    result = client.post(
        path,
        headers=promissory_requester_headers(requester_app_name),
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_route_body(result.get("body")),
    }
