"""Load Figma API credentials from a local gitignored file.

Preferred path (repo root): ``secrets/figma.env``

Copy from ``secrets/figma.example.env``. Never commit the real file.
Existing process env vars win unless ``override=True``.

``FIGMA_ACCESS_TOKEN`` is the name we document. The Framelink MCP server
reads ``FIGMA_API_KEY`` — after a successful load both are populated from
whichever one was set.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from jira_local_env import find_repo_root  # noqa: E402

_ENV_LINE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
_TRACKED_KEYS = frozenset({"FIGMA_ACCESS_TOKEN", "FIGMA_API_KEY"})


def figma_env_path(repo_root: Path | None = None) -> Path:
    """Return the path to ``secrets/figma.env`` under the repo root."""
    root = repo_root or find_repo_root()
    return root / "secrets" / "figma.env"


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def load_figma_local_env(
    *,
    start: Path | None = None,
    override: bool = False,
) -> Path | None:
    """Populate os.environ from secrets/figma.env. Returns path if the file exists."""
    path = figma_env_path(find_repo_root(start))
    if not path.is_file():
        return None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE.match(line)
        if not match:
            continue
        key, value = match.group(1), _strip_quotes(match.group(2).strip())
        if key not in _TRACKED_KEYS or not value:
            continue
        if not override and (os.environ.get(key) or "").strip():
            continue
        os.environ[key] = value

    token = (os.environ.get("FIGMA_ACCESS_TOKEN") or os.environ.get("FIGMA_API_KEY") or "").strip()
    if token:
        os.environ.setdefault("FIGMA_ACCESS_TOKEN", token)
        os.environ.setdefault("FIGMA_API_KEY", token)

    return path
