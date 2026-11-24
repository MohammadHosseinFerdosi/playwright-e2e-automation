"""POST /kyc/cell-number/inquiry — Shahkar match of cell number to national code."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.kyc.paths import MS_KYC_PATH, requester_app_headers
from tests.api.kyc.shahkar.models import (
    CellNumberInquiryRequest,
    parse_cell_number_inquiry_body,
)


def post_kyc_cell_number_inquiry(
    client: ApiClient,
    requester_app_name: str,
    request: CellNumberInquiryRequest,
) -> dict[str, Any]:
    """Inquire whether a cell number belongs to a national code."""
    path = client.ms_path("/kyc/cell-number/inquiry", MS_KYC_PATH)
    result = client.post(
        path,
        headers=requester_app_headers(requester_app_name),
        json=request.to_payload(),
    )
    return {
        "status_code": result["status_code"],
        "body": parse_cell_number_inquiry_body(result.get("body")),
    }
