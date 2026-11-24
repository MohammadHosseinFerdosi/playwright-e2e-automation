# Target Framework

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.10 or 3.11 |
| Runner | pytest |
| BDD | pytest-bdd + `.feature` files |
| API | httpx (+ pydantic optional) |
| UI | Playwright (native Python, Page Object Model) |
| Parallel | pytest-xdist |
| Reporting | allure-pytest + JUnit XML |
| Config | pydantic-settings ← `config/environment-stage.yaml` |
| Fake data | Faker + reuse `src/library/faker_utils.py` |
| DB | reuse pymongo, mysql-connector, psycopg2, redis |

## Folder structure

```
tests/
├── conftest.py
├── config/settings.py
├── api/client.py
├── api/{team}/
├── services/
├── ui/pages/
├── bdd/features/
└── bdd/steps/
```

Pytest markers/config live in root [`pyproject.toml`](../../pyproject.toml) (`[tool.pytest.ini_options]`).

## Dependencies (foundation)

```
pytest pytest-bdd pytest-xdist httpx pydantic pydantic-settings pyyaml playwright faker allure-pytest
```

## BDD supports

- **Scenario Outline + Examples** — same test, different data
- **Data tables** — inline tables in steps
- **API scenarios** — primary use case (most Platform tests)
- **UI scenarios** — Playwright via page objects
- **Large matrices** — YAML + `@pytest.mark.parametrize` (e.g. LMS)

Gherkin writing rules (business-readable language, tag ordering, spacing/indentation,
one-behavior-per-scenario, etc.) are enforced by `.cursor/rules/gherkin-style.mdc` — read it
before writing or reviewing any `.feature` file.

## API client design

Port `src/services/backend/session-service.resource`:

| api_call_side | Base URL |
|---------------|----------|
| app | APP_BASE_URL + GATEWAY_PATH |
| microservice | MICROSERVICE_BASE_URL |
| dashboard | DASHBOARD_BASE_URL + GATEWAY_PATH |

Return shape: `{"status_code": int, "body": dict | None}`

## UI login

- **Default:** API login (inject tokens → reload) — fast
- **E2E auth tests only:** full UI login + OTP from Redis

## Markers (`pyproject.toml`)

```ini
markers =
    high: severity high
    medium: severity medium
    low: severity low
    api: API test
    e2e: UI end-to-end
    smoke: smoke suite
    regression: regression suite
```

Run: `pytest -m "high and api" tests/`

## Tag taxonomy — required axes (decided, enforce from day 1)

Every new scenario MUST resolve to these axes (via Feature tags + scenario tags).
Retrofitting tags later is far harder than requiring them now — see the 63 untracked
`robot:skip` scenarios in the legacy suite as the cautionary example.

| Axis | Values | Purpose |
|------|--------|---------|
| `story` | `@ALPHA-####` or other `@PROJECT-####` (e.g. `@KYC-2050`; **not** `@…-T…`) | Zephyr/Jira issueLinks; prefer once on `Feature:` |
| `severity` | `high` / `medium` / `low` | risk-based run selection |
| `type` | `api` / `e2e` | split fast API runs from slower UI runs |
| `suite` | `smoke` / `regression` | deploy gate vs full nightly coverage |
| `domain` | `wallet` / `payment` / `kyc` / … | ownership & targeted reruns |
| `feature` | `{domain}_{capability}` e.g. `wallet_transfer` | one unique tag per `.feature` file |

**Placement:** put story + type + suite + domain + feature on `Feature:` once when they
apply to the whole file; put `@positive`/`@negative` and severity on each scenario when
they differ (story on the scenario only when stories differ across the file). Do not
repeat Feature-level tags on every scenario. Register each new feature marker in
`pyproject.toml`. Full rules:
[`.cursor/rules/gherkin-style.mdc`](../../.cursor/rules/gherkin-style.mdc).

Add a `domain` marker (and each file’s `feature` marker) in `pyproject.toml` as domains
are migrated.

## OOP conventions — no module-level globals, ever

This directly fixes the current `_connection` / `_cursor` global-state pattern in
`src/library/mysql_db.py` (and mongo/postgres/redis equivalents), which is unsafe under
parallel execution.

