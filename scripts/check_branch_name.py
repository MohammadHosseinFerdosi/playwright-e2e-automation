#!/usr/bin/env python3
"""Fail CI when the Git branch name does not match repo convention.

Shapes (no team whitelist):
  feat|fix|chore|hotfix|docs / JIRA-123-slug   (Jira key UPPERCASE)
  chore|hotfix|docs / team-slug                (any lowercase team)
"""

from __future__ import annotations

import os
import re
import sys

PATTERN = re.compile(
    r"^((feat|fix|chore|hotfix|docs)/[A-Z][A-Z0-9]+-[0-9]+-[a-z0-9]+(-[a-z0-9]+)*|"
    r"(chore|hotfix|docs)/[a-z][a-z0-9]*(-[a-z0-9]+)+)$"
)


def main() -> int:
    """Validate the CI branch name against the repo naming convention."""
    branch = os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME") or os.environ.get(
        "CI_COMMIT_REF_NAME", ""
    )
    default = os.environ.get("CI_DEFAULT_BRANCH", "staging")
    print(f"Checking branch: {branch!r} (default={default!r})")

    if not branch:
        print("ERROR: could not determine branch name from CI variables")
        return 1
    if branch == default:
        print(f"Default branch ({branch}) — OK")
        return 0
    if PATTERN.fullmatch(branch):
        print(f"Branch name OK: {branch}")
        return 0

    print(f"ERROR: Branch {branch!r} does not match the naming convention.")
    print()
    print("Ticketed:  <feat|fix|chore|hotfix|docs>/<JIRA-KEY>-<number>-<slug>")
    print("  e.g.     feat/ALPHA-1234-bill-inquiry-tests")
    print("Team:      <chore|hotfix|docs>/<team>-<slug>  (team lowercase, any name)")
    print("  e.g.     chore/infra-upgrade-ci-runners")
    print()
    print("feat/fix require a Jira key (UPPERCASE). Underscores are not allowed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
