"""Readable assertion reports + optional Allure attachments for ``tests/``.

Every check goes through this module so a run produces one consistent
PASS/FAIL/ERROR trail in three places at once: the Allure attachment, the
``allure-results/pytest.log`` file (see the log_file config in ``pyproject.toml``'s
``[tool.pytest.ini_options]``), and the ``allure-results/summary.log`` end-of-run
report (``pytest_terminal_summary`` in ``tests/conftest.py``).

Multi-check steps — use ``AssertionReport`` directly::

    report = AssertionReport("TCI final inquiry")
    report.equals("telStatus", actual=data.tel_status, expected=1)
    report.truthy("billId present", data.bill_id)
    report.attach_json("TCI bill data", data)
    report.assert_all()

Single-check steps — use the one-shot helpers instead of a bare ``assert``::

    assert_equals("HTTP status", result["status_code"], 200)
    assert_status_ok("Create business", result)
    assert_isinstance("Response body", result["body"], TotalBalanceBody)

``FAIL`` means the check ran and the value was wrong (a product defect).
``ERROR`` means the check itself couldn't run (exception, missing
precondition, environment/connectivity problem) — keep these distinct so the
Allure "Product defects" vs "Environment / connectivity" / "Test / framework
defects" categories in ``tests/conftest.py`` stay meaningful.

Run with Allure (``--alluredir=allure-results`` is already in pytest addopts)::

    PYTHONPATH=. pytest -m tci -v
    npx --yes allure-commandline serve allure-results
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

try:
    import allure
except ImportError:  # pragma: no cover
    allure = None  # type: ignore[assignment]

logger = logging.getLogger("tests.assertions")

# Landline / mobile-ish digits — used in assertion FAIL text, not HTTP bodies.
_PHONE_RE = re.compile(r"(?<!\d)(0?\d{8,13})(?!\d)")
# Iranian IBAN shape in free text / Allure blobs.
_IBAN_RE = re.compile(r"\bIR\d{24}\b", re.IGNORECASE)
_IBAN_JSON_KEYS = frozenset(
    {
        "iban",
        "targetiban",
        "sourceiban",
        "destinationiban",
        "accountiban",
    }
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*")
_SECRET_KEYS = CHANGE_ME
    "authorization",
    "authtoken",
    "accesstoken",
    "refreshtoken",
    "idtoken",
    "token",
    "bearertoken",
    "password",
    "tcipassword",
    "clientsecret",
    "apikey",
    "xapikey",
    "secret",
    "cookie",
    "setcookie",
    "proxyauthorization",
    "jwt",
}
_QUERY_SECRET_NAMES = CHANGE_ME
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "auth",
    "password",
}


def mask_pii(text: str) -> str:
    """Mask phone-like digits and IBANs in plain text."""

    def _phone_repl(match: re.Match[str]) -> str:
        value = match.group(1)
        if len(value) < 8:
            return value
        return f"{value[:3]}***{value[-2:]}"

    masked = _PHONE_RE.sub(_phone_repl, text)
    return _IBAN_RE.sub(lambda m: f"{m.group(0)[:4]}***{m.group(0)[-4:]}", masked)


_PASSWORD_PREFIX_LEN = CHANGE_ME
_PASSWORD_SUFFIX_LEN = CHANGE_ME
_PASSWORD_MASK_FILL = "****"
_PASSWORD_MIN_PLAIN_LEN = _PASSWORD_PREFIX_LEN + _PASSWORD_SUFFIX_LEN + 1
_REDACTED = "***"


def _normalize_key(key: str) -> str:
    return str(key).lower().replace("-", "").replace("_", "")


def _password_key(key: str) -> bool:
    key_l = _normalize_key(key)
    return key_l.endswith("password") or key_l.endswith("passwd")


def _secret_key(key: str) -> bool:
    """True for credential field names (tokens, cookies, secrets — not passwords)."""
    key_l = _normalize_key(key)
    if _password_key(key):
        return False
    if key_l in _SECRET_KEYS:
        return True
    return key_l.endswith(("token", "secret"))


def _mask_password_value(value: Any) -> str:
    """Keep prefix and last character; hide short values fully."""
    if not isinstance(value, str) or len(value) < _PASSWORD_MIN_PLAIN_LEN:
        return _REDACTED
    return (
        f"{value[:_PASSWORD_PREFIX_LEN]}{_PASSWORD_MASK_FILL}"
        f"{value[-_PASSWORD_SUFFIX_LEN:]}"
    )


def mask_secrets(obj: Any) -> Any:
    """Redact credentials; leave business fields (cell number, NID) intact."""
    if isinstance(obj, str):
        return _BEARER_RE.sub(f"Bearer {_REDACTED}", obj)
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            key_l = _normalize_key(key)
            if _password_key(key):
                out[str(key)] = _mask_password_value(value)
            elif _secret_key(key):
                out[str(key)] = _REDACTED
            elif isinstance(value, str) and key_l in _IBAN_JSON_KEYS:
                out[str(key)] = mask_pii(value)
            else:
                out[str(key)] = mask_secrets(value)
        return out
    if isinstance(obj, list):
        return [mask_secrets(item) for item in obj]
    return obj


def _mask_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.query:
        return url
    pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in _QUERY_SECRET_NAMES:
            if key.lower() == "password":
                pairs.append((key, _mask_password_value(value)))
            else:
                pairs.append((key, _REDACTED))
        else:
            pairs.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(pairs)))


def _to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(by_alias=True, mode="json")
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return repr(obj)


def attach_text(name: str, body: str) -> None:
    """Attach plain text to Allure when the plugin is available."""
    text = mask_pii(body)
    if allure is None:
        return
    allure.attach(text, name=name, attachment_type=allure.attachment_type.TEXT)


def attach_json(name: str, obj: Any) -> None:
    """Attach JSON to Allure with credentials redacted."""
    payload = mask_secrets(_to_jsonable(obj))
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if allure is None:
        return
    allure.attach(text, name=name, attachment_type=allure.attachment_type.JSON)


def attach_http_exchange(
    *,
    method: str,
    url: str,
    request_headers: dict[str, str],
    request_body: Any,
    status_code: int,
    response_headers: dict[str, str],
    response_body: Any,
) -> None:
    """Attach request and response as two Allure JSON files on the current step."""
    path = urlparse(url).path or url
    attach_json(
        f"Request {method} {path}",
        {
            "method": method,
            "url": _mask_url(url),
            "headers": request_headers,
            "body": request_body,
        },
    )
    attach_json(
        f"Response {method} {path} -> {status_code}",
        {
            "status_code": status_code,
            "headers": response_headers,
            "body": response_body,
        },
    )


class AssertionReport:
    """Collect labeled checks, attach a summary, then fail with a clear block."""

    def __init__(self, title: str) -> None:
        self.title = title
        self._lines: list[str] = []
        self._failures: list[str] = []
        self._errored = False

    def equals(self, label: str, *, actual: Any, expected: Any) -> AssertionReport:
        """Record a PASS/FAIL equality check and return ``self`` for chaining."""
        ok = actual == expected
        line = f"[{'PASS' if ok else 'FAIL'}] {label}: expected={expected!r} actual={actual!r}"
        self._lines.append(line)
        if not ok:
            self._failures.append(line)
        return self

    def truthy(self, label: str, actual: Any) -> AssertionReport:
        """Record a PASS/FAIL truthiness check and return ``self`` for chaining."""
        ok = bool(actual)
        line = f"[{'PASS' if ok else 'FAIL'}] {label}: actual={actual!r}"
        self._lines.append(line)
        if not ok:
            self._failures.append(line)
        return self

    def check(self, label: str, passed: bool, *, detail: str = "") -> AssertionReport:
        """Record a PASS/FAIL boolean check and return ``self`` for chaining."""
        suffix = f" ({detail})" if detail else ""
        line = f"[{'PASS' if passed else 'FAIL'}] {label}{suffix}"
        self._lines.append(line)
        if not passed:
            self._failures.append(line)
        return self

    def note(self, message: str) -> AssertionReport:
        """Append an INFO line (does not fail) and return ``self`` for chaining."""
        self._lines.append(f"[INFO] {message}")
        return self

    def error(self, label: str, exc: BaseException | str) -> AssertionReport:
        """Record an ERROR — the check itself could not run.

        Opposite of ``FAIL``, which means the check ran and the value was wrong.
        Keeping these distinct lets Allure separate product defects from
        environment / connectivity issues (``tests/conftest.py``).
        """
        line = f"[ERROR] {label}: {exc}"
        self._lines.append(line)
        self._failures.append(line)
        self._errored = True
        return self

    def attach_json(self, name: str, obj: Any) -> AssertionReport:
        """Attach JSON to Allure and return ``self`` for chaining."""
        attach_json(name, obj)
        return self

    def summary_text(self) -> str:
        """Return the PII-masked title + checklist as plain text."""
        return mask_pii(self.title + "\n" + "\n".join(self._lines))

    def assert_all(self) -> None:
        """Attach the summary and raise ``AssertionError`` if any check failed."""
        summary = self.summary_text()
        attach_text(f"Assertions — {self.title}", summary)
        if self._failures:
            level = "ERROR" if self._errored else "FAIL"
            logger.error("[%s] %s\n%s", level, self.title, "\n".join(self._failures))
            raise AssertionError(
                mask_pii(
                    f"\n{self.title}\n"
                    + "\n".join(self._failures)
                    + "\n\nFull checklist:\n"
                    + "\n".join(self._lines)
                )
            )
        logger.info("[PASS] %s (%d checks)", self.title, len(self._lines))


def attach_api_result(name: str, result: dict[str, Any]) -> None:
    """Attach ``{status_code, body}`` envelope (tokens redacted)."""
    body = result.get("body")
    attach_json(
        name,
        {
            "status_code": result.get("status_code"),
            "body": _to_jsonable(body),
        },
    )


# --- One-shot helpers -------------------------------------------------------
#
# For steps with a single check, wrap it here instead of a bare `assert` —
# same PASS/FAIL logging + Allure attachment + PII masking as AssertionReport,
# without the boilerplate of building one by hand. Reach for AssertionReport
# directly when a step needs more than one related check.


def assert_equals(label: str, actual: Any, expected: Any) -> None:
    """One-shot equality check. Replaces ``assert actual == expected, f"..."``."""
    AssertionReport(label).equals(label, actual=actual, expected=expected).assert_all()


def assert_truthy(label: str, actual: Any) -> None:
    """One-shot truthiness check. Replaces ``assert actual, f"..."``."""
    AssertionReport(label).truthy(label, actual).assert_all()


def assert_isinstance(label: str, obj: Any, expected_type: type) -> None:
    """One-shot type check after a typed API call.

    Replaces ``assert isinstance(body, SomeModel)``.
    """
    ok = isinstance(obj, expected_type)
    detail = f"expected {expected_type.__name__}, got {type(obj).__name__}"
    AssertionReport(label).check(label, ok, detail=detail).assert_all()


def assert_status_ok(label: str, result: dict[str, Any], expected: int = 200) -> None:
    """One-shot HTTP status check for a ``{status_code, body}`` envelope.

    Attaches the response body either way so a failure is
    debuggable without re-running. Tokens in the JSON are redacted.
    """
    report = AssertionReport(label)
    report.equals(f"{label} — HTTP status", actual=result.get("status_code"), expected=expected)
    report.attach_json(f"{label} — response", result)
    report.assert_all()
