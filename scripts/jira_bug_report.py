#!/usr/bin/env python3
r"""File a standard-format Bug on Platform Jira, optionally linked to a ticket.

Manual tool only — never wired into pytest/CI. Call it explicitly after you
(or an agent) have confirmed something is actually a bug.

Env (same file as Zephyr sync — see scripts/jira_local_env.py):
  secrets/jira_atm.env   ← copy from secrets/jira_atm.example.env (gitignored)
  # or:
  export JIRA_TOKEN=...
  export JIRA_ATM=https://jira.demo-platform.net/rest/atm/1.0

The standard Jira REST API (/rest/api/2) is derived from JIRA_ATM the same way
tests/zephyr_result_collector.py does it — no extra secret needed.

Reporter is never asked for: it is resolved from the current JIRA_TOKEN via
GET /myself, same "never hardcode a person" rule as Zephyr result push.

Linked to a ticket (Jira issue or Zephyr test case — auto-detected):
  PYTHONPATH=. python scripts/jira_bug_report.py \\
    --ticket ALPHA-T2233 --summary "Operator list empty after filter reset" \\
    --step "Open Internet > Operators" \\
    --step "Apply any operator filter" \\
    --step "Clear the filter" \\
    --expected "Full operator list reappears" \\
    --actual "List stays empty until page reload" \\
    --severity High --dry-run

No ticket to link — files straight into the project backlog (--project is
then required; there is no guessed default):
  PYTHONPATH=. python scripts/jira_bug_report.py \\
    --project ALPHA --summary "..." --step "..." \\
    --expected "..." --actual "..." --severity Medium --dry-run

Drop --dry-run to create for real. Jira Priority values and any custom fields
(e.g. a dedicated Severity field, if this project has one) are instance-
specific — never guessed. Check first:
  PYTHONPATH=. python scripts/jira_bug_report.py --discover-priorities
  PYTHONPATH=. python scripts/jira_bug_report.py --discover-fields --project ALPHA

--auto-fill derives summary/steps/expected/actual/severity/environment from a
real Allure result instead of typing them by hand — run the test, see it
fail, then:
  PYTHONPATH=. python scripts/jira_bug_report.py \\
    --ticket ALPHA-T2232 --auto-fill --dry-run
--ticket must be the scenario's own @PROJECT-T#### tag (used both to find the
Allure result and as the link target). Any --summary/--step/--expected/
--actual/--severity/--environment passed explicitly still wins over the
auto-filled value.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from jira_branch import branch_issue_key  # noqa: E402
from jira_local_env import load_jira_local_env  # noqa: E402
from zephyr_sync import _get_testcase as _zephyr_get_testcase  # noqa: E402
from zephyr_sync import _sanitize_testcase_put as _zephyr_sanitize_testcase_put  # noqa: E402

_ZEPHYR_T_TAG = re.compile(r"^([A-Z][A-Z0-9]+)-T(\d+)$", re.IGNORECASE)
_ISSUE_KEY = re.compile(r"^([A-Z][A-Z0-9]+)-\d+$", re.IGNORECASE)
_SCENARIO_LINE = re.compile(r"^\s*Scenario(?: Outline)?:\s*(.+?)\s*$")
_TAG_LINE = re.compile(r"^\s*@\S+(?:\s+@\S+)*\s*$")
_THEN_STEP = re.compile(r"^then\b", re.IGNORECASE)
_DEFAULT_ENVIRONMENT = "Platform UAT"
_DEFAULT_PRIORITY = "Medium"
_DEFAULT_ISSUETYPE = "Bug"
_DEFAULT_LINK_TYPE = "Relates"
_DEFAULT_RESULTS_DIR = Path("allure-results")
_DEFAULT_FEATURES_ROOT = Path("tests/bdd/features")
_DEFAULT_MAX_ATTACHMENTS = 5
_ALLURE_SEVERITY_TO_BUG_SEVERITY = {
    "blocker": "Blocker",
    "critical": "High",
    "normal": "Medium",
    "minor": "Low",
    "trivial": "Trivial",
}


def _env(name: str) -> str:
    """Read a required env var or exit with a setup hint."""
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(
            f"Missing {name}. Set it in the shell or create "
            f"secrets/jira_atm.env (see secrets/jira_atm.example.env)."
        )
    return value


def _jira_rest_base(atm: str) -> str:
    """Derive the standard /rest/api/2 base from the ATM base URL."""
    if "/rest/atm/" in atm:
        return f"{atm.split('/rest/atm/')[0]}/rest/api/2"
    return f"{atm.rsplit('/rest/', 1)[0]}/rest/api/2"


def _jira_host(jira_rest: str) -> str:
    """Return the bare Jira host for building /browse/KEY links."""
    return jira_rest.split("/rest/")[0]


def is_zephyr_test_key(ticket: str) -> bool:
    """True for a Zephyr test-case key (ALPHA-T2233), false for a Jira issue key."""
    return bool(_ZEPHYR_T_TAG.match(ticket))


def normalize_ticket(raw: str) -> str:
    """Uppercase and validate a ticket key (Jira issue or Zephyr test case)."""
    key = raw.strip().lstrip("@")
    zephyr_match = _ZEPHYR_T_TAG.match(key)
    if zephyr_match:
        return f"{zephyr_match.group(1).upper()}-T{zephyr_match.group(2)}"
    if _ISSUE_KEY.match(key):
        return key.upper()
    raise SystemExit(
        f"Invalid --ticket {raw!r}; expected PROJECT-#### (Jira issue) "
        "or PROJECT-T#### (Zephyr test case)"
    )


def project_from_ticket(ticket: str) -> str:
    """Extract the project prefix from a normalized ticket key."""
    match = re.match(r"^([A-Z][A-Z0-9]+)-", ticket)
    if not match:
        raise SystemExit(f"Cannot derive project from {ticket!r}; pass --project")
    return match.group(1)


def find_tagged_scenario(features_root: Path, key: str) -> tuple[Path, str]:
    """Locate the .feature file + scenario name carrying scenario-level ``@key``."""
    target = key.upper()
    for feature_path in sorted(features_root.rglob("*.feature")):
        pending_tags: list[str] = []
        for line in feature_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if _TAG_LINE.match(stripped):
                pending_tags.extend(tag[1:].upper() for tag in stripped.split())
                continue
            scenario_match = _SCENARIO_LINE.match(line)
            if scenario_match:
                if target in pending_tags:
                    return feature_path, scenario_match.group(1)
                pending_tags = []
    raise SystemExit(f"No scenario tagged @{key} found under {features_root}")


def find_failed_allure_result(results_dir: Path, scenario_name: str) -> dict[str, Any]:
    """Return the most recent failed/broken Allure result for this scenario name."""
    candidates: list[tuple[float, dict[str, Any]]] = []
    for path in results_dir.glob("*-result.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("status") not in ("failed", "broken"):
            continue
        if data.get("name") != scenario_name:
            continue
        candidates.append((path.stat().st_mtime, data))
    if not candidates:
        raise SystemExit(
            f"No failed/broken Allure result for scenario {scenario_name!r} in {results_dir} "
            "— run the test first, or check --results-dir"
        )
    candidates.sort(key=lambda pair: pair[0])
    return candidates[-1][1]


def split_steps_and_expected(steps: list[dict[str, Any]]) -> tuple[list[str], str]:
    """Split Allure's executed Gherkin steps into repro steps + the Then/And expectation."""
    repro: list[str] = []
    expected: list[str] = []
    in_expected = False
    for step in steps:
        name = str(step.get("name") or "").strip()
        if not name:
            continue
        if _THEN_STEP.match(name):
            in_expected = True
        (expected if in_expected else repro).append(name)
    if not expected and repro:
        expected.append(repro.pop())
    return repro, "\n".join(expected)