- **`ApiClient`** (`tests/api/client.py`) — one class replaces `session-service.resource`
  entirely. Holds ONE reusable `httpx.Client`, not a new session per call. Path/header
  building are private methods.
- **DB clients** (`tests/services/db/`) — one class per engine (`MySQLClient`,
  `MongoClient`, `RedisClient`, `PostgresClient`), each instance owning its own
  connection, ideally as a context manager (`with MySQLClient(settings) as db:`).
- **Factories** (`tests/services/factories.py`) — `UserFactory`, `BusinessFactory` as
  classes, not standalone keyword functions.
- Every one of these is instantiated through a **pytest fixture**, never imported as a
  module-level singleton — this is what makes parallel execution safe (see below).

## Page Object Model conventions

- `tests/ui/pages/base_page.py` — one `BasePage` class with shared waits, navigation,
  screenshot-on-failure. Every page inherits from it.
- Locators live as class attributes (`LOCATORS = {...}` or typed `Locator` fields) —
  ONE place per page to update when the UI changes.
- Actions are typed methods, not raw Playwright calls scattered in step files.
- Native Playwright only — this is where the Selenium stack retires (no dual-stack UI).

## Three-angle testing (decided pattern — formalize, don't invent per-test)

For any meaningful business event (transfer, purchase, refund…), verify from all three
angles where applicable:

1. **API** — call the endpoint, assert `status_code` + response body/schema
2. **DB** — query the underlying store, confirm state actually changed
3. **UI** — reload the screen/dashboard the user would see, confirm it matches

This is already done informally in the legacy suite (e.g. wallet transfer checks API + DB
+ dashboard) — the new framework should apply it deliberately, not as an afterthought.

## Parallel execution — pytest-xdist, fixture-scoped, no shared state

Legacy uses `pabot` with hand-tuned process counts (`--processes 10` for wallet/payment,
`--processes 20 --testlevelsplit` for LMS credit-core — see `qa-script-api.sh`).

New framework: `pytest -n auto` (or explicit `-n <N>` in CI). This is safe **only if**:

- `ApiClient` and DB client instances come from fixtures (function or session scoped as
  appropriate) — never a module-level global
- Each xdist worker gets its own fixture instances automatically — no shared connection
  ever crosses worker boundaries
- Test data is isolated per test (fresh user/business via factories) — already good
  practice in the legacy suite, carry it forward

xdist merges JUnit/Allure results automatically — no manual `rebot` merge/strip step
needed.

## Improve, don't clone (migration quality — locked 2026-07-16)

Robot suites are the **behavior** source of truth, not a structure template. Every port
must leave `tests/` more reusable than the Robot original: Scenario Outline for data
variants, thin shared steps, pydantic response/config models, class+fixture clients,
poll-until-condition instead of fixed `Sleep`. Enforced by
`.cursor/rules/migration-quality.mdc` and the playbook Definition of Done.

## Jira / Zephyr Scale integration

**Tool chosen:** Zephyr Scale (ATM API) on Platform Jira Data Center. Default project
**ALPHA**; other boards (`KYC`, `SET`, …) pass `--project <KEY>`.

| Piece | Status |
|-------|--------|
| Create/update BDD test cases from `.feature` | **Built** — `scripts/zephyr_sync.py` (+ optional Postman helper `scripts/zephyr_sync_server.py`) |
| Team how-to (PAT, tags, bulk sync, result push, prompts) | [`docs/zephyr/Zephyr-Scale-Complete-Guide.pdf`](../zephyr/Zephyr-Scale-Complete-Guide.pdf) · skill [`.cursor/skills/zephyr/SKILL.md`](../../.cursor/skills/zephyr/SKILL.md) |
| Push pytest Pass/Fail into a Zephyr test cycle | **Built** — opt-in pytest plugin `tests/zephyr_result_collector.py` (`-p tests.zephyr_result_collector` + `ZEPHYR_CYCLE_NAME`; `@PROJECT-T####` scenarios) |

```
pytest-bdd .feature files (living test-case docs)
    → @zephyr / @PROJECT-T#### + scripts/zephyr_sync.py [--project KYC] → Zephyr Scale cases
    → pytest -p tests.zephyr_result_collector → new Zephyr test cycle (Pass/Fail/Blocked)
```
