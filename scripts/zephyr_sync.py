#!/usr/bin/env python3
r"""Sync Gherkin scenarios to Zephyr Scale (ATM).

Env (either process exports OR local file — preferred for agents/team laptops):
  secrets/jira_atm.env   ← copy from secrets/jira_atm.example.env (gitignored)
  # or:
  export JIRA_TOKEN=...
  export JIRA_ATM=https://jira.demo-platform.net/rest/atm/1.0

Create (scenario has @zephyr, no key yet):
  PYTHONPATH=. python scripts/zephyr_sync.py \\
    --feature tests/bdd/features/bill/tci/tci_inquiry.feature

Update all keyed scenarios in one file (skips unchanged after GET compare):
  PYTHONPATH=. python scripts/zephyr_sync.py \\
    --feature tests/bdd/features/bill/tci/tci_inquiry.feature --update

Update one case only:
  PYTHONPATH=. python scripts/zephyr_sync.py \\
    --feature tests/bdd/features/bill/tci/tci_inquiry.feature --key ALPHA-T2132

Whole directory / several trees (recursive *.feature):
  PYTHONPATH=. python scripts/zephyr_sync.py \\
    --features tests/bdd/features/bill/ --create --update

  PYTHONPATH=. python scripts/zephyr_sync.py \\
    --features tests/bdd/features/bill/ --features tests/bdd/features/wallet/ --update

Folder: default is derived from path under features/ (bill/tci → /bill/tci).
Override with --folder /Bill/TCI for every file in the run.

After create: writes @PROJECT-T#### (e.g. ALPHA-T…, KYC-T…) and removes @zephyr.

Supports plain Scenario, Scenario Outline (+ Examples), step data tables,
doc strings, multi-line tag blocks, and Feature Background (Background steps
are prepended into each case's BDD script). One Zephyr case per Outline.

Labels: Feature tags + scenario tags + path segments under features/ +
"automated" (no hardcoded bill/tci). Severity tags map to Zephyr priority.
Jira story tags like @ALPHA-123 / @KYC-99 (not @…-T…) are linked via issueLinks.
A ticketed Git branch (feat/ALPHA-15117-slug) adds that issue key automatically.

Feature-level @zephyr: create every scenario/outline in the file that has no
@PROJECT-T#### yet (including untagged scenarios); write a unique key on each;
then remove @zephyr from the Feature tag line. Scenario-level @zephyr still works.

Project defaults to ALPHA; pass --project KYC for the KYC board. Status defaults
to Draft; pass --status Approved when cases should land approved.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from jira_branch import branch_issue_key  # noqa: E402
from jira_local_env import load_jira_local_env  # noqa: E402

# Zephyr test-case keys: ALPHA-T1234, KYC-T760, …
_ZEPHYR_T_TAG = re.compile(r"^([A-Z][A-Z0-9]+)-T(\d+)$", re.IGNORECASE)
_ISSUE_KEY_TAG = re.compile(r"^[A-Z][A-Z0-9]+-\d+$", re.IGNORECASE)
_DEFAULT_PROJECT = "ALPHA"
_DEFAULT_STATUS = "Draft"
_DEFAULT_PRECONDITION = "UAT reachable; required secrets filled; dependent data stores available."
_SCENARIO_START = re.compile(r"^(\s*)(Scenario(?: Outline)?):\s*(.+?)\s*$")
_TAG_LINE = re.compile(r"^(\s*)(@\S+(?:\s+@\S+)*)\s*$")
_STEP = re.compile(r"^(\s*)(Given|When|Then|And|But)\s+(.+?)\s*$", re.IGNORECASE)
_BACKGROUND = re.compile(r"^(\s*)Background:\s*$", re.IGNORECASE)
_EXAMPLES = re.compile(r"^(\s*)Examples:\s*$", re.IGNORECASE)
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_DOCSTRING_OPEN = re.compile(r'^(\s*)"""(.*)$')

_SKIP_LABELS = frozenset({"zephyr", "positive", "negative", "high", "medium", "low"})
_PRIORITY_BY_SEVERITY = {
    "high": "High",
    "medium": "Normal",
    "low": "Low",
}


