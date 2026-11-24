#!/usr/bin/env python3
"""Pytest plugin: push Pass/Fail into a Zephyr Scale test cycle (ATM testrun).

Credentials: ``secrets/jira_atm.env`` (gitignored) or process env.

  export ZEPHYR_CYCLE_NAME="Bill TCI smoke $(date '+%Y-%m-%d %H:%M')"
  # First push, or when the user asked for a new cycle:
  export ZEPHYR_CYCLE_MODE=create
  # Later rerun, only after the user chose override:
  export ZEPHYR_CYCLE_MODE=override
  export ZEPHYR_CYCLE_KEY=ALPHA-C##

``create`` POSTs a new testrun. ``override`` PUTs results onto an existing
cycle (same key). Agents must **ask** which to use after the first cycle
exists — pytest is non-interactive. Last key is stored in
``.tmp/zephyr_last_cycle.json`` (gitignored).

Executed by / Assigned To come from the **current token** via
``GET /rest/api/2/myself`` → ``key``. Never hardcode a person.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from jira_branch import branch_issue_key  # noqa: E402
from jira_local_env import load_jira_local_env  # noqa: E402

_ZEPHYR_KEY = re.compile(r"^([A-Z][A-Z0-9]+)-T\d+$", re.IGNORECASE)
_LAST_CYCLE_PATH = _ROOT / ".tmp" / "zephyr_last_cycle.json"

# nodeid → Zephyr status
_results: dict[str, str] = {}
# nodeid → test case key
_keys: dict[str, str] = {}
# nodeid → pytest call duration in seconds
_durations: dict[str, float] = {}


def _cycle_name() -> str:
    return (os.environ.get("ZEPHYR_CYCLE_NAME") or "").strip()


def _cycle_mode() -> str:
    mode = (os.environ.get("ZEPHYR_CYCLE_MODE") or "create").strip().lower()
    return "override" if mode == "override" else "create"


def _cycle_key() -> str:
    return (os.environ.get("ZEPHYR_CYCLE_KEY") or "").strip()


def _enabled() -> bool:
    load_jira_local_env(start=_ROOT)
    if not (os.environ.get("JIRA_TOKEN") or "").strip():
        return False
    if _cycle_mode() == "override":
        return bool(_cycle_key())
    return bool(_cycle_name())


def _zephyr_key_for(item: pytest.Item) -> str | None:
    for mark in item.iter_markers(name="zephyr_key"):
        if mark.args:
            return str(mark.args[0])
    return None


def _project_from_keys(keys: list[str]) -> str:
    projects = sorted({m.group(1).upper() for key in keys if (m := _ZEPHYR_KEY.match(key))})
    if not projects:
        raise SystemExit("zephyr_result_collector: no valid PROJECT-T#### keys")
    if len(projects) > 1:
        raise SystemExit(
            "zephyr_result_collector: mixed projects in one cycle "
            f"({', '.join(projects)}); run one project at a time"
        )
    return projects[0]


def _jira_rest_base(atm: str) -> str:
    if "/rest/atm/" in atm:
        return f"{atm.split('/rest/atm/')[0]}/rest/api/2"
    return f"{atm.rsplit('/rest/', 1)[0]}/rest/api/2"


def _jira_user_key(token: str, jira_rest: str) -> str:
    """Return the Jira user key for whoever owns ``token`` (any teammate)."""
    try:
        response = httpx.get(
            f"{jira_rest.rstrip('/')}/myself",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        print(f"zephyr_result_collector: GET /myself failed: {exc}")
        return ""
    if response.status_code != 200:
        print(f"zephyr_result_collector: GET /myself HTTP {response.status_code}")
        return ""
    body = response.json() if response.content else {}
    key = str(body.get("key") or "").strip()
    display = str(body.get("displayName") or "").strip()
    if key and display:
        print(f"zephyr_result_collector: executions as {display}")
    return key


def _read_last_cycle() -> dict[str, str]:
    if not _LAST_CYCLE_PATH.is_file():
        return {}
    try:
        raw = json.loads(_LAST_CYCLE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if v is not None}


def _write_last_cycle(key: str, name: str) -> None:
    _LAST_CYCLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "key": key,
        "name": name,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _LAST_CYCLE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _result_body(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key != "testCaseKey"}


def _auth_headers(token: str, *, json_body: bool) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _execution_item(nodeid: str, test_case_key: str, user_key: str) -> dict[str, Any]:
    status = _results.get(nodeid, "Not Executed")
    item: dict[str, Any] = {
        "testCaseKey": test_case_key,
        "status": status,
        "scriptResults": [{"index": 0, "status": status}],
    }
    if user_key:
        item["executedBy"] = user_key
        item["assignedTo"] = user_key
    seconds = _durations.get(nodeid)
    if seconds is not None:
        item["executionTime"] = max(0, int(seconds * 1000))
    environment = (os.environ.get("ZEPHYR_ENVIRONMENT") or "").strip()
    if environment:
        item["environment"] = environment
    return item


def _ensure_allure_html() -> Path | None:
    report = _ROOT / "allure-report"
    if (report / "index.html").is_file():
        return report
    results = _ROOT / "allure-results"
    if not results.is_dir() or not shutil.which("allure"):
        return None
    subprocess.run(
        ["allure", "generate", str(results), "--clean", "-o", str(report)],
        check=False,
        env={**os.environ, "ALLURE_NO_ANALYTICS": "true"},
    )
    if (report / "index.html").is_file():
        return report
    return None


def _zip_folder(source: Path, dest: Path, *, skip_suffixes: tuple[str, ...] = ()) -> int:
    count = 0
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in source.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in skip_suffixes:
                continue
            archive.write(path, path.relative_to(source))
            count += 1
    return count


def _build_allure_zip(dest: Path) -> str | None:
    html = _ensure_allure_html()
    if html is not None:
        _zip_folder(html, dest)
        return "allure-report.zip"
    results = _ROOT / "allure-results"
    if not results.is_dir():
        return None
    # Skip Playwright traces (large .zip attachments); keep screenshots + JSON.
    if _zip_folder(results, dest, skip_suffixes=(".zip",)) == 0:
        return None
    return "allure-results.zip"


def _attach_cycle_zip(token: str, atm: str, cycle_key: str, zip_path: Path, filename: str) -> None:
    with zip_path.open("rb") as handle:
        response = httpx.post(
            f"{atm.rstrip('/')}/testrun/{cycle_key}/attachments",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            files={"file": (filename, handle, "application/zip")},
            timeout=120.0,
        )
    if response.status_code in (200, 201, 204):
        print(f"zephyr_result_collector: attached {filename} on {cycle_key}")
        return
    print(
        f"zephyr_result_collector: attach {filename} failed "
        f"HTTP {response.status_code}: {response.text[:300]}"
    )


def _testcase_issue_links(token: str, atm: str, case_key: str) -> list[str]:
    response = httpx.get(
        f"{atm.rstrip('/')}/testcase/{case_key}",
        headers=_auth_headers(token, json_body=False),
        timeout=30.0,
    )
    if response.status_code != 200:
        return []
    body = response.json() if response.content else {}
    raw = body.get("issueLinks") or []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if item]


def _cycle_issue_keys(token: str, atm: str, case_keys: list[str]) -> list[str]:
    keys: list[str] = []
    branch = branch_issue_key()
    if branch:
        keys.append(branch)
    for case_key in case_keys:
        keys.extend(_testcase_issue_links(token, atm, case_key))
    return list(dict.fromkeys(keys))


def _link_cycle_to_jira_issues(
    token: str,
    atm: str,
    cycle_key: str,
    name: str,
    issue_keys: list[str],
) -> None:
    if not issue_keys:
        print("zephyr_result_collector: no Jira issues to attach the cycle to")
        return
    origin = _jira_rest_base(atm).split("/rest/")[0]
    jira_rest = _jira_rest_base(atm)
    cycle_url = f"{origin}/secure/Tests.jspa#/v2/testPlayer/{cycle_key}"
    title = f"Zephyr test cycle {cycle_key} — {name}".strip(" —")
    for issue in issue_keys:
        payload = {
            "globalId": f"zephyr-testrun-{cycle_key}",
            "application": {"type": "zephyr-scale", "name": "Zephyr Scale"},
            "object": {"url": cycle_url, "title": title},
        }
        response = httpx.post(
            f"{jira_rest.rstrip('/')}/issue/{issue}/remotelink",
            headers=_auth_headers(token, json_body=True),
            json=payload,
            timeout=30.0,
        )
        if response.status_code in (200, 201):
            print(f"zephyr_result_collector: attached {cycle_key} on {issue}")
            continue
        print(
            f"zephyr_result_collector: attach {cycle_key} on {issue} failed "
            f"HTTP {response.status_code}: {response.text[:200]}"
        )


def _attach_allure_to_cycle(token: str, atm: str, cycle_key: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "allure.zip"
        filename = _build_allure_zip(zip_path)
        if not filename or not zip_path.is_file():
            print("zephyr_result_collector: no Allure artifacts to attach")
            return
        _attach_cycle_zip(token, atm, cycle_key, zip_path, filename)


def _create_cycle(
    token: str,
    atm: str,
    name: str,
    items: list[dict[str, Any]],
) -> str:
    payload: dict[str, Any] = {
        "projectKey": _project_from_keys([i["testCaseKey"] for i in items]),
        "name": name,
        "items": items,
    }
    folder = (os.environ.get("ZEPHYR_CYCLE_FOLDER") or "").strip()
    if folder:
        payload["folder"] = folder if folder.startswith("/") else f"/{folder}"
    print(f"zephyr_result_collector: CREATE cycle {name!r} with {len(items)} item(s)…")
    response = httpx.post(
        f"{atm}/testrun",
        headers=_auth_headers(token, json_body=True),
        json=payload,
        timeout=120.0,
    )
    if response.status_code not in (200, 201):
        print(
            f"zephyr_result_collector: create testrun failed "
            f"HTTP {response.status_code}: {response.text[:500]}"
        )
        return ""
    body = response.json() if response.content else {}
    return str(body.get("key") or body.get("id") or "")


def _override_cycle(
    token: str,
    atm: str,
    cycle_key: str,
    items: list[dict[str, Any]],
) -> str:
    probe = httpx.get(
        f"{atm}/testrun/{cycle_key}",
        headers=_auth_headers(token, json_body=False),
        timeout=60.0,
    )
    if probe.status_code != 200:
        print(
            f"zephyr_result_collector: override {cycle_key} failed "
            f"GET HTTP {probe.status_code}: {probe.text[:300]}"
        )
        return ""
    print(f"zephyr_result_collector: OVERRIDE {cycle_key} with {len(items)} result(s)…")
    failed = 0
    for item in items:
        case_key = str(item["testCaseKey"])
        response = httpx.put(
            f"{atm}/testrun/{cycle_key}/testcase/{case_key}/testresult",
            headers=_auth_headers(token, json_body=True),
            json=_result_body(item),
            timeout=60.0,
        )
        if response.status_code not in (200, 201):
            failed += 1
            print(
                f"zephyr_result_collector: PUT {case_key} failed "
                f"HTTP {response.status_code}: {response.text[:300]}"
            )
            continue
        print(f"  {case_key}: {item['status']}")
    if failed:
        print(f"zephyr_result_collector: override finished with {failed} failed PUT(s)")
        return ""
    return cycle_key


def pytest_configure(config: pytest.Config) -> None:
    """Announce cycle push when Zephyr result collection is enabled."""
    if not _enabled():
        return
    mode = _cycle_mode()
    if mode == "override":
        print(f"zephyr_result_collector: will OVERRIDE cycle {_cycle_key()!r}")
        return
    print(f"zephyr_result_collector: will CREATE cycle {_cycle_name()!r}")


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Record Zephyr test-case keys for tests that carry ``zephyr_key`` markers."""
    if not _enabled():
        return
    key = _zephyr_key_for(item)
    if key:
        _keys[item.nodeid] = key


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[object]
) -> Generator[None, Any, None]:
    """Map call/setup outcomes onto Pass/Fail/Blocked for cycle items."""
    outcome = yield
    if not _enabled():
        return
    report = outcome.get_result()
    if report.when != "call" and not (report.when == "setup" and report.failed):
        return
    if item.nodeid not in _keys:
        return
    _durations[item.nodeid] = float(report.duration)
    if report.passed:
        _results[item.nodeid] = "Pass"
    elif report.failed:
        _results[item.nodeid] = "Fail"
    elif report.skipped:
        _results[item.nodeid] = "Blocked"


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Create a new Zephyr cycle or overwrite results on the chosen cycle."""
    if not _enabled():
        return
    if not _keys:
        print("zephyr_result_collector: no @PROJECT-T#### tests to push")
        return

    token = os.environ["JIRA_TOKEN"].strip()
    atm = os.environ.get("JIRA_ATM", "").strip().rstrip("/")
    if not atm:
        print("zephyr_result_collector: missing JIRA_ATM — skip push")
        return

    user_key = _jira_user_key(token, _jira_rest_base(atm))
    items = [_execution_item(nodeid, key, user_key) for nodeid, key in sorted(_keys.items())]
    mode = _cycle_mode()
    try:
        if mode == "override":
            key = _override_cycle(token, atm, _cycle_key(), items)
            name = str(_read_last_cycle().get("name") or _cycle_name() or key)
        else:
            name = _cycle_name()
            key = _create_cycle(token, atm, name, items)
            for item in items:
                print(f"  {item['testCaseKey']}: {item['status']}")
    except httpx.HTTPError as exc:
        print(f"zephyr_result_collector: network error: {exc}")
        return

    if not key:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    action = "overrode" if mode == "override" else "created"
    print(f"zephyr_result_collector: {action} testrun {key} at {stamp}")
    _write_last_cycle(key, name)
    _attach_allure_to_cycle(token, atm, key)
    issues = _cycle_issue_keys(token, atm, [str(item["testCaseKey"]) for item in items])
    _link_cycle_to_jira_issues(token, atm, key, name, issues)
