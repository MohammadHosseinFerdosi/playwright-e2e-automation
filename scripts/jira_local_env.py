"""Load Platform Jira ATM credentials from a local gitignored file.

Preferred path (repo root): ``secrets/jira_atm.env``

Copy from ``secrets/jira_atm.example.env``. Never commit the real file.
Existing process env vars win unless ``override=True``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_ENV_LINE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
_TRACKED_KEYS = frozenset(
    {
        "JIRA_TOKEN",
        "JIRA_ATM",
        "ZEPHYR_CYCLE_FOLDER",
        "ZEPHYR_ENVIRONMENT",
        "ZEPHYR_CYCLE_MODE",
        "ZEPHYR_CYCLE_KEY",
    }
)


def find_repo_root(start: Path | None = None) -> Path:
    """Walk parents from ``start`` until the repo root (scripts/zephyr_sync.py) is found."""
    here = (start or Path.cwd()).resolve()
    if here.is_file():
        here = here.parent
    for candidate in (here, *here.parents):
        if (candidate / "scripts" / "zephyr_sync.py").is_file():
            return candidate
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    return here


def jira_env_path(repo_root: Path | None = None) -> Path:
    """Return the path to ``secrets/jira_atm.env`` under the repo root."""
    root = repo_root or find_repo_root()
    return root / "secrets" / "jira_atm.env"


def load_jira_local_env(
    *,
    start: Path | None = None,
    override: bool = False,
) -> Path | None:
    """Populate os.environ from secrets/jira_atm.env. Returns path if loaded."""
    path = jira_env_path(find_repo_root(start))
    if not path.is_file():
        return None

    applied = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if key not in _TRACKED_KEYS:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if not value:
            continue
        if not override and (os.environ.get(key) or "").strip():
            continue
        os.environ[key] = value
        applied = True

    return path if applied or path.is_file() else None
