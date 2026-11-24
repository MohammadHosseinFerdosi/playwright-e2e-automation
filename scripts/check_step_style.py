#!/usr/bin/env python3
"""Fail lint when step definition files break the thin-step contract.

Enforced on ``tests/bdd/steps/*.py`` (see ``.cursor/rules/step-definitions.mdc``):

- no ``if`` / ``for`` / ``while`` / ``try`` statements (module level or in functions)
- no bare ``assert`` — checks go through ``tests/services/assert_report.py``
- max ``MAX_STATEMENTS`` statements per function body

``LEGACY_ALLOWLIST`` files predate the rule and are skipped — never add to it.
An allowlisted file that becomes clean fails the check until its entry is
removed, so the list can only shrink (Phase-2 refactoring burns it down).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

STEPS_DIR = Path("tests/bdd/steps")
MAX_STATEMENTS = 8

# Phase-2 burn-down list — remove entries as files are refactored. NEVER add.
# Empty when every tests/bdd/steps/*.py meets the thin-step contract.
LEGACY_ALLOWLIST: frozenset[str] = frozenset()


RULE_DOC = ".cursor/rules/step-definitions.mdc"

_CONTROL_FLOW: dict[type[ast.AST], str] = {
    ast.If: "if",
    ast.For: "for",
    ast.AsyncFor: "for",
    ast.While: "while",
    ast.Try: "try",
}
# ast.TryStar is 3.11+; keep this 3.10-safe for basedpyright pythonVersion.
_try_star = getattr(ast, "TryStar", None)
if isinstance(_try_star, type):
    _CONTROL_FLOW[_try_star] = "try*"


def _body_statement_count(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count top-level statements in a function body, excluding the docstring."""
    body = func.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    return len(body)


def check_file(path: Path) -> list[str]:
    """Return one 'line: message' violation string per broken contract rule."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        keyword = _CONTROL_FLOW.get(type(node))
        if keyword is not None and isinstance(node, ast.stmt):
            violations.append(
                f"{node.lineno}: `{keyword}` statement — move branching/loops/error "
                f"handling to tests/services/ ({RULE_DOC})"
            )
        elif isinstance(node, ast.Assert):
            violations.append(
                f"{node.lineno}: bare `assert` — use tests/services/assert_report.py helpers"
            )
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            count = _body_statement_count(node)
            if count > MAX_STATEMENTS:
                violations.append(
                    f"{node.lineno}: `{node.name}` has {count} statements "
                    f"(max {MAX_STATEMENTS}) — extract logic to tests/services/"
                )
    return violations


def main() -> int:
    """Check every step file; report violations and stale allowlist entries."""
    step_files = sorted(STEPS_DIR.glob("*.py"))
    if not step_files:
        print(f"ERROR: no step files found under {STEPS_DIR} — wrong working directory?")
        return 1

    failed = False
    for path in step_files:
        violations = check_file(path)
        if path.name in LEGACY_ALLOWLIST:
            if not violations:
                print(
                    f"{path}: now clean — remove {path.name!r} from LEGACY_ALLOWLIST "
                    f"in {__file__.rsplit('/', 1)[-1]} so it stays enforced"
                )
                failed = True
            continue
        for violation in violations:
            print(f"{path}:{violation}")
            failed = True

    if failed:
        print(f"\nThin-step contract failed — see {RULE_DOC}")
        return 1
    checked = len(step_files) - len(LEGACY_ALLOWLIST)
    print(f"Thin-step contract OK ({checked} checked, {len(LEGACY_ALLOWLIST)} legacy skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