def severity_from_allure(result: dict[str, Any]) -> str | None:
    """Map the Allure ``severity`` label back to a bug Severity, if present."""
    for label in result.get("labels") or []:
        if label.get("name") == "severity":
            return _ALLURE_SEVERITY_TO_BUG_SEVERITY.get(str(label.get("value") or "").lower())
    return None


def failed_step_name(result: dict[str, Any]) -> str | None:
    """Name of the first non-passed Gherkin step, for the auto-fill Notes."""
    for step in result.get("steps") or []:
        if step.get("status") != "passed":
            return str(step.get("name") or "").strip() or None
    return None


def actual_result_from_allure(result: dict[str, Any]) -> str:
    """Render the Allure failure message/trace as the Actual Result (masked upstream)."""
    details = result.get("statusDetails") or {}
    text = str(details.get("message") or "").strip() or str(details.get("trace") or "").strip()
    if not text:
        return f"Test status: {result.get('status')} (no failure message captured by Allure)"
    return f"{{noformat}}\n{text[:4000]}\n{{noformat}}"


def attachments_from_allure(
    result: dict[str, Any], results_dir: Path, max_attachments: int
) -> list[Path]:
    """Local paths of this result's Allure attachments (screenshots, dumps), capped."""
    paths: list[Path] = []
    for entry in (result.get("attachments") or [])[:max_attachments]:
        source = entry.get("source")
        if not source:
            continue
        path = results_dir / source
        if path.is_file():
            paths.append(path)
    return paths


