# Contributing

Human-facing quick start. AI agents (Cursor, Claude, etc.) should start at
[`AGENTS.md`](AGENTS.md) instead — it carries the same rules in agent-instruction form.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"      # project deps + ruff + pre-commit
pre-commit install
playwright install chromium
```

Or with `make`: `make install-dev && make browsers`.

## Before you open an MR

1. `make lint` — ruff must pass (or let `pre-commit` catch it on commit).
2. `make typecheck` — basedpyright must pass.
3. `make collect` — confirm pytest can still collect everything (`pytest --collect-only`).
4. Run the suite (or the slice you touched) — see README's *Run* section for marker examples.
5. Update `docs/framework/STATUS.md` if your change affects tracked state — it goes stale
   fast if forgotten. See [`docs/code-review/code-review-standard.md`](docs/code-review/code-review-standard.md)
   for the full pre-MR checklist.

## Adding a test — where things go

| Adding... | Goes in | Notes |
|-----------|---------|-------|
| A new HTTP call | `tests/api/{team}/{endpoint}.py` | Thin — returns `{status_code, body}`, no assertions |
| A new scenario | `tests/bdd/features/{domain}/{name}.feature` | Prefer `Scenario Outline` over cloned scenarios |
| Step definitions | `tests/bdd/steps/{domain}_steps.py` | Thin orchestration only — no raw HTTP, no CSS selectors |
| Reused business logic | `tests/services/` | Only when logic is shared across scenarios |
| A new UI page | `tests/ui/pages/...` | Inherit `BasePage`; see [`docs/framework/ui-pom-cookbook.md`](docs/framework/ui-pom-cookbook.md) |
| A new fixture | `tests/conftest.py` | Never a module-level global — always a fixture (xdist safety) |

Full rules: [`.cursor/rules/pytest-architecture.mdc`](.cursor/rules/pytest-architecture.mdc)
(layer boundaries) and [`.cursor/rules/gherkin-style.mdc`](.cursor/rules/gherkin-style.mdc)
(Gherkin style + required tag axes).

## Style

- Formatting/linting: `ruff format` + `ruff check` (config in `pyproject.toml`), enforced via
  `pre-commit`.
- No module-level HTTP/DB/factory singletons — everything is a class instantiated through a
  pytest fixture. This is what keeps `pytest -n auto` (xdist) safe; see
  `docs/framework/target-framework.md` for the rationale.
- Every scenario must resolve to **story** (`@PROJECT-####`) + **severity** + **type** +
  **suite** + **domain** + **feature** — see [`AGENTS.md`](AGENTS.md) and the tag taxonomy
  in [`docs/framework/target-framework.md`](docs/framework/target-framework.md) /
  [`.cursor/rules/gherkin-style.mdc`](.cursor/rules/gherkin-style.mdc).
- Mask PII (phone, NID, IBAN) in logs and assertion messages.

## Secrets

Never commit real files under `secrets/` — only `*.example.yaml` / `*.example.env`. Copy the
example, fill in real values locally (Jira: `jira_atm.env`; Figma: `figma.env`), and confirm
`git status` doesn't show it before pushing.
That includes `secrets/jira_atm.env` and `secrets/figma.env`. The pre-commit hook
`no-real-secrets` blocks this automatically once installed.

Figma (Cursor + Claude Code): [`docs/ai/figma-setup.md`](docs/ai/figma-setup.md).

## Questions

Start with [`AGENTS.md`](AGENTS.md) → [`docs/framework/STATUS.md`](docs/framework/STATUS.md)
for current project state, or [`docs/framework/README.md`](docs/framework/README.md) for the
full doc index.
