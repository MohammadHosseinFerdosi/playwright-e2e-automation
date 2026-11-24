"""Port of src/apis/uaa/users/users-send-sms.resource."""

from typing import Any

from tests.api.client import ApiClient, ApiSide
from tests.api.ms_paths import MS_UAA_PATH


def post_users_send_sms(
    client: ApiClient,
    cell_number: str,
    device_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Port of POST Users Send SMS.

    `client` must already carry Basic Auth (normally ``APP_BASIC_AUTH``) as its
    ``auth_header`` — matching the Robot keyword's default
    ``${basic_auth_param}=${APP_BASIC_AUTH}``.
    """
    if client.side is ApiSide.MICROSERVICE:
        path = f"{MS_UAA_PATH}/users/otp/sms"
    else:
        path = "/users/send-sms"

    body: dict[str, Any] = {"cellNumber": cell_number}
    if device_info:
        body["device"] = device_info

    return client.post(path, json=body)