def environment_from_properties(results_dir: Path) -> str | None:
    """Render allure-results/environment.properties as the Environment field."""
    path = results_dir / "environment.properties"
    if not path.is_file():
        return None
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return "\n".join(lines) if lines else None


def apply_auto_fill(args: argparse.Namespace) -> None:
    """Populate missing bug fields from the matching Allure result — mutates ``args``."""
    if not args.auto_fill:
        return
    if not args.ticket:
        raise SystemExit("--auto-fill requires --ticket (a Zephyr test-case key)")
    key = normalize_ticket(args.ticket)
    if not is_zephyr_test_key(key):
        raise SystemExit(
            f"--auto-fill requires --ticket to be a Zephyr test-case key (PROJECT-T####), got {key!r}"
        )
    feature_path, scenario_name = find_tagged_scenario(args.features_root, key)
    result = find_failed_allure_result(args.results_dir, scenario_name)
    repro, expected = split_steps_and_expected(result.get("steps") or [])
    feature_label = next(
        (lbl.get("value") for lbl in result.get("labels") or [] if lbl.get("name") == "feature"),
        None,
    )
    failed_step = failed_step_name(result)
    notes_bits = [f"Auto-filed from Allure result for {key} (status={result.get('status')})."]
    if failed_step:
        notes_bits.append(f"Failed step: {failed_step}.")
    notes_bits.append(f"Source feature: {feature_path}.")

    args.summary = args.summary or (
        f"{feature_label}: {scenario_name}" if feature_label else scenario_name
    )
    args.steps = args.steps or repro
    args.expected = args.expected or expected
    args.actual = args.actual or actual_result_from_allure(result)
    args.severity = args.severity or severity_from_allure(result)
    args.notes = args.notes or " ".join(notes_bits)
    args.environment = args.environment or environment_from_properties(args.results_dir)
    if not args.attachments:
        args.attachments = attachments_from_allure(result, args.results_dir, args.max_attachments)
    if not args.severity:
        raise SystemExit(
            "Could not auto-derive --severity from Allure (no severity label on this result); "
            "pass --severity explicitly"
        )
    print(
        f"jira_bug_report: auto-filled from {feature_path} + Allure result (status={result.get('status')})"
    )


def current_user_reporter_field(client: httpx.Client) -> dict[str, str]:
    """Resolve {reporter} for the token owner via GET /myself — never hardcode a person."""
    response = client.get("/myself")
    if response.status_code != 200:
        raise SystemExit(
            f"GET /myself failed HTTP {response.status_code}: {response.text[:500]} "
            "(cannot resolve Reporter for this token)"
        )
    body = response.json()
    username = str(body.get("name") or "").strip()
    key = str(body.get("key") or "").strip()
    display = str(body.get("displayName") or "").strip()
    if not username and not key:
        raise SystemExit(f"GET /myself returned no name/key to use as Reporter: {body!r}")
    if display:
        print(f"jira_bug_report: reporter will be {display}")
    return {"name": username} if username else {"key": key}


def build_description(
    *,
    steps: list[str],
    expected: str,
    actual: str,
    environment: str,
    severity: str,
    notes: str,
    ticket: str | None,
    branch_ticket: str,
) -> str:
    """Render the standard bug-report body (Jira wiki markup, /rest/api/2 style)."""
    lines = ["h3. Steps to Reproduce"]
    lines.extend(f"# {step}" for step in steps)
    lines += [
        "",
        "h3. Expected Result",
        expected,
        "",
        "h3. Actual Result",
        actual,
        "",
        "h3. Environment",
        environment,
        "",
        "h3. Severity",
        severity,
    ]
    if notes:
        lines += ["", "h3. Additional Notes", notes]
    footer = "_Filed via scripts/jira_bug_report.py"
    if ticket:
        footer += f" — linked to {ticket}"
        if branch_ticket and branch_ticket != ticket:
            footer += f", branch ticket {branch_ticket}"
    else:
        footer += " — filed to backlog, no linked ticket"
    footer += "_"
    lines += ["", "----", footer]
    return "\n".join(lines)


