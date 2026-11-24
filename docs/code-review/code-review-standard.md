# Code Review Standard — Platform Playwright Automation

PR-review checklist for `playwright-e2e-automation/`. Supersedes the old Robot Framework MR
checklist. For deeper rationale/rules, see [`AGENTS.md`](../../AGENTS.md),
[`.cursor/rules/pytest-architecture.mdc`](../../.cursor/rules/pytest-architecture.mdc),
[`.cursor/rules/python-code-style.mdc`](../../.cursor/rules/python-code-style.mdc),
[`.cursor/rules/step-definitions.mdc`](../../.cursor/rules/step-definitions.mdc), and
[`.cursor/rules/gherkin-style.mdc`](../../.cursor/rules/gherkin-style.mdc). 🚫 marks a blocker;
unmarked items should be fixed or get a tracked follow-up.

## MR hygiene

- [ ] MR purpose is clear (what / why / where); description matches the diff.
- 🚫 Unrelated work mixed in (new coverage + an unrelated refactor in the same MR).
- [ ] Test-run evidence attached (Allure/JUnit output or CI link) for the touched slice.
- [ ] Branch name follows the required convention (checked early — catching it at final gate
      is too late).

## Architecture & API

- 🚫 HTTP only via `ApiClient` ([`tests/api/client.py`](../../tests/api/client.py)), obtained
  from its fixture — never a raw `httpx.Client()` or module-level singleton.
- 🚫 No hardcoded URLs/tokens/phone numbers/`Platform-Version` — use
  `tests/config/settings.py` / `tests/config/constants.py`.
- 🚫 New endpoints return the `{status_code, body}` envelope only; JSON parsed into a
  `pydantic.BaseModel` at the boundary, not passed around as a raw dict. Do not add
  extra top-level keys beside that envelope.
- 🚫 Response parsing catches `pydantic.ValidationError`, not a bare `Exception`.
- [ ] New POST/PUT bodies are a small request `BaseModel` + `to_payload()`, not an inline dict.
- [ ] Each API client method is one HTTP operation (one path + verb).
- [ ] Correct `ApiSide` used (`APP`/`MICROSERVICE`/`DASHBOARD`/`GENERAL`); no duplicate base
      URL. Paths go through `ms_path` / settings — no full URL in the path.
- [ ] Required headers for that side are set (`User-Id` on microservice when the endpoint
      needs it). Extra headers are not copied onto every call.
- [ ] HTTP timeout comes from settings — not `None` / infinite, not a one-off literal.
- 🚫 Steps do not build URLs, headers, or request bodies — that stays in `tests/api/`.
- [ ] New code lands in the right layer (api / bdd steps / services / ui pages), per
      `pytest-architecture.mdc`.
- [ ] Idempotency-sensitive endpoints (purchase/refund/pay) have a repeat-call check where
      the domain requires it.

## Fixtures & test data

- 🚫 New fixtures use `yield` + `close()` (or a context manager) — resource released even on
  failure.
- 🚫 Data-creating tests (purchase/refund/business/wallet) clean up via fixture/factory
  teardown (`yield` + `close()` / Collect-all / equivalent). No leftover suite-global cleanup
  modules.
- [ ] No shared mutable state between tests (xdist safety).
- 🚫 Every scenario is independent — it must not need another scenario's leftover data or
      a fixed run order (`pytest -n auto` shuffles workers).
- 🚫 Tests that mutate **shared live UAT** (config, routing, balances other workers use)
      pin `pytest.mark.xdist_group(...)` and run with `-n auto --dist loadgroup`
      so workers do not race.
- [ ] Factories (`UserFactory`/`BusinessFactory`) used over hardcoded fixed test data.
- 🚫 Magic numbers and unexplained strings live in `tests/config/constants.py` or
      `data/CONSTANTS.yaml`, not in the test body.

## Python style & thin steps

- 🚫 Every new/edited function under `tests/` and `scripts/` has type hints and a Google-style
  docstring (`python-code-style.mdc`). Ruff `ANN`/`D` catch omissions — do not add `# noqa`
  to silence them.
- 🚫 Step files under `tests/bdd/steps/` stay thin: max 8 statements, no `if`/`for`/`while`/
  `try`, no bare `assert`. Branching, loops, and assertions belong in `tests/services/`
  (`step-definitions.mdc`, enforced by `scripts/check_step_style.py` via `make lint`).
- 🚫 Never grow the empty baselines — do not add entries to `pyproject.toml` per-file-ignores
  for style debt, and do not add files to `LEGACY_ALLOWLIST` in `scripts/check_step_style.py`.
- [ ] Complexity (`C901` ≤ 10) and statement/branch caps (`PLR0915`/`PLR0912`) stay green;
      extract a helper/service instead of silencing with `# noqa`.
- [ ] Public API/service functions: Google docstring covers inputs, return value, and
      side-effects (creates money, mutates live config, leaves a row).

## Playwright / UI

- 🚫 No `page.wait_for_timeout`, `time.sleep`, or leftover `page.pause()` — poll until a
  condition (Playwright auto-wait, or a service helper).
