"""Port of src/apis/purchase-mng/post-purchases-pay-dpg.resource."""

from typing import Any

from tests.api.client import ApiClient
from tests.api.ms_paths import MS_PURCHASE_PATH


def post_purchases_pay_dpg(
    client: ApiClient,
    destination_type: str,
    ticket: str,
    source_type: int,
    value: str,
    expire_date: str,
    prefix: str,
    postfix: str,
    encrypted_pin_dto: str,
    cert_file: str,
    agent: str,
    platform_version: str = "",
    x_forwarded_for: str = "",
) -> dict[str, Any]:
    """Port of POST Purchase Pay DPG."""
    path = client.ms_path("/purchases/pay/dpg", MS_PURCHASE_PATH)
    headers: dict[str, str] = {
        "ticket": ticket,
        "Agent": agent,
    }
    if platform_version:
        headers["Platform-Version"] = platform_version
    if x_forwarded_for:
        headers["X-Forwarded-For"] = x_forwarded_for
    body = {
        "type": destination_type,
        "ticket": ticket,
        "source": {
            "value": value,
            "type": source_type,
            "expireDate": expire_date,
            "prefix": prefix,
            "postfix": postfix,
        },
        "encryptedPinDto": encrypted_pin_dto,
        "certFile": cert_file,
    }
    return client.post(path, headers=headers, json=body)
