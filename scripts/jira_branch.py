"""Resolve a Jira issue key from the current Git branch name.

Ticketed branches (see ``scripts/check_branch_name.py``)::

    feat|fix|chore|hotfix|docs / PROJECT-1234-slug

Team-only branches (``chore/superapp-…``) have no issue key — return empty.
"""

from __future__ import annotations

import os
import re
import subprocess
from functools import lru_cache

_TICKETED_BRANCH = re.compile(r"^(?:feat|fix|chore|hotfix|docs)/([A-Z][A-Z0-9]+-[0-9]+)-")


def issue_key_from_branch_name(branch: str) -> str:
    """Return ``PROJECT-1234`` from a ticketed branch name, else empty."""
    match = _TICKETED_BRANCH.match((branch or "").strip())
    return match.group(1) if match else ""


def current_git_branch() -> str:
    """Return the current branch from CI env or ``git rev-parse``."""
    for name in ("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME", "CI_COMMIT_REF_NAME"):
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or "").strip()


@lru_cache(maxsize=1)
def branch_issue_key() -> str:
    """Return the Jira issue key encoded in the current branch, else empty."""
    return issue_key_from_branch_name(current_git_branch())
