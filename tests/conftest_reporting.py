"""Allure / Zephyr reporting hooks and CLI options for pytest.

Imported into ``tests/conftest.py`` (pytest only auto-loads that entry point).
"""

from __future__ import annotations

import platform
import re
import subprocess
from pathlib import Path
from typing import Any, cast

import allure
import pytest
from pytest import MarkDecorator

from tests.services.allure_dashboard import write_dashboard
from tests.services.allure_labels import (
    FEATURES_ROOT,
    all_domain_markers,
    gherkin_tag_markers,
    taxonomy_from_markers,
    write_allure_sidecars,
)

_ZEPHYR_KEY_TAG = re.compile(r"^([A-Z][A-Z0-9]+)-T(\d+)$", re.IGNORECASE)
_JIRA_ISSUE_TAG = re.compile(r"^[A-Z][A-Z0-9]+-\d+$", re.IGNORECASE)
_SAFE_NAME_RE = re.compile(r"[^\w.-]+")

ALLURE_RESULTS_DIR = Path("allure-results")
DASHBOARD_PATH = Path("allure-dashboard") / "index.html"

_SEVERITY_MARKERS = {
    "high": allure.severity_level.CRITICAL,
    "medium": allure.severity_level.NORMAL,
    "low": allure.severity_level.MINOR,
}


def safe_name(name: str) -> str:
    """Sanitize a node name for filesystem / Allure attachment filenames."""
    return _SAFE_NAME_RE.sub("_", name)[:150]


def _zephyr_key_of(item: pytest.Item) -> str | None:
    for mark in item.iter_markers(name="zephyr_key"):
        if mark.args:
            return str(mark.args[0])
    return None


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, timeout=5, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _collect_only(config: pytest.Config) -> bool:
    return bool(getattr(config.option, "collectonly", False))


def pytest_configure(config: pytest.Config) -> None:
    """Register Gherkin team folders and feature tags so new slices collect."""
    known = {row.split(":", 1)[0].strip() for row in config.getini("markers")}
    incoming = all_domain_markers() | gherkin_tag_markers()
    for name in sorted(incoming):
        if name not in known:
            config.addinivalue_line("markers", f"{name}: Platform Gherkin tag ({name})")


def _domain_from_feature_path(item: pytest.Item) -> str:
    raw = getattr(item, "path", None) or getattr(item, "fspath", None)
    if raw is None:
        return ""
    path = Path(str(raw)).resolve()
    try:
        relative = path.relative_to(FEATURES_ROOT.resolve())
    except ValueError:
        return ""
    return relative.parts[0] if relative.parts else ""


def pytest_sessionstart(session: pytest.Session) -> None:
    """Write categories, environment, and executor before any test runs."""
    if _collect_only(session.config):
        return
    results_dir = Path(str(session.config.option.allure_report_dir or ALLURE_RESULTS_DIR))
    lines = [
        "Framework=pytest-bdd + Playwright",
        f"Python={platform.python_version()}",
        f"OS={platform.system()} {platform.release()}",
        f"Git.Branch={_git('rev-parse', '--abbrev-ref', 'HEAD')}",
        f"Git.Commit={_git('rev-parse', '--short', 'HEAD')}",
    ]
    try:
        from tests.config.settings import Settings as _Settings

        settings = _Settings()  # type: ignore[call-arg]  # YAML source fills fields
        lines.append(f"App.Base.URL={settings.app_base_url}")
        lines.append(f"Dashboard.Base.URL={settings.dashboard_base_url}")
        lines.append(f"Browser={settings.ui_browser_alias}")
    except Exception as exc:  # config incomplete for this run — still write the rest
        lines.append(f"Config.Load.Error={exc}")
    write_allure_sidecars(results_dir, lines)


