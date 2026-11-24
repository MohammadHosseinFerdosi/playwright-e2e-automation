"""Map Platform pytest markers onto Allure epic / feature / suite labels.

Behaviors and Graphs stay empty unless every scenario carries these labels.
Story (Jira) and Zephyr keys are attached in ``pytest_bdd_apply_tag``.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

FEATURES_ROOT = Path(__file__).resolve().parents[2] / "tests" / "bdd" / "features"

ALLURE_CATEGORIES = [
    {
        "name": "Product defects",
        "matchedStatuses": ["failed"],
        "messageRegex": ".*AssertionError.*",
    },
    {
        "name": "Environment / connectivity issues",
        "matchedStatuses": ["failed", "broken"],
        "messageRegex": (
            ".*(Connection refused|Name or service not known|ECONNREFUSED|"
            "ConnectTimeout|net::ERR_|ERR_NAME_NOT_RESOLVED|ERR_CONNECTION|"
            "401 |403 |got 401|got 403|AUTHENTICATION_INVALID).*"
        ),
    },
    {
        "name": "Timeouts",
        "matchedStatuses": ["failed", "broken"],
        "messageRegex": r".*TimeoutError.*",
    },
    {
        "name": "Playwright timeouts",
        "matchedStatuses": ["failed", "broken"],
        "traceRegex": r".*(Timeout \d+ms exceeded|waiting for locator).*",
    },
    {
        "name": "Test / framework defects",
        "matchedStatuses": ["broken"],
    },
    {
        "name": "Skipped — missing secrets or test data",
        "matchedStatuses": ["skipped"],
        "messageRegex": ".*(secrets|missing).*",
    },
]


def categorize_allure(status: str, message: str, trace: str = "") -> str:
    """Return the first matching Allure category name (same rules as categories.json).

    Args:
        status: Allure status (passed, failed, broken, skipped).
        message: ``statusDetails.message`` (unmasked, for regex only).
        trace: Optional traceback snippet; falls back to ``message``.

    Returns:
        Category name, ``Uncategorized`` for unmatched failures, or empty for passes.
    """
    blob_msg = message or ""
    blob_trace = trace or blob_msg
    flags = re.IGNORECASE | re.DOTALL
    for cat in ALLURE_CATEGORIES:
        statuses = cat.get("matchedStatuses")
        if isinstance(statuses, list) and statuses and status not in statuses:
            continue
        msg_re = cat.get("messageRegex")
        trace_re = cat.get("traceRegex")
        if msg_re and not re.search(str(msg_re), blob_msg, flags):
            continue
        if trace_re and not re.search(str(trace_re), blob_trace, flags):
            continue
        name = cat.get("name")
        if isinstance(name, str) and name:
            return name
    if status in {"failed", "broken"}:
        return "Uncategorized"
    if status == "skipped":
        return "Skipped"
    return ""


TYPE_MARKERS = frozenset({"api", "e2e"})
SUITE_MARKERS = frozenset({"smoke", "regression"})
SEVERITY_MARKERS = frozenset({"high", "medium", "low"})
BEHAVIOR_MARKERS = frozenset({"positive", "negative"})
RISK_MARKERS = frozenset(
    {"idempotency", "pii", "aml", "rounding", "concurrency", "session_timeout"}
)
PROCESS_MARKERS = frozenset({"zephyr", "zephyr_key"})
PLUGIN_MARKERS = frozenset({"xdist_group", "usefixtures", "parametrize", "filterwarnings"})
DOMAIN_MARKERS = frozenset(
    {
        "platform",
        "payment",
        "wallet",
        "bill",
        "tci",
        "kyc",
        "lms",
        "app",
        "debit",
        "dashboard",
    }
)


@lru_cache(maxsize=1)
def feature_domain_names() -> frozenset[str]:
    """Top-level folders under ``tests/bdd/features`` — one folder is one team.

    A new team is a new folder. Cached for one process (pytest collection).
    """
    if not FEATURES_ROOT.is_dir():
        return frozenset()
    return frozenset(
        path.name
        for path in FEATURES_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith(("_", "."))
    )


def all_domain_markers() -> frozenset[str]:
    """Domain tags: known markers plus every Gherkin team folder."""
    return DOMAIN_MARKERS | feature_domain_names()


@lru_cache(maxsize=1)
def gherkin_tag_markers() -> frozenset[str]:
    """Lowercase ``@tags`` in ``.feature`` files so new tests collect under strict markers."""
    found: set[str] = set()
    if not FEATURES_ROOT.is_dir():
        return frozenset()
    tag_re = re.compile(r"@([a-z][a-z0-9_]*)")
    for path in FEATURES_ROOT.rglob("*.feature"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        found.update(tag_re.findall(text))
    return frozenset(found)


def _non_feature_tags() -> frozenset[str]:
    return (
        TYPE_MARKERS
        | SUITE_MARKERS
        | SEVERITY_MARKERS
        | BEHAVIOR_MARKERS
        | RISK_MARKERS
        | PROCESS_MARKERS
        | PLUGIN_MARKERS
        | all_domain_markers()
    )


@dataclass(frozen=True)
class AllureTaxonomy:
    """Allure labels derived from registered pytest marker names."""

    epic: str | None
    feature: str | None
    parent_suite: str | None
    suite: str | None
    sub_suite: str | None
    package: str | None
    tags: tuple[str, ...]


def taxonomy_from_markers(names: set[str]) -> AllureTaxonomy:
    """Pick epic/feature/suite from the scenario's marker names.

    Feature is the longest ``{domain}_{capability}`` marker so a slice tag
    like ``kyc_promissory`` loses to ``kyc_promissory_renew``. Package is
    ``api.wallet.wallet_transfer`` so the Packages tab groups every team.
    """
    domains = names & all_domain_markers()
    types = names & TYPE_MARKERS
    suites = names & SUITE_MARKERS
    behaviors = names & BEHAVIOR_MARKERS
    skip_tags = _non_feature_tags()
    feature_candidates = [
        name
        for name in names
        if name not in skip_tags and "_" in name and not name.startswith("allure")
    ]
    feature = max(feature_candidates, key=len) if feature_candidates else None
    epic = sorted(domains)[0] if domains else None
    parent_suite = sorted(types)[0] if types else None
    package_parts = [part for part in (parent_suite, epic, feature) if part]
    tags = tuple(sorted((names & RISK_MARKERS) | behaviors))
    return AllureTaxonomy(
        epic=epic,
        feature=feature,
        parent_suite=parent_suite,
        suite=sorted(suites)[0] if suites else None,
        sub_suite=sorted(behaviors)[0] if behaviors else None,
        package=".".join(package_parts) if package_parts else None,
        tags=tags,
    )


def executor_payload(environ: Mapping[str, str]) -> dict[str, Any]:
    """Allure ``executor.json`` for Overview — GitLab when CI vars exist."""
    job_url = environ.get("CI_JOB_URL") or environ.get("CI_PIPELINE_URL") or ""
    if job_url:
        name = environ.get("CI_JOB_NAME") or "GitLab CI"
        return {
            "name": name,
            "type": "gitlab",
            "url": environ.get("CI_PROJECT_URL") or "",
            "buildName": name,
            "buildUrl": job_url,
            "reportName": "Platform Allure",
            "reportUrl": job_url,
        }
    return {
        "name": "Local",
        "type": "local",
        "buildName": "pytest",
        "reportName": "Platform Allure",
    }


def write_allure_sidecars(
    results_dir: Path,
    environment_lines: list[str],
    environ: Mapping[str, str] | None = None,
) -> None:
    """Write categories.json, environment.properties, and executor.json into ``results_dir``.

    Args:
        results_dir: Pytest ``--alluredir`` folder.
        environment_lines: ``KEY=value`` lines for environment.properties.
        environ: Process env for GitLab executor fields. Defaults to ``os.environ``.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "categories.json").write_text(
        json.dumps(ALLURE_CATEGORIES, indent=2), encoding="utf-8"
    )
    (results_dir / "environment.properties").write_text(
        "\n".join(environment_lines) + "\n", encoding="utf-8"
    )
    payload = executor_payload(environ if environ is not None else os.environ)
    (results_dir / "executor.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