def create_bug(
    client: httpx.Client,
    *,
    project: str,
    issuetype: str,
    summary: str,
    description: str,
    environment: str,
    severity: str,
    priority: str,
    labels: list[str],
    components: list[str],
    reporter: dict[str, str],
    severity_field: str | None = None,
    severity_field_value: str | None = None,
) -> str:
    """POST a new Bug issue; return its key."""
    fields: dict[str, Any] = {
        "project": {"key": project},
        "issuetype": {"name": issuetype},
        "summary": summary,
        "description": description,
        "environment": environment,
        "priority": {"name": priority},
        "labels": [*labels, f"severity-{severity.lower()}"],
        "reporter": reporter,
    }
    if components:
        fields["components"] = [{"name": name} for name in components]
    if severity_field and severity_field_value:
        fields[severity_field] = {"value": severity_field_value}
    response = client.post("/issue", json={"fields": fields})
    if response.status_code == 400:
        response = _retry_create_without_unscreened_fields(client, fields, response)
    if response.status_code not in (200, 201):
        raise SystemExit(f"Create failed HTTP {response.status_code}: {response.text[:800]}")
    body = response.json()
    key = body.get("key")
    if not key:
        raise SystemExit(f"Create response missing key: {body!r}")
    return str(key)


def _retry_create_without_unscreened_fields(
    client: httpx.Client, fields: dict[str, Any], response: httpx.Response
) -> httpx.Response:
    """Drop fields Jira rejects as not-on-this-screen and retry once.

    E.g. no Environment field on this project's Create Bug screen — the content still
    lives in the description, so nothing is lost. Never drops project/issuetype/summary/reporter.
    """
    try:
        errors = response.json().get("errors") or {}
    except ValueError:
        return response
    protected = {"project", "issuetype", "summary", "reporter"}
    droppable = [key for key in errors if key in fields and key not in protected]
    if not droppable:
        return response
    print(f"  create rejected {droppable} (not on this project's screen) — retrying without them")
    retry_fields = {k: v for k, v in fields.items() if k not in droppable}
    return client.post("/issue", json={"fields": retry_fields})


def link_issue_to_issue(
    client: httpx.Client, *, from_key: str, to_key: str, link_type: str
) -> bool:
    """Best-effort standard Jira issue link between two real Jira issues."""
    payload = {
        "type": {"name": link_type},
        "inwardIssue": {"key": from_key},
        "outwardIssue": {"key": to_key},
    }
    response = client.post("/issueLink", json=payload)
    if response.status_code in (200, 201):
        print(f"  linked {from_key} --[{link_type}]--> {to_key}")
        return True
    print(
        f"  warning: could not link {from_key} to {to_key} "
        f"(HTTP {response.status_code}: {response.text[:300]}); link manually in Jira"
    )
    return False


def link_bug_to_testcase(atm_client: httpx.Client, *, testcase_key: str, bug_key: str) -> bool:
    """Attach the new Bug to a Zephyr test case — same fallback chain zephyr_sync.py uses.

    This ATM instance's ``POST /testcase/{key}/issueLinks`` 404s outright, so the reliable
    path is GET the test case, sanitize it, and PUT it back with ``issueLinks`` added.
    """
    attempts = [
        (f"/testcase/{testcase_key}/issueLinks", {"issueKeys": [bug_key]}),
        (f"/testcase/{testcase_key}/issueLinks", [bug_key]),
        ("/testcase/link-issues", {"testCaseKey": testcase_key, "issueKeys": [bug_key]}),
    ]
    for path, payload in attempts:
        response = atm_client.post(path, json=payload)
        if response.status_code in (200, 201, 204):
            print(f"  linked {bug_key} -> {testcase_key} (Zephyr test case)")
            return True

    remote = _zephyr_get_testcase(atm_client, testcase_key)
    body = _zephyr_sanitize_testcase_put(remote)
    existing = [str(x) for x in (remote.get("issueLinks") or [])]
    body["issueLinks"] = [*existing, bug_key]
    response = atm_client.put(f"/testcase/{testcase_key}", json=body)
    if response.status_code in (200, 201):
        print(f"  linked {bug_key} -> {testcase_key} (Zephyr test case, via PUT)")
        return True
    print(
        f"  warning: could not link {bug_key} to {testcase_key} "
        f"(last HTTP {response.status_code}); link manually in Zephyr UI"
    )
    return False


