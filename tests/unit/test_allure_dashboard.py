"""Unit tests for the Platform Allure HTML dashboard (no UAT)."""

from __future__ import annotations

import json
from pathlib import Path

from tests.services.allure_dashboard import (
    build_dashboard_model,
    load_cases,
    team_color,
    write_dashboard,
)


def _write_result(folder: Path, stem: str, payload: dict[str, object]) -> None:
    (folder / f"{stem}-result.json").write_text(json.dumps(payload), encoding="utf-8")


def test_load_cases_groups_labels_and_skips_junk(tmp_path: Path) -> None:
    _write_result(
        tmp_path,
        "wallet",
        {
            "name": "Customer transfers wallet balance",
            "status": "passed",
            "start": 1000,
            "stop": 2500,
            "labels": [
                {"name": "epic", "value": "wallet"},
                {"name": "feature", "value": "wallet_transfer"},
                {"name": "story", "value": "ALPHA-1"},
                {"name": "parentSuite", "value": "api"},
                {"name": "suite", "value": "smoke"},
            ],
        },
    )
    _write_result(tmp_path, "broken-json", {"not": "a test"})
    (tmp_path / "nope-container.json").write_text("{}", encoding="utf-8")
    (tmp_path / "bad-result.json").write_text("{", encoding="utf-8")
    cases = load_cases(tmp_path)
    assert len(cases) == 1
    assert cases[0].epic == "wallet"
    assert cases[0].duration_ms == 1500
    assert cases[0].parent_suite == "api"
    assert cases[0].started_ms == 1000


def test_load_cases_reads_zephyr_and_masked_reason(tmp_path: Path) -> None:
    _write_result(
        tmp_path,
        "fail",
        {
            "name": "Inquiry fails",
            "status": "failed",
            "statusDetails": {"message": "AssertionError: phone 09121234567 bad"},
            "labels": [
                {"name": "tag", "value": "@KYC-T1131"},
                {"name": "epic", "value": "kyc"},
            ],
        },
    )
    cases = load_cases(tmp_path)
    assert cases[0].zephyr == "KYC-T1131"
    assert "09121234567" not in cases[0].reason
    assert "AssertionError" in cases[0].reason


def test_build_dashboard_model_counts_domains(tmp_path: Path) -> None:
    _write_result(
        tmp_path,
        "kyc-ok",
        {
            "name": "Inquiry succeeds",
            "status": "passed",
            "start": 1,
            "stop": 2,
            "labels": [
                {"name": "epic", "value": "kyc"},
                {"name": "feature", "value": "kyc_inquiry"},
                {"name": "parentSuite", "value": "api"},
                {"name": "suite", "value": "regression"},
            ],
        },
    )
    _write_result(
        tmp_path,
        "bill-fail",
        {
            "name": "Bill pay fails",
            "status": "failed",
            "start": 1,
            "stop": 11,
            "labels": [
                {"name": "epic", "value": "bill"},
                {"name": "feature", "value": "bill_pay"},
                {"name": "parentSuite", "value": "e2e"},
                {"name": "suite", "value": "smoke"},
            ],
        },
    )
    (tmp_path / "environment.properties").write_text("Python=3.11\n", encoding="utf-8")
    model = build_dashboard_model(tmp_path, features_root=tmp_path / "no-features")
    assert model["total"] == 2
    assert model["passed"] == 1
    assert model["failed"] == 1
    assert model["failedOnly"] == 1
    assert model["broken"] == 0
    bill = next(row for row in model["domains"] if row["name"] == "bill")
    assert bill["failedOnly"] == 1
    assert bill["broken"] == 0
    assert bill["ran"] == 1
    assert model["rate"] == 50.0
    assert model["executed"] == 2
    assert model["executedRate"] == 50.0
    names = {row["name"] for row in model["domains"]}
    assert names == {"kyc", "bill"}
    assert len(model["problems"]) == 1
    assert model["problems"][0]["name"] == "Bill pay fails"
    assert dict(model["environment"])["Python"] == "3.11"


