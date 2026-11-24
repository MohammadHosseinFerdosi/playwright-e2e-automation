"""Shared "raise if the API call failed" helper for ``tests/services/``.

Step files use ``tests.services.assert_report`` (``AssertionReport`` / the
``assert_*`` helpers) for readable pass/fail checks inside a scenario — those
are business assertions and belong in the Allure report.

Service-layer orchestration code (factories, ``WalletInitializer``, auth
helpers, ...) is different: a failed call there is a setup/teardown problem,
not something under test, so it should raise immediately with enough context
to debug — not collect into a scenario report. Use ``ensure_ok`` /
``ensure_status`` instead of hand-rolling ``if result["status_code"] != 200:
raise RuntimeError(...)`` at every call site.
"""

from __future__ import annotations

from typing import Any


def ensure_status(result: dict[str, Any], expected: int, *, context: str) -> dict[str, Any]:
    """Raise ``RuntimeError`` when ``result["status_code"] != expected``.

    Returns ``result`` unchanged so it can be used inline::

        body = ensure_status(post_wallets_users(...), 200, context="create wallet")["body"]
    """
    if result.get("status_code") != expected:
        raise RuntimeError(
            f"{context} failed: expected status_code={expected}, "
            f"got {result.get('status_code')}; body={result.get('body')}"
        )
    return result


def ensure_ok(result: dict[str, Any], *, context: str) -> dict[str, Any]:
    """``ensure_status(result, 200, context=...)`` shorthand — the common case."""
    return ensure_status(result, 200, context=context)
