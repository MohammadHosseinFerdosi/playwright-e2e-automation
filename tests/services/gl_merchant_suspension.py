"""Suspend/unsuspend session for GL merchants without a Rahkaran code.

Port of the ``Suspend Merchant`` / ``Get Id Of Merchant`` / ``Unsuspend Merchant``
keywords in ``src/steps/gl/detailed-code-mangement/merchants-without-rahkaran-codes.resource``.

Robot ran ``Unsuspend Merchant`` as a ``Suite Teardown`` (once, at the end of the
whole file). pytest has no direct equivalent of "suite teardown" scoped to one
scenario, so this uses the same note/restore *session* pattern as
``tests/services/bill_inquiry_admin.py``: a small class holds what was changed,
and ``request.addfinalizer`` registers its cleanup method to run after the
scenario finishes — pass or fail.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.api.client import ApiClient
from tests.api.gl.detailed_code_management.merchants_without_rahkaran_codes import (
    MerchantWithoutRahkaranCode,
    suspend_merchant,
)
from tests.services.api_assert import ensure_ok
from tests.services.db.mysql_client import MySQLClient

_GL_DB = "general_ledger_db"
# Robot ``Get Id Of Merchant`` filtered ``f_profile IN (26, 12)`` — keep the
# same profile ids rather than inventing a new lookup.
_BIZ_MAPPING_PROFILE_IDS = (26, 12)


def _require_business_name(merchant: MerchantWithoutRahkaranCode) -> str:
    """Narrow the model's optional ``business_name`` to a required ``str``.

    Lives here (service layer), not in a step, because
    ``.cursor/rules/step-definitions.mdc`` bans ``if``/bare ``assert`` in step
    files — this kind of validation belongs behind one function call instead.
    """
    if not merchant.business_name:
        raise RuntimeError(f"Merchant has no business name: {merchant!r}")
    return merchant.business_name


def _business_id_by_name(mysql_client: MySQLClient, business_name: str) -> int:
    """Port of the raw SQL in "Get Id Of Merchant" against GL's own ``biz_mapping`` table.

    Uses a parameterized query (``%s``) instead of the Robot version's string
    interpolation — avoids SQL-injection-shaped bugs and quoting mistakes.
    """
    profile_placeholders = ", ".join(["%s"] * len(_BIZ_MAPPING_PROFILE_IDS))
    query = (
        "SELECT id FROM biz_mapping WHERE biz_name = %s "
        f"AND f_profile IN ({profile_placeholders}) ORDER BY f_profile DESC LIMIT 1"
    )
    result = mysql_client.fetch_all(_GL_DB, query, (business_name, *_BIZ_MAPPING_PROFILE_IDS))
    if result["status_code"] != 0:
        raise RuntimeError(f"GL biz_mapping lookup failed for {business_name!r}: {result['body']}")
    rows = result["body"]
    if not rows:
        raise RuntimeError(f"No GL biz_mapping row found for merchant {business_name!r}")
    return int(rows[0]["id"])


class SuspendMerchantSession:
    """Per-scenario suspend action + always-unsuspend-on-teardown."""

    def __init__(self, microservice_client: ApiClient, mysql_client: MySQLClient) -> None:
        self._microservice_client = microservice_client
        self._mysql_client = mysql_client
        self.business_name: str | None = None
        self.business_id: int | None = None
        self.last_suspend: dict[str, Any] = {}
        self._restored = False

    def suspend(self, merchant: MerchantWithoutRahkaranCode) -> None:
        """Look up the merchant's GL id, then suspend it via the admin API."""
        business_name = _require_business_name(merchant)
        self.business_name = business_name
        self.business_id = _business_id_by_name(self._mysql_client, business_name)
        self.last_suspend = ensure_ok(
            suspend_merchant(
                self._microservice_client, business_id=self.business_id, is_suspended=True
            ),
            context=f"GL suspend merchant {business_name!r}",
        )
        self._restored = False

    @property
    def suspended_business_name(self) -> str:
        """The business name suspended this scenario (raises if none yet)."""
        if not self.business_name:
            raise RuntimeError("No merchant has been suspended yet in this scenario")
        return self.business_name

    def unsuspend_on_teardown(self) -> None:
        """Idempotent finalizer — runs even if the scenario failed mid-way.

        Guards on ``self.business_name`` so it's a no-op if ``suspend`` was
        never actually called (e.g. an earlier step failed first).
        """
        if self._restored or not self.business_name:
            return
        self._mysql_client.execute_query(
            _GL_DB,
            "UPDATE biz_mapping SET suspended = NULL WHERE biz_name = %s",
            (self.business_name,),
        )
        self._restored = True


def bind_suspend_merchant_session(
    request: pytest.FixtureRequest,
    microservice_client: ApiClient,
    mysql_client: MySQLClient,
) -> SuspendMerchantSession:
    """Create a session and register the unsuspend finalizer."""
    session = SuspendMerchantSession(microservice_client, mysql_client)
    request.addfinalizer(session.unsuspend_on_teardown)
    return session
