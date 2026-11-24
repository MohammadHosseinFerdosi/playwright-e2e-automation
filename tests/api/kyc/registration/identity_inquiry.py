"""POST /kyc/identity/registration/inquiry — Sabt-Ahval identity lookup."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_KYC_PATH, requester_app_headers
from tests.api.kyc.registration.models import (
    RegistrationInquiryRequest,
    parse_registration_inquiry_body,
)


def post_kyc_identity_registration_inquiry(
    client: ApiClient,
    requester_app_name: str,
    request: RegistrationInquiryRequest,
) -> dict[str, Any]:
    """Inquire Sabt-Ahval identity for a national code and birth date."""
    path = client.ms_path("/kyc/identity/registration/inquiry", MS_KYC_PATH)
    result = client.post(
        path,
        headers=requester_app_headers(requester_app_name),
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_registration_inquiry_body(result.get("body")),
    }
