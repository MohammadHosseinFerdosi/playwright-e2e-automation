"""Unit tests for Allure epic/feature/suite mapping (no UAT)."""

from __future__ import annotations

import json
from pathlib import Path

from tests.services.allure_labels import (
    categorize_allure,
    executor_payload,
    feature_domain_names,
    gherkin_tag_markers,
    taxonomy_from_markers,
    write_allure_sidecars,
)


def test_taxonomy_picks_longest_feature_and_closed_axes() -> None:
    tax = taxonomy_from_markers(
        {
            "kyc",
            "kyc_promissory",
            "kyc_promissory_renew",
            "api",
            "regression",
            "high",
            "negative",
            "xdist_group",
        }
    )
    assert tax.epic == "kyc"
    assert tax.feature == "kyc_promissory_renew"
    assert tax.parent_suite == "api"
    assert tax.suite == "regression"
    assert tax.sub_suite == "negative"
    assert tax.package == "api.kyc.kyc_promissory_renew"
    assert tax.tags == ("negative",)


def test_taxonomy_ignores_plugin_and_severity_as_feature() -> None:
    tax = taxonomy_from_markers({"wallet", "api", "smoke", "high", "parametrize"})
    assert tax.epic == "wallet"
    assert tax.feature is None
    assert tax.parent_suite == "api"
    assert tax.suite == "smoke"
    assert tax.sub_suite is None
    assert tax.package == "api.wallet"
    assert tax.tags == ()


def test_executor_payload_gitlab_when_job_url_set() -> None:
    payload = executor_payload(
        {
            "CI_JOB_URL": "https://gitlab.example/jobs/1",
            "CI_JOB_NAME": "Pytest Smoke API",
            "CI_PROJECT_URL": "https://gitlab.example/proj",
        }
    )
    assert payload["type"] == "gitlab"
    assert payload["buildUrl"] == "https://gitlab.example/jobs/1"
    assert payload["name"] == "Pytest Smoke API"


def test_executor_payload_local_without_ci() -> None:
    payload = executor_payload({})
    assert payload["type"] == "local"
    assert payload["name"] == "Local"


def test_write_allure_sidecars(tmp_path: Path) -> None:
    write_allure_sidecars(tmp_path, ["Python=3.11"], environ={})
    categories = json.loads((tmp_path / "categories.json").read_text(encoding="utf-8"))
    assert categories[0]["name"] == "Product defects"
    assert any(row["name"] == "Timeouts" for row in categories)
    assert "Python=3.11" in (tmp_path / "environment.properties").read_text(encoding="utf-8")
    executor = json.loads((tmp_path / "executor.json").read_text(encoding="utf-8"))
    assert executor["type"] == "local"


def test_categorize_allure_matches_first_rule() -> None:
    assert categorize_allure("failed", "AssertionError: expected 1") == "Product defects"
    assert categorize_allure("broken", "TimeoutError: shahin wait") == "Timeouts"
    assert categorize_allure("failed", "401 Unauthorized") == "Environment / connectivity issues"
    assert (
        categorize_allure(
            "broken",
            "RuntimeError: Business login failed: expected status_code=200, got 401; body={}",
        )
        == "Environment / connectivity issues"
    )
    assert (
        categorize_allure("broken", "locator click", "Timeout 30000ms exceeded")
        == "Playwright timeouts"
    )
    assert categorize_allure("broken", "KeyError: foo") == "Test / framework defects"
    assert categorize_allure("skipped", "missing secrets file") == (
        "Skipped — missing secrets or test data"
    )
    assert categorize_allure("failed", "unexpected status 500") == "Uncategorized"
    assert categorize_allure("passed", "") == ""


def test_feature_domain_names_follows_gherkin_folders() -> None:
    names = feature_domain_names()
    assert "kyc" in names
    assert "debit" in names
    assert "wallet" in names
    assert "bill" in names


def test_gherkin_tag_markers_include_feature_tags() -> None:
    tags = gherkin_tag_markers()
    assert "kyc_promissory_note" in tags
    assert "wallet_transfer" in tags
