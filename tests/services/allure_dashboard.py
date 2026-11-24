"""Build Platform Allure dashboard HTML from ``allure-results/``."""

from __future__ import annotations

import json
import re
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from zlib import crc32

from tests.services.allure_labels import (
    ALLURE_CATEGORIES,
    FEATURES_ROOT,
    categorize_allure,
    taxonomy_from_markers,
)
from tests.services.assert_report import mask_pii

_TEMPLATE_PATH = Path(__file__).with_name("allure_dashboard.html")
_STATUS_KEYS = ("passed", "failed", "broken", "skipped", "unknown")
_SCENARIO_LINE = re.compile(r"^\s*Scenario(?: Outline)?:", re.MULTILINE)
_ZEPHYR_TAG = re.compile(r"^[A-Z][A-Z0-9]+-T\d+$", re.IGNORECASE)
_ZEPHYR_IN = re.compile(r"@?([A-Z][A-Z0-9]+-T\d+)\b", re.IGNORECASE)
_REASON_MAX = 240
_HTTP_MAX = 8
_HTTP_CHARS = 16_000
_GHERKIN_TAG = re.compile(r"@([A-Za-z][A-Za-z0-9_]*)")
_TEAM_ACRONYMS = frozenset({"kyc", "tci", "lms", "upg", "pcm", "aml", "bnpl"})
_TEAM_COLORS = {
    "kyc": "#0b3a82",
    "wallet": "#1d4ed8",
    "debit": "#2563eb",
    "bill": "#0000ff",
    "payment": "#1e3a8a",
    "app": "#1b2d4a",
    "dashboard": "#334155",
    "platform": "#64748b",
    "tci": "#0369a1",
    "lms": "#312e81",
}
_CAT_UI = {
    "Product defects": {"short": "Product", "color": "#e11d48", "icon": "bug"},
    "Environment / connectivity issues": {
        "short": "Environment",
        "color": "#0284c7",
        "icon": "cloud",
    },
    "Timeouts": {"short": "Timeout", "color": "#7a5af8", "icon": "clock"},
    "Playwright timeouts": {"short": "Playwright", "color": "#0e7490", "icon": "monitor"},
    "Test / framework defects": {"short": "Framework", "color": "#64748b", "icon": "wrench"},
    "Skipped — missing secrets or test data": {
        "short": "Secrets",
        "color": "#dc6803",
        "icon": "key",
    },
    "Uncategorized": {"short": "Other", "color": "#94a3b8", "icon": "help"},
    "Skipped": {"short": "Skipped", "color": "#dc6803", "icon": "skip"},
}


def team_label(name: str) -> str:
    """Human label for a team folder or Allure epic."""
    key = name.strip().lower()
    if not key:
        return "—"
    if key in _TEAM_ACRONYMS:
        return key.upper()
    return " ".join(part.capitalize() for part in key.replace("_", "-").split("-"))


def team_color(name: str) -> str:
    """Stable color for a team. Known teams are pinned; new folders hash to a hue."""
    key = name.strip().lower()
    if key in _TEAM_COLORS:
        return _TEAM_COLORS[key]
    hue = 215 + (crc32(key.encode("utf-8")) % 35)
    sat = 48 + (crc32(key.encode("utf-8")) % 12)
    light = 34 + (crc32(key[::-1].encode("utf-8")) % 10)
    return f"hsl({hue}, {sat}%, {light}%)"


def _category_meta() -> list[dict[str, str]]:
    names: list[str] = []
    for item in ALLURE_CATEGORIES:
        raw = item.get("name")
        if isinstance(raw, str) and raw:
            names.append(raw)
    names.extend(["Uncategorized", "Skipped"])
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        ui = _CAT_UI.get(name)
        if ui is None:
            hue = 215 + (crc32(name.encode("utf-8")) % 35)
            ui = {
                "short": name.split("—")[0].strip()[:18] or name[:18],
                "color": f"hsl({hue}, 40%, 38%)",
                "icon": "help",
            }
        rows.append({"name": name, **ui})
    return rows


