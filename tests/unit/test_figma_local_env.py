"""Unit tests for scripts/figma_local_env.py."""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "figma_local_env.py"


@pytest.fixture(scope="module")
def fle() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("figma_local_env", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["figma_local_env"] = mod
    spec.loader.exec_module(mod)
    return mod


def _fake_repo(tmp_path: Path) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "zephyr_sync.py").write_text("# marker\n", encoding="utf-8")


def test_load_figma_local_env(
    fle: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_repo(tmp_path)
    (tmp_path / "secrets" / "figma.env").write_text(
        "FIGMA_ACCESS_TOKEN='figd_secret-token-value'\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("FIGMA_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("FIGMA_API_KEY", raising=False)

    loaded = fle.load_figma_local_env(start=tmp_path)
    assert loaded == tmp_path / "secrets" / "figma.env"
    assert os.environ["FIGMA_ACCESS_TOKEN"] == "figd_secret-token-value"
    assert os.environ["FIGMA_API_KEY"] == "figd_secret-token-value"


def test_process_env_wins(
    fle: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_repo(tmp_path)
    (tmp_path / "secrets" / "figma.env").write_text(
        "FIGMA_ACCESS_TOKEN=from-file\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "from-shell")
    monkeypatch.setenv("FIGMA_API_KEY", "from-shell-key")

    fle.load_figma_local_env(start=tmp_path)
    assert os.environ["FIGMA_ACCESS_TOKEN"] == "from-shell"
    assert os.environ["FIGMA_API_KEY"] == "from-shell-key"
