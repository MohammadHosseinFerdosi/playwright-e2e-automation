"""GET /bank-transfer/statements — Platform account statements."""

from __future__ import annotations

from typing import Any

from tests.api.client import ApiClient
from tests.api.debit.bank_transfer.models import parse_statement_body
from tests.api.debit.paths import MS_BANK_TRANSFER_PATH, bank_transfer_user_headers


def get_account_statements(
    client: ApiClient,
    *,
    account_id: str,
    from_ms: int,
    to_ms: int,
    user_id: str,
    forwarded_for: str,
    platform_version: str,
) -> dict[str, Any]:
    """Fetch Platform account statements for an accountId window."""
    path = client.ms_path("/bank-transfer/statements", MS_BANK_TRANSFER_PATH)
    result = client.get(
        path,
        headers=bank_transfer_user_headers(
            user_id,
            forwarded_for=forwarded_for,
            platform_version=platform_version,
            content_type=None,
        ),
        params={"accountId": account_id, "from": from_ms, "to": to_ms},
    )
    return {
        "status_code": result["status_code"],
        "body": parse_statement_body(result.get("body")),
    }
