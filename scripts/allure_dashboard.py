#!/usr/bin/env python3
"""Write ``allure-dashboard/index.html`` from ``allure-results/``."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.services.allure_dashboard import write_dashboard  # noqa: E402  # after sys.path insert


def main() -> int:
    """Build the Platform dashboard next to Allure raw results."""
    results = REPO_ROOT / "allure-results"
    dest = REPO_ROOT / "allure-dashboard" / "index.html"
    if not results.is_dir():
        print("No allure-results/ - run pytest first.", file=sys.stderr)
        return 1
    path = write_dashboard(results, dest)
    print(f"Platform dashboard -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