def _attach_allure_taxonomy(item: pytest.Item) -> None:
    """Copy Platform tag axes onto Allure epic/feature/suite/tag labels."""
    names = {m.name for m in item.iter_markers()}
    for level, severity in _SEVERITY_MARKERS.items():
        if level in names:
            item.add_marker(cast(MarkDecorator, allure.severity(severity)))
            break
    tax = taxonomy_from_markers(names)
    if not tax.epic:
        path_domain = _domain_from_feature_path(item)
        if path_domain:
            tax = taxonomy_from_markers(names | {path_domain})
    for value, factory in (
        (tax.epic, allure.epic),
        (tax.feature, allure.feature),
        (tax.parent_suite, allure.parent_suite),
        (tax.suite, allure.suite),
        (tax.sub_suite, allure.sub_suite),
    ):
        if value:
            item.add_marker(cast(MarkDecorator, factory(value)))
    if tax.package:
        item.add_marker(cast(MarkDecorator, allure.label("package", tax.package)))
    for tag in tax.tags:
        item.add_marker(cast(MarkDecorator, allure.tag(tag)))


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Map taxonomy markers onto Allure labels; honor ``--zephyr-keys``.

    Behaviors gets epic (domain) + feature tag + story (Jira, from apply_tag).
    ``--zephyr-keys=KYC-T1,ALPHA-T2`` narrows a run to exact Zephyr test cases.
    """
    for item in items:
        _attach_allure_taxonomy(item)
    raw_keys = (config.getoption("zephyr_keys", default=None) or "").strip()
    if not raw_keys:
        return
    wanted = {k.strip().upper() for k in raw_keys.split(",") if k.strip()}
    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        key = _zephyr_key_of(item)
        if key and key.upper() in wanted:
            selected.append(item)
        else:
            deselected.append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = selected


def _write_run_artifacts(
    summary: str,
    terminalreporter: Any,
    config: pytest.Config,
) -> None:
    """Persist summary.log and the Platform Allure dashboard HTML."""
    results_dir = Path(str(config.option.allure_report_dir or ALLURE_RESULTS_DIR))
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "summary.log").write_text(summary + "\n", encoding="utf-8")
    try:
        dest = DASHBOARD_PATH
        if results_dir.resolve() != ALLURE_RESULTS_DIR.resolve():
            dest = results_dir / "dashboard.html"
        path = write_dashboard(results_dir, dest)
    except OSError as exc:
        terminalreporter.write_line(f"Platform dashboard not written: {exc}")
        return
    terminalreporter.write_line(f"Platform dashboard -> {path}")


def pytest_terminal_summary(
    terminalreporter: Any,
    exitstatus: int,
    config: pytest.Config,
) -> None:
    """Write summary.log and allure-dashboard/index.html after the run.

    Complements the per-check log lines that ``tests/services/assert_report.py``
    writes to ``allure-results/pytest.log``.
    """
    del exitstatus
    if _collect_only(config):
        return
    stats = terminalreporter.stats
    passed = len(stats.get("passed", []))
    failed = len(stats.get("failed", []))
    errored = len(stats.get("error", []))
    skipped = len(stats.get("skipped", []))

    lines = [
        "=" * 70,
        f"TEST RUN SUMMARY — passed={passed} failed={failed} error={errored} skipped={skipped}",
        "=" * 70,
    ]
    for rep in stats.get("failed", []):
        lines.append(f"[FAIL]  {rep.nodeid}")
    for rep in stats.get("error", []):
        lines.append(f"[ERROR] {rep.nodeid}")
    for rep in stats.get("skipped", []):
        reason = rep.longrepr[-1] if isinstance(rep.longrepr, tuple) else rep.longrepr
        lines.append(f"[SKIP]  {rep.nodeid} — {reason}")

    summary = "\n".join(lines)
    terminalreporter.write_line(summary)
    _write_run_artifacts(summary, terminalreporter, config)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Any:
    """Stash each phase's report on the item for fixture teardown.

    Sets ``rep_setup`` / ``rep_call`` / ``rep_teardown`` so fixtures (e.g.
    ``browser_session``) can tell whether the test failed.
    """
    del call
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register CLI overrides for UI viewport, headed mode, and Zephyr keys."""
    parser.addoption(
        "--ui-view-mode",
        action="store",
        default=None,
        choices=["mobile", "desktop"],
        help=(
            "Override the Playwright viewport preset for UI tests "
            "(mobile=390x844, desktop=1440x900). Defaults to Settings.ui_view_mode "
            "('desktop') when not passed."
        ),
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Launch Chrome visibly instead of the default headless mode.",
    )
    parser.addoption(
        "--slow-mo",
        action="store",
        type=int,
        default=0,
        metavar="MS",
        help=(
            "Delay (ms) before every Playwright action — use with --headed "
            "to watch a run step by step."
        ),
    )
    parser.addoption(
        "--zephyr-keys",
        action="store",
        default=None,
        metavar="KYC-T1234,ALPHA-T5678",
        help=(
            "Comma-separated Zephyr test-case keys — run/report only the scenarios "
            "carrying one of these @PROJECT-T#### tags. Everything else is deselected."
        ),
    )


def pytest_bdd_apply_tag(tag: str, function: Any) -> bool | None:
    """Register @zephyr / @PROJECT-T####; ignore Jira story keys for markers."""
    if tag.lower() == "zephyr":
        pytest.mark.zephyr(function)
        return True
    match = _ZEPHYR_KEY_TAG.match(tag)
    if match:
        key = f"{match.group(1).upper()}-T{match.group(2)}"
        # Hyphens are invalid in mark *names* — store the key as mark arg.
        pytest.mark.zephyr_key(key)(function)
        allure.tag(key)(function)
        return True
    if _JIRA_ISSUE_TAG.match(tag):
        # Story/bug link for Zephyr sync + Allure Behaviors (not a pytest mark name).
        allure.story(tag.upper())(function)
        return True
    return None