@dataclass
class ScenarioBlock:
    """One Scenario / Scenario Outline parsed from a feature file."""

    name: str
    tags: list[str]
    steps: list[str]
    tag_line_index: int
    tag_line_count: int
    tag_indent: str
    scenario_line_index: int

    @property
    def zephyr_key(self) -> str | None:
        """Return the ``PROJECT-T####`` key from tags, if present."""
        return _zephyr_key(self.tags)

    @property
    def wants_create(self) -> bool:
        """Scenario-level @zephyr and not yet keyed."""
        return any(t.lower() == "zephyr" for t in self.tags) and not self.zephyr_key

    @property
    def script_text(self) -> str:
        """Join steps into the Zephyr BDD script body."""
        return "\n".join(self.steps)

    @property
    def issue_keys(self) -> list[str]:
        """Jira story/bug keys from tags (excludes Zephyr ``PROJECT-T`` keys)."""
        return _issue_keys(self.tags)


def _zephyr_key(tags: list[str]) -> str | None:
    for tag in tags:
        match = _ZEPHYR_T_TAG.match(tag)
        if match:
            return f"{match.group(1).upper()}-T{match.group(2)}"
    return None


def _is_issue_key(tag: str) -> bool:
    """Jira issue key (story/bug/…) — not a Zephyr PROJECT-T#### test-case key."""
    if _ZEPHYR_T_TAG.match(tag):
        return False
    return bool(_ISSUE_KEY_TAG.match(tag))


def _issue_keys(tags: list[str]) -> list[str]:
    return list(dict.fromkeys(t.upper() for t in tags if _is_issue_key(t)))


def _priority_for(tags: list[str]) -> str:
    """Map @high/@medium/@low → Zephyr priority (first match in that order)."""
    lower = {t.lower() for t in tags}
    for severity, priority in _PRIORITY_BY_SEVERITY.items():
        if severity in lower:
            return priority
    return "Normal"


def _normalize_key(key: str) -> str:
    key = key.strip()
    if key.startswith("@"):
        key = key[1:]
    match = _ZEPHYR_T_TAG.match(key)
    if not match:
        raise SystemExit(
            f"Invalid --key {key!r}; expected PROJECT-T#### (e.g. KYC-T760, ALPHA-T2194)"
        )
    return f"{match.group(1).upper()}-T{match.group(2)}"


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(
            f"Missing {name}. Set it in the shell or create "
            f"secrets/jira_atm.env (see secrets/jira_atm.example.env)."
        )
    return value


def _normalize_keyword(raw: str) -> str:
    lower = raw.lower()
    if lower == "and":
        return "And"
    if lower == "but":
        return "But"
    return {"given": "Given", "when": "When", "then": "Then"}[lower]


