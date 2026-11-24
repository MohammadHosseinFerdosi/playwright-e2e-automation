#!/usr/bin/env python3
"""Local HTTP helper so Postman can drive Zephyr sync via headers (no body).

Start (repo root):
  # prefer secrets/jira_atm.env (see secrets/jira_atm.example.env)
  # or: export JIRA_TOKEN=... JIRA_ATM=https://jira.demo-platform.net/rest/atm/1.0
  PYTHONPATH=. python scripts/zephyr_sync_server.py

Then in Postman:
  POST http://127.0.0.1:8765/zephyr/sync
  Headers only — see docs/zephyr/Zephyr-Scale-Complete-Guide.pdf (Postman flow section)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = ROOT / "scripts" / "zephyr_sync.py"
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from jira_local_env import load_jira_local_env  # noqa: E402

DEFAULT_HOST = os.environ.get("ZEPHYR_SYNC_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("ZEPHYR_SYNC_PORT", "8765"))

_SUMMARY = re.compile(
    r"All done\. Created (?P<created>\d+), updated (?P<updated>\d+), "
    r"skipped unchanged (?P<skipped>\d+)\.",
)
_CREATED_KEY = re.compile(r"created (ALPHA-T\d+)", re.IGNORECASE)
_UPDATED_KEY = re.compile(r"updated (ALPHA-T\d+)", re.IGNORECASE)
_SKIPPED_KEY = re.compile(r"SKIP: (ALPHA-T\d+)", re.IGNORECASE)


def _header(headers: dict[str, str], *names: str) -> str | None:
    lower = {k.lower(): v for k, v in headers.items()}
    for name in names:
        value = lower.get(name.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _append_path_flags(cmd: list[str], headers: dict[str, str]) -> None:
    feature = _header(headers, "X-Feature")
    features = _header(headers, "X-Features")
    if not feature and not features:
        raise ValueError("Pass X-Feature and/or X-Features")
    if feature:
        cmd.extend(["--feature", feature])
    if features:
        cmd.extend(["--features", features])


def _append_optional_flags(cmd: list[str], headers: dict[str, str]) -> None:
    folder = _header(headers, "X-Zephyr-Folder", "X-Folder")
    key = _header(headers, "X-Key", "X-Zephyr-Key")
    branch = _header(headers, "X-Git-Branch", "X-Branch")
    if folder:
        cmd.extend(["--folder", folder])
    if _truthy(_header(headers, "X-Dry-Run")):
        cmd.append("--dry-run")
    if _truthy(_header(headers, "X-Force")):
        cmd.append("--force")
    if key:
        cmd.extend(["--key", key])
    if branch:
        # Zephyr has no native "branch" field — store as a label.
        safe = branch.replace(" ", "_")
        cmd.extend(["--label", f"branch:{safe}"])


def _append_mode_flags(cmd: list[str], mode: str) -> None:
    if mode == "create":
        cmd.append("--create")
    elif mode == "update":
        cmd.append("--update")
    else:
        cmd.extend(["--create", "--update"])


def _build_cli_from_headers(headers: dict[str, str]) -> list[str]:
    mode = (_header(headers, "X-Mode") or "create").lower()
    if mode not in {"create", "update", "sync"}:
        raise ValueError("X-Mode must be create, update, or sync")

    cmd = [sys.executable, str(SYNC_SCRIPT)]
    _append_path_flags(cmd, headers)
    _append_optional_flags(cmd, headers)
    _append_mode_flags(cmd, mode)
    return cmd


def _run_sync(cmd: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    summary = _SUMMARY.search(stdout)
    payload = {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "command": cmd[2:],  # drop python + script path for readability
        "created": int(summary.group("created")) if summary else None,
        "updated": int(summary.group("updated")) if summary else None,
        "skipped_unchanged": int(summary.group("skipped")) if summary else None,
        "created_keys": _CREATED_KEY.findall(stdout),
        "updated_keys": _UPDATED_KEY.findall(stdout),
        "skipped_keys": _SKIPPED_KEY.findall(stdout),
        "stdout": stdout,
        "stderr": stderr,
    }
    return payload


class Handler(BaseHTTPRequestHandler):
    """HTTP handler that maps header-driven POSTs onto ``zephyr_sync.py``."""

    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002  # stdlib override name
        """Write access logs to stderr (stdlib override)."""
        # Percent-formatting matches BaseHTTPRequestHandler's printf-style `format`.
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))  # noqa: UP031

    def _send(self, status: int, body: dict[str, Any]) -> None:
        """Serialize ``body`` as JSON with CORS headers."""
        raw = json.dumps(body, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type, X-Mode, X-Feature, X-Features, "
            "X-Zephyr-Folder, X-Folder, X-Key, X-Zephyr-Key, X-Git-Branch, "
            "X-Branch, X-Dry-Run, X-Force",
        )
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:  # noqa: N802
        """Answer CORS preflight."""
        self._send(204, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        """Serve health / not-found JSON."""
        path = urlparse(self.path).path
        if path in {"/", "/health"}:
            self._send(
                200,
                {
                    "ok": True,
                    "service": "zephyr-sync-server",
                    "repo_root": str(ROOT),
                    "sync_endpoint": "POST /zephyr/sync",
                    "docs": "docs/zephyr/Zephyr-Scale-Complete-Guide.pdf",
                },
            )
            return
        self._send(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        """Run Zephyr sync from request headers (body ignored)."""
        path = urlparse(self.path).path
        if path != "/zephyr/sync":
            self._send(404, {"ok": False, "error": "Use POST /zephyr/sync"})
            return

        # Drain body (we ignore it on purpose — config is headers-only)
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)

        headers = {k: v for k, v in self.headers.items()}
        try:
            cmd = _build_cli_from_headers(headers)
        except ValueError as exc:
            self._send(400, {"ok": False, "error": str(exc)})
            return

        if not (os.environ.get("JIRA_TOKEN") or "").strip():
            self._send(
                400,
                {
                    "ok": False,
                    "error": "Server shell missing JIRA_TOKEN "
                    "(export it before starting zephyr_sync_server.py)",
                },
            )
            return
        if not (os.environ.get("JIRA_ATM") or "").strip():
            self._send(
                400,
                {
                    "ok": False,
                    "error": "Server shell missing JIRA_ATM "
                    "(export https://jira.demo-platform.net/rest/atm/1.0)",
                },
            )
            return

        result = _run_sync(cmd)
        self._send(200 if result["ok"] else 500, result)


def main() -> int:
    """Start the local Zephyr sync HTTP helper."""
    loaded = load_jira_local_env(start=ROOT)
    server = ThreadingHTTPServer((DEFAULT_HOST, DEFAULT_PORT), Handler)
    print(
        f"Zephyr sync server on http://{DEFAULT_HOST}:{DEFAULT_PORT}\n"
        f"  POST /zephyr/sync  (headers only)\n"
        f"  GET  /health\n"
        f"Repo: {ROOT}\n" + (f"  Env file: {loaded}\n" if loaded else "") + "Stop with Ctrl+C",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
