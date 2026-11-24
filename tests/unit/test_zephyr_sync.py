"""Unit tests for scripts/zephyr_sync.py Gherkin parsing and metadata helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "zephyr_sync.py"


@pytest.fixture(scope="module")
def zs() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("zephyr_sync", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["zephyr_sync"] = mod
    spec.loader.exec_module(mod)
    return mod


SAMPLE = """
@api @regression @bill @tci @bill_tci_inquiry
Feature: Landline telephone bill inquiry


  Background:
    Given a shared customer identity

  @positive @high
  Scenario: Plain happy path
    Given a funded wallet
    When the customer pays with:
      | amount | currency |
      | 100    | IRR      |
    Then payment succeeds
    And the receipt contains:
      \"\"\"
      paid OK
      \"\"\"


  @ALPHA-999
  @negative
  @high
  @zephyr
  Scenario Outline: Rejects invalid input
    When the customer tries <case>
    Then it fails as <result>

    Examples:
      | case | result |
      | bad  | FAIL   |
"""


def test_parses_outline_background_table_docstring_multiline_tags(zs: types.ModuleType) -> None:
    scenarios = zs._parse_scenarios(SAMPLE)
    assert len(scenarios) == 2

    plain = scenarios[0]
    assert plain.name == "Plain happy path"
    assert plain.tags == ["positive", "high"]
    assert plain.steps[0] == "Given a shared customer identity"
    assert "When the customer pays with:" in plain.steps
    assert any("| amount | currency |" in s for s in plain.steps)
    assert any('"""' in s for s in plain.steps)
    assert any("paid OK" in s for s in plain.steps)

    outline = scenarios[1]
    assert outline.name == "Rejects invalid input"
    assert outline.tags == ["ALPHA-999", "negative", "high", "zephyr"]
    assert outline.tag_line_count == 4
    assert outline.wants_create is True
    assert outline.issue_keys == ["ALPHA-999"]
    assert outline.steps[0] == "Given a shared customer identity"
    assert "Examples:" in outline.steps
    assert any("| bad  | FAIL   |" in s or "| bad |" in s for s in outline.steps)


def test_feature_tags_and_path_labels(zs: types.ModuleType, tmp_path: Path) -> None:
    lines = SAMPLE.strip().splitlines()
    assert zs._parse_feature_tags(lines) == [
        "api",
        "regression",
        "bill",
        "tci",
        "bill_tci_inquiry",
    ]
    feature = tmp_path / "tests" / "bdd" / "features" / "bill" / "tci" / "tci_inquiry.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text("Feature: x\n", encoding="utf-8")
    assert zs._path_labels(feature) == ["bill", "tci"]


def test_labels_derived_not_hardcoded(zs: types.ModuleType) -> None:
    labels = zs._labels_for(
        ["zephyr", "high", "ALPHA-T1", "ALPHA-99", "custom_scenario"],
        feature_tags=["api", "wallet", "wallet_transfer"],
        path_labels=["wallet"],
        extra=["branch:feat/x"],
    )
    assert "bill" not in labels
    assert "tci" not in labels
    assert "ALPHA-T1" not in labels
    assert "ALPHA-99" not in labels
    assert "zephyr" not in labels
    assert "high" not in labels
    assert labels == [
        "api",
        "wallet",
        "wallet_transfer",
        "custom_scenario",
        "automated",
        "branch:feat/x",
    ]


def test_priority_mapping(zs: types.ModuleType) -> None:
    assert zs._priority_for(["high"]) == "High"
    assert zs._priority_for(["medium"]) == "Normal"
    assert zs._priority_for(["low"]) == "Low"
    assert zs._priority_for(["positive"]) == "Normal"
    assert zs._priority_for(["high", "low"]) == "High"


def test_issue_key_excludes_zephyr_testcase_key(zs: types.ModuleType) -> None:
    assert zs._is_issue_key("ALPHA-123") is True
    assert zs._is_issue_key("ALPHA-T2132") is False
    assert zs._issue_keys(["ALPHA-T2132", "ALPHA-99", "high"]) == ["ALPHA-99"]
    assert zs._is_issue_key("KYC-T760") is False
    assert zs._zephyr_key(["KYC-T760", "high"]) == "KYC-T760"
    assert zs._normalize_key("kyc-t812") == "KYC-T812"


FEATURE_BULK = """
@api @zephyr
Feature: Bulk export


  Scenario: Untagged one
    Given a precondition
    When an action happens
    Then an outcome is visible


  @positive @high
  Scenario: Tagged two
    Given a precondition
    When an action happens
    Then an outcome is visible


  @ALPHA-T1000 @positive @high
  Scenario: Already keyed
    Given a precondition
    When an action happens
    Then an outcome is visible


  Scenario Outline: Outline three
    When the input is <value>
    Then the result is ok

    Examples:
      | value |
      | 1     |
"""


def test_parses_untagged_scenarios(zs: types.ModuleType) -> None:
    scenarios = zs._parse_scenarios(FEATURE_BULK)
    assert [s.name for s in scenarios] == [
        "Untagged one",
        "Tagged two",
        "Already keyed",
        "Outline three",
    ]
    untagged = scenarios[0]
    assert untagged.tags == []
    assert untagged.tag_line_count == 0
    assert untagged.tag_indent == "  "


def test_feature_zephyr_bulk_create_selection(zs: types.ModuleType, tmp_path: Path) -> None:
    feature = tmp_path / "bulk.feature"
    feature.write_text(FEATURE_BULK.strip() + "\n", encoding="utf-8")
    created, updated, skipped = zs.sync_feature(
        feature,
        folder="/Bill/TCI",
        dry_run=True,
        do_create=True,
        do_update=False,
        only_key=None,
        force=False,
    )
    assert created == 3  # all except Already keyed
    assert updated == 0
    assert skipped == 0
    assert zs._feature_wants_create(zs._parse_feature_tags(FEATURE_BULK.splitlines()))


def test_strip_zephyr_from_feature_tags(zs: types.ModuleType) -> None:
    lines = ["@api @zephyr @bill", "Feature: Demo", "", "  Scenario: X"]
    assert zs._strip_zephyr_from_feature_tags(lines) is True
    assert lines[0] == "@api @bill"
    assert zs._strip_zephyr_from_feature_tags(lines) is False


def test_write_scenario_tags_inserts_when_untagged(zs: types.ModuleType) -> None:
    lines = [
        "@zephyr",
        "Feature: Demo",
        "",
        "  Scenario: Untagged one",
        "    Given a precondition",
        "    When an action happens",
        "    Then an outcome is visible",
    ]
    scenarios = zs._parse_scenarios("\n".join(lines))
    assert len(scenarios) == 1
    zs._write_scenario_tags(lines, scenarios[0], ["ALPHA-T2001"])
    assert lines[3] == "  @ALPHA-T2001"
    assert lines[4].startswith("  Scenario:")