def _normalize_script(text: str) -> str:
    """Compare BDD scripts ignoring trailing spaces / blank lines."""
    lines = [ln.rstrip() for ln in (text or "").replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return "\n".join(lines)


def _normalize_folder(folder: str) -> str:
    return "/" + "/".join(p for p in folder.strip().split("/") if p)


def _is_gherkin_block_end(raw: str) -> bool:
    """True when a scenario/background body should stop collecting lines."""
    if _SCENARIO_START.match(raw) or _TAG_LINE.match(raw) or _BACKGROUND.match(raw):
        return True
    return raw.strip().startswith("Feature:")


def _collect_docstring(lines: list[str], start: int) -> tuple[list[str], int]:
    """Collect a Gherkin doc string (\"\"\" … \"\"\") including delimiters."""
    raw = lines[start]
    out = [raw.rstrip()]
    stripped = raw.strip()
    if stripped.startswith('"""') and stripped.endswith('"""') and len(stripped) > 3:
        return out, start + 1
    k = start + 1
    while k < len(lines):
        out.append(lines[k].rstrip())
        if '"""' in lines[k]:
            return out, k + 1
        k += 1
    return out, k


def _collect_gherkin_body(lines: list[str], start: int) -> tuple[list[str], int]:
    """Collect steps, data tables, doc strings, and Examples until the next block."""
    body: list[str] = []
    k = start
    while k < len(lines):
        raw = lines[k]
        if _is_gherkin_block_end(raw):
            break
        if _DOCSTRING_OPEN.match(raw):
            doc_lines, k = _collect_docstring(lines, k)
            body.extend(doc_lines)
            continue
        step_match = _STEP.match(raw)
        if step_match:
            keyword = _normalize_keyword(step_match.group(2))
            body.append(f"{keyword} {step_match.group(3).strip()}")
            k += 1
            continue
        if _EXAMPLES.match(raw):
            body.append("Examples:")
            k += 1
            continue
        if _TABLE_ROW.match(raw):
            body.append(raw.rstrip())
            k += 1
            continue
        k += 1
    return body, k


def _parse_background(lines: list[str]) -> list[str]:
    """Feature Background steps (+ tables/doc strings), or [] if none."""
    for i, raw in enumerate(lines):
        if _SCENARIO_START.match(raw):
            return []
        if _BACKGROUND.match(raw):
            body, _ = _collect_gherkin_body(lines, i + 1)
            return body
    return []


def _parse_feature_tags(lines: list[str]) -> list[str]:
    """Tags on the line(s) immediately above Feature:."""
    for i, raw in enumerate(lines):
        if not raw.strip().startswith("Feature:"):
            continue
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        tag_lines: list[str] = []
        while j >= 0 and _TAG_LINE.match(lines[j]):
            tag_lines.append(lines[j])
            j -= 1
        tags: list[str] = []
        for tag_line in reversed(tag_lines):
            tags.extend(re.findall(r"@(\S+)", tag_line))
        return tags
    return []


def _collect_tag_block(lines: list[str], start: int) -> tuple[list[str], int, int, str] | None:
    """Consecutive @tag lines → (tags, first_index, line_count, indent)."""
    tag_match = _TAG_LINE.match(lines[start])
    if not tag_match:
        return None
    tag_indent = tag_match.group(1)
    tags: list[str] = []
    j = start
    while j < len(lines):
        match = _TAG_LINE.match(lines[j])
        if not match:
            break
        tags.extend(re.findall(r"@(\S+)", match.group(2)))
        j += 1
    return tags, start, j - start, tag_indent


def _feature_wants_create(feature_tags: list[str]) -> bool:
    return any(t.lower() == "zephyr" for t in feature_tags)


def _parse_scenarios(feature_text: str) -> list[ScenarioBlock]:
    """Parse Scenario / Scenario Outline (with or without tags); prepend Background."""
    lines = feature_text.splitlines()
    background = _parse_background(lines)
    found: list[ScenarioBlock] = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("Feature:"):
            i += 1
            continue

        block = _collect_tag_block(lines, i)
        if block:
            tags, tag_line_index, tag_line_count, tag_indent = block
            j = tag_line_index + tag_line_count
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines):
                break
            scenario_match = _SCENARIO_START.match(lines[j])
            if not scenario_match:
                # Tag block above Feature: or orphan tags — skip one line
                i += 1
                continue
            name = scenario_match.group(3).strip()
            body, k = _collect_gherkin_body(lines, j + 1)
            steps = [*background, *body]
            if steps:
                found.append(
                    ScenarioBlock(
                        name=name,
                        tags=tags,
                        steps=steps,
                        tag_line_index=tag_line_index,
                        tag_line_count=tag_line_count,
                        tag_indent=tag_indent,
                        scenario_line_index=j,
                    )
                )
            i = k
            continue

        scenario_match = _SCENARIO_START.match(lines[i])
        if scenario_match:
            name = scenario_match.group(3).strip()
            indent = scenario_match.group(1)
            body, k = _collect_gherkin_body(lines, i + 1)
            steps = [*background, *body]
            if steps:
                found.append(
                    ScenarioBlock(
                        name=name,
                        tags=[],
                        steps=steps,
                        tag_line_index=-1,
                        tag_line_count=0,
                        tag_indent=indent,
                        scenario_line_index=i,
                    )
                )
            i = k
            continue

        i += 1
    return found


def _strip_zephyr_from_feature_tags(lines: list[str]) -> bool:
    """Remove @zephyr from the Feature tag block. Returns True if anything changed."""
    for i, raw in enumerate(lines):
        if not raw.strip().startswith("Feature:"):
            continue
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        end = j
        while j >= 0 and _TAG_LINE.match(lines[j]):
            j -= 1
        start = j + 1
        if start > end:
            return False
        changed = False
        for idx in range(start, end + 1):
            match = _TAG_LINE.match(lines[idx])
            if not match:
                continue
            indent = match.group(1)
            tags = re.findall(r"@(\S+)", match.group(2))
            new_tags = [t for t in tags if t.lower() != "zephyr"]
            if new_tags == tags:
                continue
            changed = True
            lines[idx] = indent + " ".join(f"@{t}" for t in new_tags) if new_tags else ""
        return changed
    return False


def _path_labels(feature_path: Path) -> list[str]:
    """Directory segments under features/ → labels (bill/tci → bill, tci)."""
    parts = feature_path.resolve().parts
    if "features" not in parts:
        return []
    idx = parts.index("features")
    return [p for p in parts[idx + 1 : -1] if p]


def _label_candidates(tags: list[str]) -> list[str]:
    return [
        t
        for t in tags
        if t.lower() not in _SKIP_LABELS and not _ZEPHYR_T_TAG.match(t) and not _is_issue_key(t)
    ]


