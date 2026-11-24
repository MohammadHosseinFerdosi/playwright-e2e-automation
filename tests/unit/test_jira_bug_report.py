"""Unit tests for scripts/jira_bug_report.py (pure functions only, no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.jira_bug_report import (
    actual_result_from_allure,
    build_description,
    environment_from_properties,
    failed_step_name,
    find_failed_allure_result,
    find_tagged_scenario,
    is_zephyr_test_key,
    normalize_ticket,
    project_from_ticket,
    severity_from_allure,
    split_steps_and_expected,
)


def test_normalize_ticket_zephyr_test_case() -> None:
    assert normalize_ticket("@alpha-t2233") == "ALPHA-T2233"


def test_normalize_ticket_jira_issue() -> None:
    assert normalize_ticket("kyc-1234") == "KYC-1234"


def test_normalize_ticket_rejects_garbage() -> None:
    with pytest.raises(SystemExit):
        normalize_ticket("not-a-ticket")


def test_is_zephyr_test_key_true_for_test_case() -> None:
    assert is_zephyr_test_key("ALPHA-T2233") is True


def test_is_zephyr_test_key_false_for_issue() -> None:
    assert is_zephyr_test_key("ALPHA-1234") is False


def test_project_from_ticket() -> None:
    assert project_from_ticket("ALPHA-T2233") == "ALPHA"
    assert project_from_ticket("KYC-1234") == "KYC"


def test_build_description_linked_ticket() -> None:
    text = build_description(
        steps=["Open page", "Click button"],
        expected="Success toast",
        actual="Nothing happens",
        environment="Platform UAT",
        severity="High",
        notes="",
        ticket="ALPHA-T2233",
        branch_ticket="",
    )
    assert "# Open page" in text
    assert "# Click button" in text
    assert "h3. Expected Result" in text
    assert "h3. Severity" in text
    assert "linked to ALPHA-T2233" in text


def test_build_description_no_ticket_goes_to_backlog() -> None:
    text = build_description(
        steps=["Open page"],
        expected="Success",
        actual="Failure",
        environment="Platform UAT",
        severity="Low",
        notes="",
        ticket=None,
        branch_ticket="",
    )
    assert "filed to backlog, no linked ticket" in text


def test_split_steps_and_expected_splits_on_then() -> None:
    steps = [
        {"name": "Given a Platform business access token", "status": "passed"},
        {"name": "When the bundle catalog is requested", "status": "passed"},
        {"name": "Then every internet package has a positive amount", "status": "failed"},
    ]
    repro, expected = split_steps_and_expected(steps)
    assert repro == [
        "Given a Platform business access token",
        "When the bundle catalog is requested",
    ]
    assert expected == "Then every internet package has a positive amount"


def test_split_steps_and_expected_no_then_falls_back_to_last_step() -> None:
    steps = [
        {"name": "Given something", "status": "passed"},
        {"name": "When it happens", "status": "failed"},
    ]
    repro, expected = split_steps_and_expected(steps)
    assert repro == ["Given something"]
    assert expected == "When it happens"


def test_severity_from_allure_maps_known_levels() -> None:
    assert severity_from_allure({"labels": [{"name": "severity", "value": "critical"}]}) == "High"
    assert severity_from_allure({"labels": [{"name": "severity", "value": "normal"}]}) == "Medium"
    assert severity_from_allure({"labels": [{"name": "severity", "value": "minor"}]}) == "Low"


def test_severity_from_allure_missing_label_returns_none() -> None:
    assert severity_from_allure({"labels": []}) is None


def test_failed_step_name_returns_first_non_passed() -> None:
    steps = [
        {"name": "Given setup", "status": "passed"},
        {"name": "When action", "status": "failed"},
        {"name": "Then check", "status": "skipped"},
    ]
    assert failed_step_name({"steps": steps}) == "When action"


def test_actual_result_from_allure_wraps_message_in_noformat() -> None:
    result = {
        "status": "failed",
        "statusDetails": {"message": "[FAIL] amount: expected=True actual=False"},
    }
    text = actual_result_from_allure(result)
    assert text.startswith("{noformat}")
    assert "expected=True actual=False" in text


def test_actual_result_from_allure_falls_back_when_empty() -> None:
    text = actual_result_from_allure({"status": "broken", "statusDetails": {}})
    assert "no failure message captured" in text


def test_find_tagged_scenario_matches_scenario_level_tag(tmp_path: Path) -> None:
    feature = tmp_path / "sample.feature"
    feature.write_text(
        "Feature: Sample\n\n"
        "  @ALPHA-T9999 @positive @high\n"
        "  Scenario: Do the thing\n"
        "    Given a precondition\n"
        "    Then it works\n",
        encoding="utf-8",
    )
    found_path, scenario_name = find_tagged_scenario(tmp_path, "ALPHA-T9999")
    assert found_path == feature
    assert scenario_name == "Do the thing"


def test_find_tagged_scenario_raises_when_not_found(tmp_path: Path) -> None:
    (tmp_path / "sample.feature").write_text("Feature: Sample\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        find_tagged_scenario(tmp_path, "ALPHA-T0000")


def test_find_failed_allure_result_picks_failed_by_name(tmp_path: Path) -> None:
    (tmp_path / "a-result.json").write_text(
        json.dumps({"name": "Do the thing", "status": "passed"}), encoding="utf-8"
    )
    (tmp_path / "b-result.json").write_text(
        json.dumps({"name": "Do the thing", "status": "failed", "statusDetails": {}}),
        encoding="utf-8",
    )
    result = find_failed_allure_result(tmp_path, "Do the thing")
    assert result["status"] == "failed"


def test_find_failed_allure_result_raises_when_no_match(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        find_failed_allure_result(tmp_path, "Nonexistent scenario")


def test_environment_from_properties_reads_file(tmp_path: Path) -> None:
    (tmp_path / "environment.properties").write_text(
        "Git.Branch=main\nApp.Base.URL=https://example.test\n", encoding="utf-8"
    )
    text = environment_from_properties(tmp_path)
    assert text is not None
    assert "Git.Branch=main" in text


def test_environment_from_properties_missing_file_returns_none(tmp_path: Path) -> None:
    assert environment_from_properties(tmp_path) is None