def test_team_tiles_include_catalog_domains_not_in_run(tmp_path: Path) -> None:
    wallet = tmp_path / "features" / "wallet"
    wallet.mkdir(parents=True)
    (wallet / "x.feature").write_text(
        "Feature: x\n  Scenario: one\n  Scenario Outline: two\n",
        encoding="utf-8",
    )
    _write_result(
        tmp_path,
        "kyc-ok",
        {
            "name": "Inquiry succeeds",
            "status": "passed",
            "start": 1,
            "stop": 2,
            "labels": [{"name": "epic", "value": "kyc"}],
        },
    )
    model = build_dashboard_model(tmp_path, features_root=tmp_path / "features")
    by_name = {row["name"]: row for row in model["domains"]}
    assert by_name["wallet"]["rate"] is None
    assert by_name["wallet"]["inRepo"] == 2
    assert by_name["kyc"]["total"] == 1
    assert model["catalogTeams"] == 1
    assert model["domains"][0]["name"] == "kyc"
    assert model["catalogScenarios"] == 2
    assert by_name["wallet"]["label"] == "Wallet"
    assert by_name["wallet"]["color"] == "#1d4ed8"
    assert by_name["kyc"]["label"] == "KYC"
    assert team_color("debit") == "#2563eb"
    assert team_color("wallet") != "#12b76a"