def _gherkin_counts(text: str) -> tuple[int, int]:
    """Return (Scenario/Outline count, Examples data rows)."""
    scenarios = len(_SCENARIO_LINE.findall(text))
    example_rows = 0
    in_examples = False
    skipped_header = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Examples"):
            in_examples = True
            skipped_header = False
            continue
        if not in_examples:
            continue
        if line.startswith("|"):
            if not skipped_header:
                skipped_header = True
                continue
            if line.replace("|", "").strip():
                example_rows += 1
            continue
        if line.startswith(("@", "Scenario", "Feature", "Background", "Rule")):
            in_examples = False
    return scenarios, example_rows


def _feature_id(text: str, team: str, stem: str) -> str:
    header = text.split("Feature:", 1)[0]
    tags = set(_GHERKIN_TAG.findall(header))
    tags.add(team)
    tax = taxonomy_from_markers(tags)
    return tax.feature or f"{team}_{stem}"


def _empty_feature_row(name: str, in_repo: int) -> dict[str, Any]:
    return {
        "name": name,
        "total": 0,
        "passed": 0,
        "failed": 0,
        "failedOnly": 0,
        "broken": 0,
        "skipped": 0,
        "ran": 0,
        "rate": None,
        "ranRate": None,
        "ms": 0,
        "inRepo": in_repo,
    }


@dataclass(frozen=True)
class AllureCase:
    """One Allure ``*-result.json`` test.

    JSON attachments are included when pytest wrote them (passed, failed, or
    broken).
    """

    name: str
    status: str
    duration_ms: int
    epic: str
    feature: str
    story: str
    parent_suite: str
    suite: str
    full_name: str
    started_ms: int | None
    severity: str
    reason: str
    zephyr: str
    category: str
    step: str
    params: str
    behavior: str
    package: str
    http: tuple[dict[str, str], ...] = ()
    has_screenshot: bool = False
    has_trace: bool = False
    source: str = ""
    retries: int = 0
    history_id: str = ""
    is_retry: bool = False


def _gherkin_severity(labels: list[Any], allure_severity: str) -> str:
    """Map Allure Jira severity onto Gherkin ``@high`` / ``@medium`` / ``@low``."""
    for item in labels:
        if not isinstance(item, dict) or item.get("name") != "tag":
            continue
        raw = item.get("value")
        if not isinstance(raw, str):
            continue
        key = raw.strip().lstrip("@").lower()
        if key in {"high", "medium", "low"}:
            return key
    key = allure_severity.strip().lower()
    if key in {"high", "medium", "low"}:
        return key
    return {
        "critical": "high",
        "blocker": "high",
        "normal": "medium",
        "minor": "low",
        "trivial": "low",
    }.get(key, key)


def _label_value(labels: list[Any], key: str, default: str = "untagged") -> str:
    for item in labels:
        if isinstance(item, dict) and item.get("name") == key:
            value = item.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return default


def _duration_ms(payload: dict[str, Any]) -> int:
    start = payload.get("start")
    stop = payload.get("stop")
    if isinstance(start, int) and isinstance(stop, int) and stop >= start:
        return stop - start
    return 0


def _normalize_zephyr(text: str) -> str:
    match = _ZEPHYR_IN.search(text)
    if not match:
        return ""
    value = match.group(1).upper()
    return value if _ZEPHYR_TAG.match(value) else ""


def _zephyr_key(
    labels: list[Any],
    name: str = "",
    full_name: str = "",
    params: str = "",
) -> str:
    blobs = [name, full_name, params]
    for item in labels:
        if not isinstance(item, dict):
            continue
        for field in ("value", "name"):
            raw = item.get(field)
            if isinstance(raw, str) and raw.strip():
                blobs.append(raw)
    for blob in blobs:
        found = _normalize_zephyr(blob)
        if found:
            return found
    return ""