def attach_files(client: httpx.Client, *, key: str, paths: list[Path]) -> None:
    """Upload local files (screenshots, traces) onto the created issue."""
    for path in paths:
        if not path.is_file():
            print(f"  warning: attachment not found, skipping: {path}")
            continue
        with path.open("rb") as handle:
            response = client.post(
                f"/issue/{key}/attachments",
                headers={"X-Atlassian-Token": "no-check"},
                files={"file": (path.name, handle)},
            )
        if response.status_code in (200, 201):
            print(f"  attached {path.name}")
        else:
            print(f"  warning: attach {path.name} failed HTTP {response.status_code}")


def discover_priorities(client: httpx.Client) -> None:
    """Print the Jira instance's real Priority names (verify before --priority)."""
    response = client.get("/priority")
    if response.status_code != 200:
        raise SystemExit(f"GET /priority failed HTTP {response.status_code}: {response.text[:500]}")
    for entry in response.json():
        print(f"  {entry.get('name')}")


def _find_sample_issue(client: httpx.Client, *, project: str, issuetype: str) -> str:
    """Find one existing issue of this project/issuetype, for editmeta discovery."""
    response = client.get(
        "/search",
        params={
            "jql": f'project={project} AND issuetype="{issuetype}"',
            "maxResults": 1,
            "fields": "key",
        },
    )
    if response.status_code != 200:
        raise SystemExit(f"GET /search failed HTTP {response.status_code}: {response.text[:500]}")
    issues = response.json().get("issues") or []
    if not issues:
        raise SystemExit(f"No existing {issuetype} in project {project} to discover fields from")
    return str(issues[0]["key"])