def _labels_for(
    scenario_tags: list[str],
    *,
    feature_tags: list[str] | None = None,
    path_labels: list[str] | None = None,
    extra: list[str] | None = None,
) -> list[str]:
    """Feature tags + scenario tags + path segments + automated (+ CLI extras)."""
    items: list[str] = [
        *_label_candidates(feature_tags or []),
        *_label_candidates(scenario_tags),
        "automated",
        *(path_labels or []),
        *(extra or []),
    ]
    return list(dict.fromkeys(items))


def _create_testcase(
    client: httpx.Client,
    *,
    name: str,
    steps: list[str],
    folder: str,
    labels: list[str],
    priority: str,
    project_key: str,
    status: str,
    precondition: str,
    issue_keys: list[str] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "projectKey": project_key,
        "name": name,
        "objective": name,
        "precondition": precondition,
        "status": status,
        "priority": priority,
        "labels": labels,
        "folder": folder,
        "testScript": {
            "type": "BDD",
            "text": "\n".join(steps),
        },
    }
    if issue_keys:
        payload["issueLinks"] = issue_keys
    response = client.post("/testcase", json=payload)
    if response.status_code not in (200, 201) and issue_keys:
        # Some ATM builds reject issueLinks on create — retry without, link after.
        payload.pop("issueLinks", None)
        response = client.post("/testcase", json=payload)
    if response.status_code not in (200, 201):
        raise SystemExit(f"Create failed HTTP {response.status_code}: {response.text[:500]}")
    body = response.json()
    key = body.get("key")
    if not key:
        raise SystemExit(f"Create response missing key: {body!r}")
    return str(key)


def _sanitize_testcase_put(body: dict[str, Any]) -> dict[str, Any]:
    """Drop ATM read-only / nested fields that make PUT return HTTP 500."""
    cleaned = dict(body)
    for read_only in (
        "createdOn",
        "updatedOn",
        "createdBy",
        "updatedBy",
        "owner",
        "key",
        "id",
        "self",
        "projectKey",
        "projectId",
        "keyNumber",
    ):
        cleaned.pop(read_only, None)
    script = cleaned.get("testScript")
    if isinstance(script, dict):
        cleaned["testScript"] = {
            "type": script.get("type") or "BDD",
            "text": script.get("text") or "",
        }
    return cleaned


def _link_issues(client: httpx.Client, key: str, issue_keys: list[str]) -> None:
    """Best-effort link of Jira issues to a Zephyr test case."""
    if not issue_keys:
        return
    attempts = [
        (f"/testcase/{key}/issueLinks", {"issueKeys": issue_keys}),
        (f"/testcase/{key}/issueLinks", issue_keys),
        ("/testcase/link-issues", {"testCaseKey": key, "issueKeys": issue_keys}),
    ]
    for path, payload in attempts:
        response = client.post(path, json=payload)
        if response.status_code in (200, 201, 204):
            print(f"  linked issues {issue_keys} -> {key}")
            return
    remote = _get_testcase(client, key)
    body = _sanitize_testcase_put(remote)
    body["issueLinks"] = issue_keys
    response = client.put(f"/testcase/{key}", json=body)
    if response.status_code in (200, 201):
        print(f"  linked issues {issue_keys} -> {key} (via PUT)")
        return
    again = _get_testcase(client, key)
    linked = again.get("issueLinks") or []
    if set(issue_keys).issubset({str(x) for x in linked}):
        print(f"  linked issues {issue_keys} -> {key} (already present)")
        return
    print(
        f"  warning: could not link {issue_keys} to {key} "
        f"(last HTTP {response.status_code}); link manually in Zephyr UI"
    )


def _get_testcase(client: httpx.Client, key: str) -> dict[str, Any]:
    current = client.get(f"/testcase/{key}")
    if current.status_code != 200:
        raise SystemExit(f"GET {key} failed HTTP {current.status_code}: {current.text[:500]}")
    return current.json()


def _normalize_label_set(labels: list[str] | None) -> list[str]:
    return sorted({(x or "").strip().lower() for x in (labels or []) if x})


def _remote_matches(
    remote: dict[str, Any],
    *,
    name: str,
    script_text: str,
    folder: str,
    priority: str,
    labels: list[str],
) -> bool:
    remote_script = ""
    script = remote.get("testScript") or {}
    if isinstance(script, dict):
        remote_script = script.get("text") or ""
    remote_folder = remote.get("folder") or ""
    remote_priority = (remote.get("priority") or "Normal").strip()
    return (
        (remote.get("name") or "").strip() == name.strip()
        and _normalize_script(remote_script) == _normalize_script(script_text)
        and _normalize_folder(str(remote_folder)).lower() == _normalize_folder(folder).lower()
        and remote_priority.lower() == priority.lower()
        and _normalize_label_set(remote.get("labels")) == _normalize_label_set(labels)
    )