def _gherkin_zephyr_index(features_root: Path) -> dict[str, tuple[str, str]]:
    """Map scenario title (casefold) to ``(zephyr, relative .feature path)``."""
    index: dict[str, tuple[str, str]] = {}
    if not features_root.is_dir():
        return index
    for path in features_root.rglob("*.feature"):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            rel = path.relative_to(features_root).as_posix()
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        pending: list[str] = []
        feature_key = ""
        for raw in lines:
            line = raw.strip()
            if line.startswith("@"):
                pending.append(line)
                continue
            if line.startswith("Feature:"):
                feature_key = _normalize_zephyr(" ".join(pending))
                pending = []
                continue
            if line.startswith("Scenario"):
                title = line.split(":", 1)[-1].strip()
                key = _normalize_zephyr(" ".join(pending)) or feature_key
                pending = []
                if title:
                    index.setdefault(title.casefold(), (key, rel))
                continue
            if line.startswith(("Background", "Rule", "Examples")):
                pending = []
    return index


def _lookup_gherkin(
    index: dict[str, tuple[str, str]],
    name: str,
) -> tuple[str, str]:
    stripped = re.sub(r"\s*\[[^\]]+]\s*$", "", name).strip()
    candidates = [name, name.split(" -- ", 1)[0], stripped]
    for cand in candidates:
        hit = index.get(cand.strip().casefold())
        if hit:
            return hit
    return "", ""


def _with_gherkin_zephyr(cases: list[AllureCase], features_root: Path) -> list[AllureCase]:
    index = _gherkin_zephyr_index(features_root)
    if not index:
        return cases
    filled: list[AllureCase] = []
    for case in cases:
        zephyr, source = _lookup_gherkin(index, case.name)
        next_z = case.zephyr or zephyr
        next_s = case.source or source
        if next_z == case.zephyr and next_s == case.source:
            filled.append(case)
            continue
        filled.append(replace(case, zephyr=next_z, source=next_s))
    return filled


def _detail_line(payload: dict[str, Any]) -> str:
    details = payload.get("statusDetails")
    if not isinstance(details, dict):
        return ""
    raw = details.get("message")
    if not isinstance(raw, str) or not raw.strip():
        return ""
    cleaned = (
        raw.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )
    return mask_pii(" ".join(cleaned.split()))[:_REASON_MAX]


def _status_blobs(payload: dict[str, Any]) -> tuple[str, str]:
    details = payload.get("statusDetails")
    if not isinstance(details, dict):
        return "", ""
    message = details.get("message")
    trace = details.get("trace")
    msg = message if isinstance(message, str) else ""
    snippet = trace[:800] if isinstance(trace, str) else ""
    return msg, snippet


def _first_failed_step(steps: Any) -> str:
    if not isinstance(steps, list):
        return ""
    for step in steps:
        if not isinstance(step, dict):
            continue
        nested = _first_failed_step(step.get("steps"))
        if nested:
            return nested
        if step.get("status") in {"failed", "broken"}:
            name = step.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()[:120]
    return ""


def _params_line(payload: dict[str, Any]) -> str:
    raw = payload.get("parameters")
    if not isinstance(raw, list):
        return ""
    parts: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        if " object at " in value:
            continue
        parts.append(f"{name}={mask_pii(value)}")
    return "; ".join(parts)[:160]


def _iter_attachment_nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    raw = payload.get("attachments")
    if isinstance(raw, list):
        found.extend(item for item in raw if isinstance(item, dict))
    steps = payload.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                found.extend(_iter_attachment_nodes(step))
    return found


def _attachment_kind(item: dict[str, Any]) -> str:
    mime = str(item.get("type") or "").lower()
    name = str(item.get("name") or "").lower()
    source = str(item.get("source") or "").lower()
    if "image" in mime or name.startswith("screenshot"):
        return "screenshot"
    if "zip" in mime or name.startswith("trace") or source.endswith(".zip"):
        return "trace"
    if "json" in mime or source.endswith(".json") or name.startswith(("request ", "response ")):
        return "json"
    return ""


def _read_json_attachment(results_dir: Path, source: str) -> str:
    path = results_dir / Path(source).name
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    try:
        pretty = json.dumps(json.loads(text), ensure_ascii=True, indent=2)
    except json.JSONDecodeError:
        pretty = text
    if len(pretty) > _HTTP_CHARS:
        return pretty[:_HTTP_CHARS] + "\n..."
    return pretty


