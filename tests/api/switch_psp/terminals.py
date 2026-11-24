"""Port of src/apis/switch-psp/post-terminal.resource."""

from typing import Any

from tests.api.client import ApiClient, ApiSide
from tests.api.ms_paths import MS_SWITCH_PSP_PATH


def post_terminals(
    client: ApiClient,
    payment_gateway: int,
    transaction_type: int,
    terminal_id: str,
    kyc_supported: Any,
    bank_code: str,
    pin_code: str,
    merchant_id: str,
    business_id: str,
    psp_code: str,
    active: Any,
) -> dict[str, Any]:
    """Port of POST Terminals — assign a PSP terminal to a business."""
    if client.side is ApiSide.MICROSERVICE:
        path = client.ms_path("/terminals", MS_SWITCH_PSP_PATH)
        pay_types: list[Any] = [
            {
                "paymentGateway": payment_gateway,
                "transactionType": transaction_type,
            }
        ]
    else:
        path = "/admin/terminals"
        pay_types = [payment_gateway]

    return client.post(
        path,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "CONSOLE",
            "Platform-Version": "2022-02-02",
        },
        json={
            "terminalId": terminal_id,
            "kycSupported": kyc_supported,
            "bankCode": bank_code,
            "pinCode": pin_code,
            "merchantId": merchant_id,
            "ownerUserId": business_id,
            "pspCode": psp_code,
            "active": active,
            "payTypes": pay_types,
        },
    )