def _put_testcase(
    client: httpx.Client,
    *,
    key: str,
    remote: dict[str, Any],
    name: str,
    steps: list[str],
    folder: str,
    labels: list[str],
    priority: str,
    status: str,
    precondition: str,
    issue_keys: list[str] | None = None,
) -> None:
    body = _sanitize_testcase_put(remote)
    body["name"] = name
    body["folder"] = folder
    body["labels"] = labels
    body["priority"] = priority
    body["status"] = status
    body["precondition"] = precondition
    body["objective"] = body.get("objective") or name
    body["testScript"] = {
        "type": "BDD",
        "text": "\n".join(steps),
    }
    if issue_keys:
        body["issueLinks"] = issue_keys

    response = client.put(f"/testcase/{key}", json=body)
    if response.status_code not in (200, 201):
        minimal: dict[str, Any] = {
            "name": name,
            "folder": folder,
            "labels": labels,
            "priority": priority,
            "status": status,
            "precondition": precondition,
            "testScript": {"type": "BDD", "text": "\n".join(steps)},
        }
        if issue_keys:
            minimal["issueLinks"] = issue_keys
        response = client.put(f"/testcase/{key}", json=minimal)
    if response.status_code not in (200, 201):
        raise SystemExit(f"Update {key} failed HTTP {response.status_code}: {response.text[:500]}")


def _insert_key_tag(tags: list[str], key: str) -> list[str]:
    """Replace @zephyr with the Zephyr key; keep other scenario tags."""
    rest = [t for t in tags if t.lower() != "zephyr" and not _ZEPHYR_T_TAG.match(t)]
    return [key, *rest]


def _folder_from_feature_path(feature_path: Path) -> str:
    """Map tests/bdd/features/bill/tci/x.feature → /bill/tci."""
    parts = feature_path.resolve().parts
    if "features" not in parts:
        raise SystemExit(
            f"Cannot derive folder from {feature_path} "
            "(path has no 'features/' segment); pass --folder"
        )
    idx = parts.index("features")
    dirs = parts[idx + 1 : -1]
    if not dirs:
        raise SystemExit(
            f"Cannot derive folder from {feature_path} "
            "(feature is directly under features/); pass --folder"
        )
    return _normalize_folder("/" + "/".join(dirs))


def _expand_glob_path(text: str) -> list[Path]:
    """Resolve a glob string into .feature files (and directories' recursive features)."""
    found: list[Path] = []
    matches = sorted(Path().glob(text))
    if not matches:
        matches = sorted(Path(".").glob(text))
    for match in matches:
        if match.is_file() and match.suffix == ".feature":
            found.append(match.resolve())
        elif match.is_dir():
            found.extend(sorted(match.rglob("*.feature")))
    return found


def _expand_concrete_path(path: Path) -> list[Path]:
    """Resolve an existing file or directory into .feature paths."""
    if not path.exists():
        raise SystemExit(f"Path not found: {path}")
    if path.is_file():
        if path.suffix != ".feature":
            raise SystemExit(f"Not a .feature file: {path}")
        return [path.resolve()]
    if path.is_dir():
        return sorted(path.rglob("*.feature"))
    raise SystemExit(f"Unsupported path: {path}")


def _discover_feature_files(paths: list[Path]) -> list[Path]:
    """Expand files, directories (recursive), and glob patterns to .feature paths."""
    found: list[Path] = []
    for raw in paths:
        text = str(raw)
        if any(ch in text for ch in "*?[]"):
            found.extend(_expand_glob_path(text))
            continue
        found.extend(_expand_concrete_path(raw.expanduser()))
    uniq = sorted({p.resolve() for p in found})
    if not uniq:
        raise SystemExit("No .feature files found")
    return uniq


def _write_scenario_tags(lines: list[str], scenario: ScenarioBlock, tags: list[str]) -> None:
    """Write tags above the scenario; insert a new tag line if the scenario had none."""
    new_line = scenario.tag_indent + " ".join(f"@{t}" for t in tags)
    if scenario.tag_line_count == 0:
        # Bottom-up create order keeps earlier scenario_line_index values valid.
        lines.insert(scenario.scenario_line_index, new_line)
        return
    lines[scenario.tag_line_index] = new_line
    for offset in range(1, scenario.tag_line_count):
        lines[scenario.tag_line_index + offset] = ""


