"""Unit tests for scripts/jira_local_env.py"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "jira_local_env.py"


@pytest.fixture(scope="module")
def jle() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("jira_local_env", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["jira_local_env"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_load_jira_local_env(
    jle: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "jira_atm.env").write_text(
        "JIRA_ATM=https://jira.example/rest/atm/1.0\nJIRA_TOKEN='secret-token-value'\n",
        encoding="utf-8",
    )
    # Pretend repo root is tmp_path (has scripts/zephyr_sync.py marker)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "zephyr_sync.py").write_text("# marker\n", encoding="utf-8")

    monkeypatch.delenv("JIRA_TOKEN", raising=False)
    monkeypatch.delenv("JIRA_ATM", raising=False)

    loaded = jle.load_jira_local_env(start=tmp_path)
    assert loaded == secrets / "jira_atm.env"
    assert os.environ["JIRA_ATM"] == "https://jira.example/rest/atm/1.0"
    assert os.environ["JIRA_TOKEN"] == "secret-token-value"


def test_process_env_wins(
    jle: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "jira_atm.env").write_text(
        "JIRA_ATM=https://from-file\nJIRA_TOKEN=from-file\n",
        encoding="utf-8",
    )
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "zephyr_sync.py").write_text("# marker\n", encoding="utf-8")

    monkeypatch.setenv("JIRA_TOKEN", "from-shell")
    monkeypatch.setenv("JIRA_ATM", "https://from-shell")

    jle.load_jira_local_env(start=tmp_path)
    assert os.environ["JIRA_TOKEN"] == "from-shell"
    assert os.environ["JIRA_ATM"] == "https://from-shell"
