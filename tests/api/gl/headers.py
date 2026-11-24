"""Identity headers for GL's admin financial-transactions endpoint.

Same gateway/MS trust model as bill-mng (see ``tests/api/bill_mng/headers.py``):
no JWT is validated, so the caller must supply a ``user-id`` plus a live
session ``Cookie``. Port of the header dict built inline in
``src/apis/gl/incoming-transactions/post-financial-transactions-manual.resource``.
"""

from __future__ import annotations

# GL's manual-transaction endpoint accepts any non-empty user id — this mirrors
# the literal Robot fixture value (src/data/gl/gl.yaml: USER_ID: test-user), not
# a real identity, so it is a plain constant rather than a secret.
DEFAULT_GL_ADMIN_USER_ID = "test-user"


def financial_transaction_headers(*, user_id: str, cookie: str) -> dict[str, str]:
    """Build the headers required by POST /api/gl/admin/financial/transactions/manual."""
    return {
        "user-id": user_id,
        "Cookie": cookie,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