def test_write_dashboard_embeds_model(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    _write_result(
        results,
        "one",
        {"name": "A scenario", "status": "passed", "labels": [{"name": "epic", "value": "app"}]},
    )
    dest = tmp_path / "out" / "index.html"
    path = write_dashboard(results, dest)
    html = path.read_text(encoding="utf-8")
    assert "Platform" in html
    assert "Test dashboard" in html
    assert "A scenario" in html
    assert "categoryMeta" in html
    assert "generatedMs" in html
    assert '"epic": "app"' in html or "app" in html


def test_load_cases_reads_failed_step_params_and_category(tmp_path: Path) -> None:
    _write_result(
        tmp_path,
        "fail",
        {
            "name": "Cash-out via Shahin",
            "status": "broken",
            "statusDetails": {"message": "TimeoutError: shahin INTERNAL_TRANSFER"},
            "parameters": [
                {"name": "weight", "value": "100"},
                {"name": "client", "value": "<tests.services.Foo object at 0x1>"},
            ],
            "steps": [
                {
                    "name": "Given cash-out goes through Shahin",
                    "status": "broken",
                    "steps": [
                        {"name": "poll until weight is 100", "status": "broken"},
                    ],
                }
            ],
            "labels": [
                {"name": "epic", "value": "debit"},
                {"name": "subSuite", "value": "positive"},
                {"name": "severity", "value": "high"},
            ],
        },
    )
    cases = load_cases(tmp_path)
    assert cases[0].step == "poll until weight is 100"
    assert cases[0].params == "weight=100"
    assert cases[0].category == "Timeouts"
    assert cases[0].behavior == "positive"
    assert cases[0].severity == "high"


def test_allure_critical_severity_maps_to_gherkin_high(tmp_path: Path) -> None:
    _write_result(
        tmp_path,
        "fail",
        {
            "name": "Cash-out",
            "status": "broken",
            "labels": [
                {"name": "epic", "value": "debit"},
                {"name": "severity", "value": "critical"},
            ],
        },
    )
    assert load_cases(tmp_path)[0].severity == "high"


def test_build_dashboard_model_executed_rate_excludes_skips(tmp_path: Path) -> None:
    _write_result(
        tmp_path,
        "ok",
        {"name": "ok", "status": "passed", "labels": [{"name": "epic", "value": "kyc"}]},
    )
    _write_result(
        tmp_path,
        "skip",
        {
            "name": "skip",
            "status": "skipped",
            "statusDetails": {"message": "missing secrets"},
            "labels": [{"name": "epic", "value": "bill"}],
        },
    )
    model = build_dashboard_model(tmp_path, features_root=tmp_path / "no-features")
    assert model["total"] == 2
    assert model["skipped"] == 1
    assert model["executed"] == 1
    assert model["rate"] == 50.0
    assert model["executedRate"] == 100.0
    assert model["skips"][0]["category"] == "Skipped — missing secrets or test data"
    names = {row["name"] for row in model["categoryMeta"]}
    assert "Product defects" in names
    assert "Timeouts" in names


def test_new_team_and_feature_show_before_they_run(tmp_path: Path) -> None:
    wealth = tmp_path / "features" / "wealth"
    wealth.mkdir(parents=True)
    (wealth / "portfolio.feature").write_text(
        "@wealth @wealth_portfolio @api @regression\n"
        "Feature: Portfolio\n"
        "  Scenario: holdings list\n",
        encoding="utf-8",
    )
    _write_result(
        tmp_path,
        "kyc-ok",
        {
            "name": "Inquiry succeeds",
            "status": "passed",
            "start": 1,
            "stop": 2,
            "labels": [{"name": "epic", "value": "kyc"}],
        },
    )
    model = build_dashboard_model(tmp_path, features_root=tmp_path / "features")
    by_team = {row["name"]: row for row in model["domains"]}
    assert by_team["wealth"]["total"] == 0
    assert by_team["wealth"]["inRepo"] == 1
    assert by_team["wealth"]["label"] == "Wealth"
    assert by_team["wealth"]["color"].startswith("hsl(")
    by_feat = {row["name"]: row for row in model["features"]}
    assert by_feat["wealth_portfolio"]["total"] == 0
    assert by_feat["wealth_portfolio"]["inRepo"] == 1
    assert model["catalogFiles"] == 1
    assert model["catalogTeams"] == 1


def test_failed_and_passed_embed_json_attachments(tmp_path: Path) -> None:
    (tmp_path / "req.json").write_text(
        json.dumps({"headers": {"Authorization": "***"}, "body": {"status_code": 422}}),
        encoding="utf-8",
    )
    (tmp_path / "ok.json").write_text(
        json.dumps({"headers": {"Authorization": "***"}, "body": {"status_code": 200}}),
        encoding="utf-8",
    )
    (tmp_path / "secret.json").write_text(
        json.dumps({"accessToken": "SHOULD-NOT-APPEAR"}),
        encoding="utf-8",
    )
    _write_result(
        tmp_path,
        "fail",
        {
            "name": "Inquiry fails",
            "status": "failed",
            "labels": [{"name": "epic", "value": "kyc"}],
            "attachments": [
                {
                    "name": "Response POST /inquiry -> 422",
                    "source": "req.json",
                    "type": "application/json",
                },
                {"name": "screenshot-fail", "source": "shot.png", "type": "image/png"},
            ],
        },
    )
    _write_result(
        tmp_path,
        "ok",
        {
            "name": "Inquiry succeeds",
            "status": "passed",
            "labels": [{"name": "epic", "value": "kyc"}],
            "attachments": [
                {
                    "name": "Response POST /inquiry -> 200",
                    "source": "ok.json",
                    "type": "application/json",
                }
            ],
        },
    )
    model = build_dashboard_model(tmp_path, features_root=tmp_path / "no-features")
    problem = model["problems"][0]
    assert problem["http"][0]["name"].startswith("Response")
    assert "422" in problem["http"][0]["body"]
    assert "***" in problem["http"][0]["body"]
    assert problem["hasScreenshot"] is True
    passed = next(row for row in model["cases"] if row["status"] == "passed")
    assert passed["http"][0]["name"].startswith("Response")
    assert "200" in passed["http"][0]["body"]
    dest = tmp_path / "out" / "index.html"
    html = write_dashboard(tmp_path, dest).read_text(encoding="utf-8")
    assert "422" in html
    assert "SHOULD-NOT-APPEAR" not in html


def test_write_dashboard_stamps_run(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    _write_result(
        results,
        "fail",
        {
            "name": "Inquiry fails",
            "status": "failed",
            "labels": [{"name": "epic", "value": "bill"}],
        },
    )
    (results / "environment.properties").write_text("Python=3.11\n", encoding="utf-8")
    dest = tmp_path / "out" / "index.html"
    write_dashboard(results, dest, features_root=tmp_path / "no-features")
    env = (results / "environment.properties").read_text(encoding="utf-8")
    assert "Python=3.11" in env
    assert "Platform.Dashboard.GeneratedMs=" in env
    sidecar = json.loads((results / "platform-run.json").read_text(encoding="utf-8"))
    assert sidecar["generatedMs"]
    html = dest.read_text(encoding="utf-8")
    assert "allureReport" not in html


def test_gherkin_fills_zephyr_when_allure_label_missing(tmp_path: Path) -> None:
    features = tmp_path / "features" / "kyc"
    features.mkdir(parents=True)
    (features / "note.feature").write_text(
        "@kyc @api\nFeature: Notes\n  @KYC-T1092 @smoke\n  Scenario: Customer cannot look up a note\n",
        encoding="utf-8",
    )
    _write_result(
        tmp_path,
        "fail",
        {
            "name": "Customer cannot look up a note",
            "status": "failed",
            "labels": [{"name": "epic", "value": "kyc"}],
        },
    )
    model = build_dashboard_model(tmp_path, features_root=tmp_path / "features")
    assert model["problems"][0]["zephyr"] == "KYC-T1092"
    assert model["problems"][0]["source"] == "kyc/note.feature"


def test_load_cases_collapses_allure_retries(tmp_path: Path) -> None:
    hid = "hist-cashout"
    _write_result(
        tmp_path,
        "try1",
        {
            "name": "Cash-out",
            "status": "broken",
            "retry": True,
            "historyId": hid,
            "start": 1,
            "stop": 10,
            "labels": [{"name": "epic", "value": "debit"}],
        },
    )
    _write_result(
        tmp_path,
        "try2",
        {
            "name": "Cash-out",
            "status": "broken",
            "retry": False,
            "historyId": hid,
            "start": 20,
            "stop": 40,
            "statusDetails": {"message": "TimeoutError: still down"},
            "labels": [{"name": "epic", "value": "debit"}],
        },
    )
    cases = load_cases(tmp_path)
    assert len(cases) == 1
    assert cases[0].retries == 1
    assert cases[0].is_retry is False
    assert cases[0].status == "broken"
    model = build_dashboard_model(tmp_path, features_root=tmp_path / "no-features")
    assert model["total"] == 1
    assert model["broken"] == 1
    assert model["problems"][0]["retries"] == 1


def test_dashboard_html_drops_heatmap_and_keeps_retried_mark(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    _write_result(
        results,
        "one",
        {"name": "A scenario", "status": "passed", "labels": [{"name": "epic", "value": "app"}]},
    )
    html = write_dashboard(results, tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "Heatmap this run" not in html
    assert "in repo" not in html
    assert ">Type<" in html
    assert ">Suite<" in html
    assert "retried" in html
    assert "donut-counts" in html
    assert "failEpic" in html
    assert "data-copy" in html
    assert "Copy pytest" in html
    assert "Failed = assertion" not in html
    assert "assertion mismatch" not in html
    assert "data-page-kind" in html
    assert "data-case" in html
    assert "pytest --zephyr-keys=" in html
    assert "pytest -k test_" in html
    assert "'\\''" not in html
    assert "$env:PYTHONPATH" not in html
    assert "attached on failed and broken only" not in html
    assert "file:// is 500" not in html
    assert "#testresult" not in html
    assert "allure-report/index.html#" not in html