- [ ] One `BrowserSession` per test via fixture; trace kept on failure, discarded on pass.
- [ ] Screenshot (and video, if enabled) captured on UI failure alongside the trace.
- [ ] New pages inherit `BasePage`; locators centralized as class attributes; prefer
      `tests/ui/labels/` over raw Farsi strings.

## BDD / tagging

- 🚫 No Farsi literals, **raw SQL** (`SELECT … FROM …`), HTTP paths, or
  Playwright/pytest/selector vocabulary in `.feature` files — business language only.
  Domain table/field/status names that **are** the assertion stay (see
  `gherkin-style.mdc` “Technical contract details”). N similar Thens: capture the
  tail; do not rename the sentence
  ([`.cursor/skills/bdd-step-regex/examples.md`](../../.cursor/skills/bdd-step-regex/examples.md)
  “N similar Thens”).
- 🚫 Every scenario **resolves** to exactly one `@high`/`@medium`/`@low`, exactly one
  `@api`/`@e2e`, and exactly one `@smoke`/`@regression`, plus story + domain + feature.
  Extra tags (behavior, risk-area) never replace those axes. Spelling is exact
  (`@high`, not `@High` / `@severity:high` / `@sanity`).
- 🚫 Feature tag `{domain}_{capability}` is unique per `.feature` file and registered in
  `pyproject.toml` in the same MR. Story is `@PROJECT-####` and Zephyr is `@PROJECT-T####`
  for **that team's** Jira board. Sync with `scripts/zephyr_sync.py --project <BOARD>`.
- [ ] Every scenario has `Given`, `When`, and `Then` (extra `And`/`But` for more of the
      same is fine) — no keyword skipped by folding a precondition into the `When` text
      (e.g. `When ... without a valid token` with no `Given` establishing that state), and
      no empty `Given` added just to fill the slot.
- 🚫 New `parsers.re` is not a full-sentence `|` list, and a new `@given`/`@when`/`@then`
  is not added when an existing family stem already matches — rewrite Gherkin onto the
  stem or extend the dispatch dict
  ([`.cursor/skills/bdd-step-regex/SKILL.md`](../../.cursor/skills/bdd-step-regex/SKILL.md)).
- [ ] One behavior per scenario; `Scenario Outline` over cloned scenarios.
- [ ] Severity matches impact: `high` = money, auth, or data integrity (idempotency /
      duplicate / broken state); `medium` = real gap with a workaround; `low` = copy,
      optional fields, no business break.

## Assertions & data

- 🚫 Business-logic checks go through `AssertionReport` / `assert_*` helpers in
  `tests/services/assert_report.py`, not bare `assert`; PII masked.
- 🚫 HTTP status is the real code (`200`, `422`) — not “not 200”, not `2xx` / `4xx` / `5xx`.
- 🚫 Negative-path scenarios validate the actual error code **and** message, not just
  "it failed".
- [ ] Happy path checks business invariants (required fields, amounts), not only HTTP status.
- [ ] FAIL text is actionable (expected vs actual, enough to debug without re-running).
- [ ] DB queries fetch only needed fields, log no sensitive columns, and are parameterized
      (no string-built SQL). After a write, poll until the row is visible — do not assume
      the first read is enough.

## Secrets

- 🚫 No real credentials in `secrets/*` (only `*.example.*`) or in
  `config/environment-stage.yaml`.
- [ ] No `.env` with real values committed.

## Flakiness & CI

- 🚫 Known-flaky tests are disclosed in the MR, not merged silently (CI has no auto-retry).
- 🚫 `make lint`, `make typecheck`, and `make collect` pass locally before every commit/push.
  CI also runs `make lint` + `make typecheck` in the `Lint and typecheck` validate-stage job
  (`.gitlab-ci.yml`) — a red local gate will be a red MR. Paste the output if asked; don't
  just say it passed.
- 🚫 A CI skip because gitignored secrets are missing is not a UAT pass — attach a local
  Allure/JUnit run of the slice on the MR.
- 🚫 Do not `pytest.skip` a live path because UAT/provider is down — delete the scenario or
  let it fail. Skip is not a pass.
- [ ] The new test's tag combination actually matches an existing `.gitlab-ci.yml` job.
- [ ] Rate-limit-sensitive calls back off/retry rather than failing outright.
- [ ] Generated/random test data is traceable (logged id, or built from a named factory).

## Shared files

These are **all-team** files. An MR may add *its* marker or *its* domain row — it must not
rewrite, delete, or restyle other teams' entries.

- 🚫 `pyproject.toml` markers, `tests/conftest.py` / `tests/conftest_reporting.py`,
  `tests/api/client.py`, `tests/api/ms_paths.py`, `config/environment-stage.yaml`
- 🚫 `docs/framework/STATUS.md` and `migration-status.md` — **your domain row only**

## Naming & tooling

- [ ] Clear, action+outcome names; no typos; identifiers stay `snake_case` in Python
      (`provider_id`, not `tracking_CODE` / mixed `providerId` in the same layer).
- 🚫 `# noqa: <code>` is always scoped to one rule with a real reason — no blanket ignores.

## Before approving

- [ ] No 🚫 item outstanding; branch name follows convention; MR scope matches its
      description; layers, tags, cleanup, and assertions are sufficient for the slice.