def discover_fields(client: httpx.Client, *, project: str, issuetype: str) -> None:
    """Print required fields (incl. any custom Severity field) via editmeta on a sample issue.

    The classic ``/issue/createmeta`` endpoint is deprecated/unreliable on modern Jira Data
    Center — editmeta on a real issue is the dependable source of ``allowedValues``.
    """
    sample_key = _find_sample_issue(client, project=project, issuetype=issuetype)
    response = client.get(f"/issue/{sample_key}/editmeta")
    if response.status_code != 200:
        raise SystemExit(
            f"GET /issue/{sample_key}/editmeta failed HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )
    print(f"  (discovered from existing issue {sample_key})")
    fields = response.json().get("fields") or {}
    for field_id, meta in fields.items():
        allowed = meta.get("allowedValues")
        hint = f" allowed={[a.get('name') or a.get('value') for a in allowed]}" if allowed else ""
        required = " required" if meta.get("required") else ""
        print(f"  {field_id}: {meta.get('name')}{required}{hint}")


def _print_dry_run(
    *,
    ticket: str | None,
    project: str,
    issuetype: str,
    summary: str,
    description: str,
    environment: str,
    severity: str,
    priority: str,
    labels: list[str],
    components: list[str],
    attachments: list[Path],
    link_type: str,
    branch_ticket: str,
) -> None:
    print("DRY RUN — nothing sent to Jira (reporter/myself not queried either)")
    print(
        f"  project={project!r} issuetype={issuetype!r} priority={priority!r} severity={severity!r}"
    )
    print(f"  summary={summary!r}")
    print(f"  labels={[*labels, f'severity-{severity.lower()}']!r} components={components!r}")
    print(f"  environment={environment!r}")
    if ticket:
        print(
            f"  link target={ticket!r} (zephyr_test_case={is_zephyr_test_key(ticket)}) "
            f"type={link_type!r}"
        )
        if branch_ticket and branch_ticket != ticket:
            print(f"  also link branch ticket={branch_ticket!r}")
    else:
        print("  no --ticket given → files to backlog, no issue link")
    if attachments:
        print(f"  attachments={[str(p) for p in attachments]!r}")
    print("  --- description ---")
    print(description)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ticket",
        default=None,
        help="Jira issue key or Zephyr test-case key to link the bug to (omit to file to backlog)",
    )
    parser.add_argument("--summary", help="Short bug title")
    parser.add_argument(
        "--step",
        action="append",
        default=[],
        dest="steps",
        help="One reproduction step (repeatable, in order)",
    )
    parser.add_argument("--expected", help="Expected result")
    parser.add_argument("--actual", help="Actual result observed")
    parser.add_argument(
        "--severity",
        choices=["Blocker", "Critical", "High", "Medium", "Low", "Trivial"],
        help="Required. Blocker / Critical / High / Medium / Low / Trivial",
    )
    parser.add_argument(
        "--environment",
        default=None,
        help=f"Where it was observed (default: {_DEFAULT_ENVIRONMENT!r}, or Allure's "
        "environment.properties with --auto-fill)",
    )
    parser.add_argument("--notes", default="", help="Optional extra context")
    parser.add_argument(
        "--priority", default=_DEFAULT_PRIORITY, help="Real Jira Priority name for this instance"
    )
    parser.add_argument(
        "--severity-field",
        default=None,
        metavar="customfield_NNNNN",
        help="This project's dedicated Severity custom field id, if it has one "
        "(check with --discover-fields; required together with --severity-field-value)",
    )
    parser.add_argument(
        "--severity-field-value",
        default=None,
        help="The exact allowedValues option to set on --severity-field (from --discover-fields — "
        "this project's custom Severity field vocabulary may not match --severity's)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Jira project key. Derived from --ticket when given; required otherwise",
    )
    parser.add_argument(
        "--issuetype", default=_DEFAULT_ISSUETYPE, help="Jira issue type name (default: Bug)"
    )
    parser.add_argument(
        "--label", action="append", default=[], dest="labels", help="Extra label (repeatable)"
    )
    parser.add_argument(
        "--component",
        action="append",
        default=[],
        dest="components",
        help="Component name (repeatable)",
    )
    parser.add_argument(
        "--attach",
        action="append",
        default=[],
        dest="attachments",
        type=Path,
        help="File to attach (repeatable)",
    )
    parser.add_argument(
        "--link-type",
        default=_DEFAULT_LINK_TYPE,
        help="Jira issue-link type name (default: Relates)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the payload only; no Jira call"
    )
    parser.add_argument(
        "--discover-priorities", action="store_true", help="Print real Priority names, then exit"
    )
    parser.add_argument(
        "--discover-fields",
        action="store_true",
        help="Print createmeta fields for --project, then exit",
    )
    parser.add_argument(
        "--auto-fill",
        action="store_true",
        help="Derive summary/steps/expected/actual/severity/environment from the Allure result "
        "matching --ticket (must be a Zephyr test-case key). Explicit flags still win.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=_DEFAULT_RESULTS_DIR,
        help=f"Allure results directory for --auto-fill (default: {_DEFAULT_RESULTS_DIR})",
    )
    parser.add_argument(
        "--features-root",
        type=Path,
        default=_DEFAULT_FEATURES_ROOT,
        help=f"Root to search for the @PROJECT-T#### tag with --auto-fill (default: {_DEFAULT_FEATURES_ROOT})",
    )
    parser.add_argument(
        "--max-attachments",
        type=int,
        default=_DEFAULT_MAX_ATTACHMENTS,
        help=f"Cap on Allure attachments auto-attached with --auto-fill (default: {_DEFAULT_MAX_ATTACHMENTS})",
    )
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    """Exit with a clear message if required fields are missing for this mode."""
    if args.discover_fields and not args.project:
        raise SystemExit("--discover-fields requires --project")
    if args.discover_priorities or args.discover_fields:
        return
    missing = [
        name
        for name, value in (
            ("--summary", args.summary),
            ("--expected", args.expected),
            ("--actual", args.actual),
            ("--severity", args.severity),
        )
        if not value
    ]
    if not args.steps:
        missing.append("--step (at least one)")
    if not args.ticket and not args.project:
        missing.append("--project (required when --ticket is omitted)")
    if missing:
        raise SystemExit(f"Missing required args: {', '.join(missing)}")


def _resolve_project(args: argparse.Namespace, ticket: str | None) -> str:
    if args.project:
        return args.project.upper()
    assert ticket is not None  # enforced by _validate_args
    return project_from_ticket(ticket)