def _select_sync_targets(
    scenarios: list[ScenarioBlock],
    *,
    do_create: bool,
    do_update: bool,
    only_key: str | None,
    feature_bulk: bool,
) -> tuple[list[ScenarioBlock], list[ScenarioBlock]]:
    """Return (to_create, to_update) scenario lists for this sync run."""
    to_create: list[ScenarioBlock] = []
    if do_create:
        for scenario in scenarios:
            if scenario.zephyr_key:
                continue
            if scenario.wants_create or feature_bulk:
                to_create.append(scenario)
    to_update = [s for s in scenarios if s.zephyr_key and s.steps] if do_update else []
    if only_key:
        to_create = []  # --key is for updating an existing case
        to_update = [s for s in to_update if s.zephyr_key == only_key]
    return to_create, to_update


def _handle_empty_sync(
    feature_path: Path,
    lines: list[str],
    *,
    feature_bulk: bool,
    do_create: bool,
    do_update: bool,
    only_key: str | None,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Handle the nothing-to-do path; return (0, 0, 0) counts."""
    # Orphan Feature @zephyr while every scenario is already keyed — just clean up.
    if feature_bulk and do_create and not only_key and not dry_run:
        if _strip_zephyr_from_feature_tags(lines):
            print(f"Nothing to create in {feature_path}")
            print("  removed orphan @zephyr from Feature tags")
            feature_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return 0, 0, 0
    if only_key:
        print(f"  (no @{only_key} in this file)")
    else:
        print(f"Nothing to do in {feature_path}")
        if do_create and not do_update:
            print("  (no Feature @zephyr / scenario @zephyr without a PROJECT-T key)")
        if do_update and not do_create:
            print("  (no scenarios with @PROJECT-T####)")
    return 0, 0, 0


def _scenario_meta(
    scenario: ScenarioBlock,
    *,
    feature_tags: list[str],
    path_labels: list[str],
    extra_labels: list[str] | None,
) -> tuple[list[str], str, list[str]]:
    """Return (labels, priority, issue_keys) for a scenario."""
    labels = _labels_for(
        scenario.tags,
        feature_tags=feature_tags,
        path_labels=path_labels,
        extra=extra_labels,
    )
    # Scenario severity wins; fall back to Feature-level severity.
    if any(t.lower() in _PRIORITY_BY_SEVERITY for t in scenario.tags):
        priority = _priority_for(scenario.tags)
    else:
        priority = _priority_for(feature_tags)
    issues = list(dict.fromkeys([*_issue_keys(feature_tags), *scenario.issue_keys]))
    branch_issue = branch_issue_key()
    if branch_issue and branch_issue not in issues:
        issues.append(branch_issue)
    return labels, priority, issues


def _print_dry_run(
    to_create: list[ScenarioBlock],
    to_update: list[ScenarioBlock],
    *,
    feature_bulk: bool,
    folder: str,
    feature_tags: list[str],
    path_labels: list[str],
    extra_labels: list[str] | None,
    project_key: str,
    status: str,
    precondition: str,
) -> tuple[int, int, int]:
    """Print planned creates/updates without calling Zephyr."""
    if feature_bulk and to_create:
        print(
            f"Feature @zephyr → bulk CREATE {len(to_create)} unkeyed "
            f"scenario(s) in project {project_key}; "
            f"will remove Feature @zephyr after create"
        )
    for scenario in to_create:
        labels, priority, issues = _scenario_meta(
            scenario,
            feature_tags=feature_tags,
            path_labels=path_labels,
            extra_labels=extra_labels,
        )
        print(f"CREATE: {scenario.name!r}")
        print(
            f"  project={project_key!r} folder={folder!r} "
            f"status={status!r} priority={priority!r} "
            f"labels={labels!r} issueLinks={issues!r} "
            f"steps={len(scenario.steps)}"
        )
        print(f"  precondition={precondition!r}")
        for step in scenario.steps:
            print(f"    {step}")
    for scenario in to_update:
        labels, priority, issues = _scenario_meta(
            scenario,
            feature_tags=feature_tags,
            path_labels=path_labels,
            extra_labels=extra_labels,
        )
        print(f"UPDATE?: {scenario.zephyr_key} ← {scenario.name!r}")
        print(f"  status={status!r} priority={priority!r} labels={labels!r} issueLinks={issues!r}")
        print("  (real run GETs Zephyr and skips PUT if name/steps/folder/priority/labels match)")
        for step in scenario.steps:
            print(f"    {step}")
    return len(to_create), len(to_update), 0


def _create_scenarios(
    client: httpx.Client,
    lines: list[str],
    to_create: list[ScenarioBlock],
    *,
    folder: str,
    feature_tags: list[str],
    path_labels: list[str],
    extra_labels: list[str] | None,
    project_key: str,
    status: str,
    precondition: str,
) -> int:
    """POST new Zephyr cases and write ``@PROJECT-T####`` tags into ``lines``."""
    created = 0
    # Bottom-up so inserting tag lines does not shift later indices.
    for scenario in sorted(to_create, key=lambda s: s.scenario_line_index, reverse=True):
        labels, priority, issues = _scenario_meta(
            scenario,
            feature_tags=feature_tags,
            path_labels=path_labels,
            extra_labels=extra_labels,
        )
        print(f"CREATE: {scenario.name!r}")
        key = _create_testcase(
            client,
            name=scenario.name,
            steps=scenario.steps,
            folder=folder,
            labels=labels,
            priority=priority,
            project_key=project_key,
            status=status,
            precondition=precondition,
            issue_keys=issues or None,
        )
        if issues:
            # Ensure links even when create omitted/rejected issueLinks.
            _link_issues(client, key, issues)
        new_tags = _insert_key_tag(scenario.tags, key)
        _write_scenario_tags(lines, scenario, new_tags)
        print(f"  created {key} → wrote tag into feature")
        created += 1
    return created


def _update_scenarios(
    client: httpx.Client,
    to_update: list[ScenarioBlock],
    *,
    folder: str,
    force: bool,
    feature_tags: list[str],
    path_labels: list[str],
    extra_labels: list[str] | None,
    status: str,
    precondition: str,
) -> tuple[int, int]:
    """PUT changed Zephyr cases; return (updated, skipped_unchanged)."""
    updated = 0
    skipped = 0
    for scenario in to_update:
        key = scenario.zephyr_key
        assert key is not None
        labels, priority, issues = _scenario_meta(
            scenario,
            feature_tags=feature_tags,
            path_labels=path_labels,
            extra_labels=extra_labels,
        )
        remote = _get_testcase(client, key)
        if not force and _remote_matches(
            remote,
            name=scenario.name,
            script_text=scenario.script_text,
            folder=folder,
            priority=priority,
            labels=labels,
        ):
            if issues:
                _link_issues(client, key, issues)
            print(f"SKIP: {key} (already matches BDD)")
            skipped += 1
            continue
        print(f"UPDATE: {key} ← {scenario.name!r}")
        _put_testcase(
            client,
            key=key,
            remote=remote,
            name=scenario.name,
            steps=scenario.steps,
            folder=folder,
            labels=labels,
            priority=priority,
            status=status,
            precondition=precondition,
            issue_keys=issues or None,
        )
        if issues:
            _link_issues(client, key, issues)
        print(f"  updated {key} in Zephyr")
        updated += 1
    return updated, skipped


def sync_feature(
    feature_path: Path,
    *,
    folder: str,
    dry_run: bool,
    do_create: bool,
    do_update: bool,
    only_key: str | None,
    force: bool,
    extra_labels: list[str] | None = None,
    project_key: str = _DEFAULT_PROJECT,
    status: str = _DEFAULT_STATUS,
    precondition: str = _DEFAULT_PRECONDITION,
) -> tuple[int, int, int]:
    """Sync one feature file to Zephyr.

    Returns:
        ``(created, updated, skipped_unchanged)`` counts.
    """
    text = feature_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    feature_tags = _parse_feature_tags(lines)
    path_labels = _path_labels(feature_path)
    scenarios = _parse_scenarios(text)
    feature_bulk = _feature_wants_create(feature_tags)
    project_key = project_key.strip().upper() or _DEFAULT_PROJECT

    to_create, to_update = _select_sync_targets(
        scenarios,
        do_create=do_create,
        do_update=do_update,
        only_key=only_key,
        feature_bulk=feature_bulk,
    )

    if not to_create and not to_update:
        result = _handle_empty_sync(
            feature_path,
            lines,
            feature_bulk=feature_bulk,
            do_create=do_create,
            do_update=do_update,
            only_key=only_key,
            dry_run=dry_run,
        )
        return result

    if dry_run:
        return _print_dry_run(
            to_create,
            to_update,
            feature_bulk=feature_bulk,
            folder=folder,
            feature_tags=feature_tags,
            path_labels=path_labels,
            extra_labels=extra_labels,
            project_key=project_key,
            status=status,
            precondition=precondition,
        )

    token = _env("JIRA_TOKEN")
    atm = _env("JIRA_ATM").rstrip("/")
    with httpx.Client(
        base_url=atm,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    ) as client:
        created = _create_scenarios(
            client,
            lines,
            to_create,
            folder=folder,
            feature_tags=feature_tags,
            path_labels=path_labels,
            extra_labels=extra_labels,
            project_key=project_key,
            status=status,
            precondition=precondition,
        )
        updated, skipped = _update_scenarios(
            client,
            to_update,
            folder=folder,
            force=force,
            feature_tags=feature_tags,
            path_labels=path_labels,
            extra_labels=extra_labels,
            status=status,
            precondition=precondition,
        )

    wrote = bool(created)
    if feature_bulk and do_create and not only_key:
        # After bulk create (or if every scenario was already keyed), drop Feature @zephyr.
        if _strip_zephyr_from_feature_tags(lines):
            print("  removed @zephyr from Feature tags")
            wrote = True
    if wrote:
        feature_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return created, updated, skipped


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for creating/updating Zephyr cases from feature files."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--feature",
        type=Path,
        default=None,
        help="Path to a single .feature file",
    )
    parser.add_argument(
        "--features",
        action="append",
        default=[],
        metavar="PATH",
        help="Directory (recursive *.feature), glob, or file; repeatable",
    )
    parser.add_argument(
        "--folder",
        default=None,
        help="Force the same Zephyr folder for every file "
        "(default: derive from path under features/, e.g. bill/tci → /bill/tci)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print only; do not call Jira or write the file",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create scenarios tagged @zephyr (default if neither flag is set)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update scenarios that already have @PROJECT-T####",
    )
    parser.add_argument(
        "--key",
        default=None,
        help="With --update: only this PROJECT-T#### case (searches all files)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --update: PUT even when remote already matches",
    )
    parser.add_argument(
        "--label",
        action="append",
        default=[],
        help="Extra Zephyr label (repeatable), e.g. --label branch:feat/bill-management",
    )
    parser.add_argument(
        "--project",
        default=_DEFAULT_PROJECT,
        help="Zephyr/Jira project key for create (default: ALPHA). Use KYC for KYC cases.",
    )
    parser.add_argument(
        "--status",
        default=_DEFAULT_STATUS,
        help="Zephyr test-case status on create/update (default: Draft)",
    )
    parser.add_argument(
        "--precondition",
        default=_DEFAULT_PRECONDITION,
        help="Zephyr Details → Precondition text",
    )
    args = parser.parse_args(argv)

    loaded = load_jira_local_env(start=Path(__file__))
    if loaded and not args.dry_run:
        print(f"Using local Jira env file: {loaded}")

    if args.feature is None and not args.features:
        raise SystemExit("Pass --feature FILE and/or --features DIR|GLOB")

    paths: list[Path] = []
    if args.feature is not None:
        paths.append(args.feature)
    paths.extend(Path(p) for p in args.features)
    feature_files = _discover_feature_files(paths)

    only_key = _normalize_key(args.key) if args.key else None

    # Default: create-only. --key alone implies --update.
    if only_key and not args.create and not args.update:
        do_create, do_update = False, True
    elif not args.create and not args.update:
        do_create, do_update = True, False
    else:
        do_create, do_update = args.create, args.update

    if only_key and not do_update:
        raise SystemExit("--key requires --update (or pass --key alone)")

    total_c = total_u = total_s = 0
    print(f"Scanning {len(feature_files)} feature file(s)…")
    for feature_path in feature_files:
        folder = (
            _normalize_folder(args.folder)
            if args.folder
            else _folder_from_feature_path(feature_path)
        )
        print(f"\n=== {feature_path} → folder {folder} ===")
        branch_issue = branch_issue_key()
        if branch_issue:
            print(f"  branch issue link: {branch_issue}")
        created, updated, skipped = sync_feature(
            feature_path,
            folder=folder,
            dry_run=args.dry_run,
            do_create=do_create,
            do_update=do_update,
            only_key=only_key,
            force=args.force,
            extra_labels=args.label,
            project_key=args.project,
            status=args.status,
            precondition=args.precondition,
        )
        total_c += created
        total_u += updated
        total_s += skipped

    if only_key and total_u == 0 and total_s == 0:
        raise SystemExit(f"No scenario with @{only_key} in scanned feature files")

    print(f"\nAll done. Created {total_c}, updated {total_u}, skipped unchanged {total_s}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
