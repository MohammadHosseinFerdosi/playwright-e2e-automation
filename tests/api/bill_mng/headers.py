"""Identity headers for bill-mng (gateway / MS trust model).

bill-mng does not validate JWT; callers must send User-Id and Platform
request-context headers (see docs/bill-mng-sdet/BILL_AUTOMATION_GUIDANCE_BOOK.md §4).
"""

from __future__ import annotations

# Primary user from bill-mng WireMock ITs — valid User-Id for MS validation calls.
BILL_IT_PRIMARY_USER_ID = "2d04d8eb-e6fa-4b12-8dae-6d15b4d1fda0"

DEFAULT_AGENT = "ANDROID"
DEFAULT_PLATFORM_VERSION = "2019-09-30"
DEFAULT_CLIENT_ID = "platform-client-id"
DEFAULT_X_FORWARDED_FOR = "192.168.1.1"


def bill_request_headers(
    user_id: str,
    *,
    agent: str = DEFAULT_AGENT,
    platform_version: str = DEFAULT_PLATFORM_VERSION,
    client_id: str = DEFAULT_CLIENT_ID,
    x_forwarded_for: str = DEFAULT_X_FORWARDED_FOR,
) -> dict[str, str]:
    """Build the header set required by inquiry / init / pay endpoints."""
    return {
        "User-Id": user_id,
        "Agent": agent,
        "Platform-Version": platform_version,
        "Client-Id": client_id,
        "X-Forwarded-For": x_forwarded_for,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