def _bug_content(args: argparse.Namespace, *, ticket: str | None) -> tuple[str, str, list[str]]:
    """Return (project, description, labels) shared by dry-run and live create."""
    project = _resolve_project(args, ticket)
    branch_ticket = branch_issue_key()
    description = build_description(
        steps=args.steps,
        expected=args.expected,
        actual=args.actual,
        environment=args.environment,
        severity=args.severity,
        notes=args.notes,
        ticket=ticket,
        branch_ticket=branch_ticket,
    )
    labels = list(dict.fromkeys(["automated", "playwright", *args.labels]))
    return project, description, labels


def _run_dry_run(args: argparse.Namespace, ticket: str | None) -> int:
    """--dry-run needs no credentials at all — mirrors zephyr_sync.py's contract."""
    project, description, labels = _bug_content(args, ticket=ticket)
    _print_dry_run(
        ticket=ticket,
        project=project,
        issuetype=args.issuetype,
        summary=args.summary,
        description=description,
        environment=args.environment,
        severity=args.severity,
        priority=args.priority,
        labels=labels,
        components=args.components,
        attachments=args.attachments,
        link_type=args.link_type,
        branch_ticket=branch_issue_key(),
    )
    return 0


def _link_new_bug(
    client: httpx.Client,
    *,
    atm: str,
    token: CHANGE_ME
    bug_key: str,
    ticket: str | None,
    link_type: str,
) -> None:
    """Link the new bug to --ticket (Jira issue or Zephyr test case) and the branch ticket."""
    branch_ticket = branch_issue_key()
    if ticket and is_zephyr_test_key(ticket):
        with httpx.Client(
            base_url=atm,
            # No default Content-Type — httpx sets application/json for json=... calls on
            # its own, and a client-level default would otherwise collide with the
            # multipart boundary header attach_files() needs for file uploads.
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=60.0,
        ) as atm_client:
            link_bug_to_testcase(atm_client, testcase_key=ticket, bug_key=bug_key)
    elif ticket:
        link_issue_to_issue(client, from_key=bug_key, to_key=ticket, link_type=link_type)

    if branch_ticket and branch_ticket != ticket and not is_zephyr_test_key(branch_ticket):
        link_issue_to_issue(client, from_key=bug_key, to_key=branch_ticket, link_type=link_type)


def _run_create(args: argparse.Namespace, ticket: str | None) -> int:
    """Live path: create the Bug, then link + attach."""
    loaded = load_jira_local_env(start=Path(__file__))
    if loaded:
        print(f"Using local Jira env file: {loaded}")
    token = _env("JIRA_TOKEN")
    atm = _env("JIRA_ATM").rstrip("/")
    jira_rest = _jira_rest_base(atm)

    with httpx.Client(
        base_url=jira_rest,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    ) as client:
        if args.discover_priorities:
            discover_priorities(client)
            return 0
        if args.discover_fields:
            discover_fields(client, project=args.project, issuetype=args.issuetype)
            return 0

        project, description, labels = _bug_content(args, ticket=ticket)
        reporter = current_user_reporter_field(client)
        bug_key = create_bug(
            client,
            project=project,
            issuetype=args.issuetype,
            summary=args.summary,
            description=description,
            environment=args.environment,
            severity=args.severity,
            priority=args.priority,
            labels=labels,
            components=args.components,
            reporter=reporter,
            severity_field=args.severity_field,
            severity_field_value=args.severity_field_value,
        )
        print(f"Created {bug_key} → {_jira_host(jira_rest)}/browse/{bug_key}")

        _link_new_bug(
            client, atm=atm, token=token, bug_key=bug_key, ticket=ticket, link_type=args.link_type
        )

        if args.attachments:
            attach_files(client, key=bug_key, paths=args.attachments)

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for filing a standard-format Bug on Jira."""
    args = _build_arg_parser().parse_args(argv)
    apply_auto_fill(args)
    args.environment = args.environment or _DEFAULT_ENVIRONMENT
    _validate_args(args)
    ticket = normalize_ticket(args.ticket) if args.ticket else None
    if args.dry_run:
        return _run_dry_run(args, ticket)
    return _run_create(args, ticket)


if __name__ == "__main__":
    sys.exit(main())