def _case_attachments(
    payload: dict[str, Any],
    results_dir: Path,
) -> tuple[tuple[dict[str, str], ...], bool, bool]:
    nodes = _iter_attachment_nodes(payload)
    has_shot = any(_attachment_kind(node) == "screenshot" for node in nodes)
    has_trace = any(_attachment_kind(node) == "trace" for node in nodes)
    http: list[dict[str, str]] = []
    for node in nodes:
        if len(http) >= _HTTP_MAX:
            break
        if _attachment_kind(node) != "json":
            continue
        source = node.get("source")
        name = node.get("name")
        if not isinstance(source, str) or not isinstance(name, str):
            continue
        body = _read_json_attachment(results_dir, source)
        if not body:
            continue
        http.append({"name": name[:160], "body": body})
    return tuple(http), has_shot, has_trace


def _git_short() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _with_git(rows: list[list[str]]) -> list[list[str]]:
    mapping = {row[0]: row[1] for row in rows}
    if mapping.get("Git.Commit") not in {None, "", "unknown"}:
        return rows
    commit = _git_short()
    if not commit:
        return rows
    out = [row for row in rows if row[0] != "Git.Commit"]
    out.append(["Git.Commit", commit])
    return out


def _case_from_payload(
    payload: dict[str, Any],
    stem: str,
    results_dir: Path,
) -> AllureCase | None:
    if "status" not in payload:
        return None
    raw_labels = payload.get("labels")
    labels: list[Any] = raw_labels if isinstance(raw_labels, list) else []
    name = payload.get("name")
    status = payload.get("status")
    full_name = payload.get("fullName")
    started_raw = payload.get("start")
    status_s = status if isinstance(status, str) else "unknown"
    name_s = name if isinstance(name, str) else stem
    full_s = full_name if isinstance(full_name, str) else ""
    params_s = _params_line(payload)
    raw_msg, raw_trace = _status_blobs(payload)
    raw_hid = payload.get("historyId")
    history_id = raw_hid if isinstance(raw_hid, str) else ""
    is_retry = payload.get("retry") is True
    if is_retry:
        http, has_shot, has_trace = (), False, False
    else:
        http, has_shot, has_trace = _case_attachments(payload, results_dir)
    return AllureCase(
        name=name_s,
        status=status_s,
        duration_ms=_duration_ms(payload),
        epic=_label_value(labels, "epic"),
        feature=_label_value(labels, "feature"),
        story=_label_value(labels, "story"),
        parent_suite=_label_value(labels, "parentSuite", default="other"),
        suite=_label_value(labels, "suite", default="other"),
        full_name=full_s,
        started_ms=started_raw if isinstance(started_raw, int) else None,
        severity=_gherkin_severity(labels, _label_value(labels, "severity", default="")),
        reason=_detail_line(payload),
        zephyr=_zephyr_key(labels, name_s, full_s, params_s),
        category=categorize_allure(status_s, raw_msg, raw_trace),
        step=_first_failed_step(payload.get("steps")),
        params=params_s,
        behavior=_label_value(labels, "subSuite", default=""),
        package=_label_value(labels, "package", default=""),
        http=http,
        has_screenshot=has_shot,
        has_trace=has_trace,
        history_id=history_id,
        is_retry=is_retry,
    )


def _retry_group_key(case: AllureCase) -> str:
    if case.history_id:
        return case.history_id
    if case.full_name:
        return f"{case.full_name}\0{case.params}"
    return ""


def _pick_final_attempt(group: list[AllureCase]) -> AllureCase:
    live = [case for case in group if not case.is_retry]
    pool = live or group
    return max(pool, key=lambda case: (case.started_ms or 0, case.duration_ms))


def _collapse_retries(cases: list[AllureCase]) -> list[AllureCase]:
    groups: dict[str, list[AllureCase]] = defaultdict(list)
    loners: list[AllureCase] = []
    for case in cases:
        key = _retry_group_key(case)
        if not key:
            loners.append(case)
            continue
        groups[key].append(case)
    out: list[AllureCase] = list(loners)
    for group in groups.values():
        final = _pick_final_attempt(group)
        extra = len(group) - 1
        out.append(replace(final, retries=extra) if extra else final)
    return out


