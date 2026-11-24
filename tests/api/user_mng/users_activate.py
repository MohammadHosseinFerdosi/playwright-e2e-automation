"""Port of src/apis/user-mng/users-activate.resource."""

from typing import Any

from tests.api.client import ApiClient


def post_users_activate(
    client: ApiClient,
    user_id: str,
    sms_token: str,
) -> dict[str, Any]:
    """Port of POST Users Activate.

    Robot always opens the session on ``${APP_SIDE}`` with
    ``${APP_BASIC_AUTH}`` (the ``api_call_side`` argument is unused for the
    session). Pass an APP-side client with ``APP_BASIC_AUTH``.
    """
    return client.post(
        "/users/activate",
        json={"smsToken": sms_token, "userId": user_id},
    )