def load_cases(results_dir: Path) -> list[AllureCase]:
    """Parse Allure ``*-result.json`` files. Skips containers and unreadable JSON."""
    cases: list[AllureCase] = []
    for path in sorted(results_dir.glob("*-result.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        parsed = _case_from_payload(payload, path.stem, results_dir)
        if parsed is not None:
            cases.append(parsed)
    return _collapse_retries(cases)


def _empty_bucket() -> dict[str, int]:
    return {**{key: 0 for key in _STATUS_KEYS}, "ms": 0}


def _bucket_counts(cases: list[AllureCase], attr: str) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, int]] = defaultdict(_empty_bucket)
    for case in cases:
        key = getattr(case, attr) or "untagged"
        status = case.status if case.status in _STATUS_KEYS else "unknown"
        buckets[key][status] += 1
        buckets[key]["ms"] += case.duration_ms
    rows: list[dict[str, Any]] = []
    for name, counts in sorted(buckets.items()):
        total = sum(counts[key] for key in _STATUS_KEYS)
        passed = counts["passed"]
        skipped = counts["skipped"]
        ran = total - skipped
        rows.append(
            {
                "name": name,
                "total": total,
                "passed": passed,
                "failed": counts["failed"] + counts["broken"],
                "failedOnly": counts["failed"],
                "broken": counts["broken"],
                "skipped": skipped,
                "ran": ran,
                "rate": round(100.0 * passed / total, 1) if total else 0.0,
                "ranRate": round(100.0 * passed / ran, 1) if ran else None,
                "ms": counts["ms"],
            }
        )
    return rows


def _catalog_teams(features_root: Path) -> list[dict[str, Any]]:
    if not features_root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for folder in sorted(p for p in features_root.iterdir() if p.is_dir()):
        if folder.name.startswith(("_", ".")):
            continue
        files = list(folder.rglob("*.feature"))
        scenarios = 0
        examples = 0
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            scn, ex = _gherkin_counts(text)
            scenarios += scn
            examples += ex
        rows.append(
            {
                "name": folder.name,
                "files": len(files),
                "scenarios": scenarios,
                "examples": examples,
            }
        )
    return rows


def _catalog_features(features_root: Path) -> list[dict[str, Any]]:
    if not features_root.is_dir():
        return []
    by_name: dict[str, dict[str, Any]] = {}
    for folder in sorted(p for p in features_root.iterdir() if p.is_dir()):
        if folder.name.startswith(("_", ".")):
            continue
        team = folder.name
        for path in folder.rglob("*.feature"):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            scn, ex = _gherkin_counts(text)
            name = _feature_id(text, team, path.stem)
            current = by_name.get(name)
            if current is None:
                by_name[name] = {
                    "name": name,
                    "team": team,
                    "scenarios": scn,
                    "examples": ex,
                    "files": 1,
                }
            else:
                current["scenarios"] = int(current["scenarios"]) + scn
                current["examples"] = int(current["examples"]) + ex
                current["files"] = int(current["files"]) + 1
    return list(by_name.values())


def _merge_features(
    run_rows: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_run = {str(row["name"]): row for row in run_rows}
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in catalog:
        name = str(item["name"])
        seen.add(name)
        run = by_run.get(name)
        if run is None:
            merged.append(_empty_feature_row(name, int(item["scenarios"])))
            continue
        row = dict(run)
        row["inRepo"] = int(item["scenarios"])
        merged.append(row)
    for row in run_rows:
        name = str(row["name"])
        if name not in seen:
            extra = dict(row)
            extra.setdefault("inRepo", 0)
            merged.append(extra)
    merged.sort(
        key=lambda row: (
            0 if int(row["total"]) else 1,
            -int(row["failed"]),
            -int(row["total"]),
            str(row["name"]),
        )
    )
    return merged


def _team_tiles(
    run_rows: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_run = {row["name"]: row for row in run_rows}
    tiles: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in catalog:
        name = str(item["name"])
        seen.add(name)
        run = by_run.get(name)
        tiles.append(_tile_from_run(name, run, item))
    for row in run_rows:
        name = str(row["name"])
        if name not in seen:
            tiles.append(_tile_from_run(name, row, None))
    tiles.sort(
        key=lambda tile: (
            0 if int(tile["total"]) else 1,
            -int(tile["failed"]),
            -int(tile["inRepo"]),
            str(tile["name"]),
        )
    )
    return tiles


def _tile_from_run(
    name: str,
    run: dict[str, Any] | None,
    catalog: dict[str, Any] | None,
) -> dict[str, Any]:
    in_repo = int(catalog["scenarios"]) if catalog else 0
    files = int(catalog["files"]) if catalog else 0
    if run is None:
        return {
            "name": name,
            "total": 0,
            "passed": 0,
            "failed": 0,
            "failedOnly": 0,
            "broken": 0,
            "skipped": 0,
            "ran": 0,
            "rate": None,
            "ranRate": None,
            "inRepo": in_repo,
            "files": files,
            "ms": 0,
            "cover": 0.0,
            "label": team_label(name),
            "color": team_color(name),
            "examples": int(catalog["examples"]) if catalog and "examples" in catalog else 0,
        }
    total = int(run["total"])
    cover = round(100.0 * total / in_repo, 1) if in_repo else 100.0
    return {
        "name": name,
        "total": run["total"],
        "passed": run["passed"],
        "failed": run["failed"],
        "failedOnly": run.get("failedOnly", max(0, int(run["failed"]) - int(run.get("broken", 0)))),
        "broken": run.get("broken", 0),
        "skipped": run["skipped"],
        "ran": run.get("ran", max(0, int(run["total"]) - int(run["skipped"]))),
        "rate": run["rate"],
        "ranRate": run.get("ranRate"),
        "inRepo": in_repo,
        "files": files,
        "ms": run.get("ms", 0),
        "cover": cover,
        "label": team_label(name),
        "color": team_color(name),
        "examples": int(catalog["examples"]) if catalog and "examples" in catalog else 0,
    }


def _read_environment(results_dir: Path) -> list[list[str]]:
    path = results_dir / "environment.properties"
    if not path.is_file():
        return []
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        rows.append([key.strip(), value.strip()])
    return rows


def _read_executor(results_dir: Path) -> dict[str, Any]:
    path = results_dir / "executor.json"
    if not path.is_file():
        return {"name": "Local", "type": "local"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {"name": "Local", "type": "local"}
    return payload if isinstance(payload, dict) else {"name": "Local", "type": "local"}


def _case_row(case: AllureCase) -> dict[str, Any]:
    row: dict[str, Any] = {
        "name": case.name,
        "status": case.status,
        "epic": case.epic,
        "feature": case.feature,
        "story": case.story,
        "type": case.parent_suite,
        "suite": case.suite,
        "ms": case.duration_ms,
        "severity": case.severity,
        "reason": case.reason,
        "zephyr": case.zephyr,
        "category": case.category,
        "step": case.step,
        "params": case.params,
        "behavior": case.behavior,
        "package": case.package,
    }
    if case.source:
        row["source"] = case.source
    if case.retries:
        row["retries"] = case.retries
    if case.http:
        row["http"] = list(case.http)
    if case.has_screenshot:
        row["hasScreenshot"] = True
    if case.has_trace:
        row["hasTrace"] = True
    return row


def build_dashboard_model(
    results_dir: Path,
    features_root: Path | None = None,
) -> dict[str, Any]:
    """Aggregate counts for the HTML dashboard.

    Args:
        results_dir: Pytest ``--alluredir`` folder.
        features_root: Gherkin tree for team tiles. Defaults to ``tests/bdd/features``.

    Returns:
        JSON-serializable dashboard model (counts, team tiles, case rows).
    """
    cases = _with_gherkin_zephyr(
        load_cases(results_dir),
        features_root if features_root is not None else FEATURES_ROOT,
    )
    status_counts = {key: 0 for key in _STATUS_KEYS}
    for case in cases:
        key = case.status if case.status in _STATUS_KEYS else "unknown"
        status_counts[key] += 1
    total = len(cases)
    passed = status_counts["passed"]
    failed = status_counts["failed"] + status_counts["broken"]
    skipped = status_counts["skipped"]
    executed = total - skipped
    duration_ms = sum(case.duration_ms for case in cases)
    rows = [_case_row(case) for case in cases]
    catalog = _catalog_teams(features_root if features_root is not None else FEATURES_ROOT)
    catalog_features = _catalog_features(
        features_root if features_root is not None else FEATURES_ROOT
    )
    catalog_scenarios = sum(int(item["scenarios"]) for item in catalog)
    catalog_files = sum(int(item["files"]) for item in catalog)
    starts = [case.started_ms for case in cases if case.started_ms is not None]
    problems = [row for row in rows if row["status"] in {"failed", "broken"}]
    skip_rows = [row for row in rows if row["status"] == "skipped"]
    fail_cases = [case for case in cases if case.status in {"failed", "broken"}]
    skip_cases = [case for case in cases if case.status == "skipped"]
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "failedOnly": status_counts["failed"],
        "skipped": skipped,
        "broken": status_counts["broken"],
        "executed": executed,
        "rate": round(100.0 * passed / total, 1) if total else 0.0,
        "executedRate": round(100.0 * passed / executed, 1) if executed else 0.0,
        "durationMs": duration_ms,
        "startedMs": min(starts) if starts else None,
        "catalogScenarios": catalog_scenarios,
        "catalogFiles": catalog_files,
        "coveragePct": round(100.0 * total / catalog_scenarios, 1) if catalog_scenarios else 0.0,
        "domains": _team_tiles(_bucket_counts(cases, "epic"), catalog),
        "types": _bucket_counts(cases, "parent_suite"),
        "suites": _bucket_counts(cases, "suite"),
        "features": _merge_features(_bucket_counts(cases, "feature"), catalog_features),
        "failCategories": _bucket_counts(fail_cases, "category"),
        "skipCategories": _bucket_counts(skip_cases, "category"),
        "categoryMeta": _category_meta(),
        "problems": problems,
        "skips": skip_rows,
        "cases": rows,
        "catalogTeams": len(catalog),
        "environment": _with_git(_read_environment(results_dir)),
        "executor": _read_executor(results_dir),
    }


def render_dashboard_html(model: dict[str, Any]) -> str:
    """Single-file dashboard. Data is JSON; the browser paints the UI."""
    payload = json.dumps(model, ensure_ascii=True).replace("<", "\\u003c")
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace("__DASHBOARD_JSON__", payload)


def _stamp_environment(results_dir: Path, generated_ms: int) -> None:
    path = results_dir / "environment.properties"
    kept: list[str] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            key = line.split("=", 1)[0].strip()
            if key.startswith("Platform."):
                continue
            kept.append(line)
    extra = [
        f"Platform.Dashboard.GeneratedMs={generated_ms}",
        f"Platform.Results={results_dir.name}",
    ]
    commit = _git_short()
    if commit:
        extra.append(f"Platform.Git.Commit={commit}")
    path.write_text("\n".join([*kept, *extra]) + "\n", encoding="utf-8")


def _write_run_sidecar(results_dir: Path, generated_ms: int) -> None:
    payload = {
        "generatedMs": generated_ms,
        "git": _git_short(),
        "results": results_dir.name,
    }
    (results_dir / "platform-run.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def write_dashboard(
    results_dir: Path,
    dest: Path,
    features_root: Path | None = None,
) -> Path:
    """Write ``dest`` HTML from ``results_dir``. Creates parent folders.

    Also writes ``environment.properties`` Platform.* keys and ``platform-run.json``
    into ``results_dir``.

    Args:
        results_dir: Pytest ``--alluredir`` folder.
        dest: Output HTML path (usually ``allure-dashboard/index.html``).
        features_root: Gherkin tree for team tiles. Defaults to ``tests/bdd/features``.

    Returns:
        The path written.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    model = build_dashboard_model(results_dir, features_root)
    generated_ms = int(time.time() * 1000)
    model["generatedMs"] = generated_ms
    _stamp_environment(results_dir, generated_ms)
    _write_run_sidecar(results_dir, generated_ms)
    model["environment"] = _with_git(_read_environment(results_dir))
    dest.write_text(render_dashboard_html(model), encoding="utf-8")
    return dest
