# Migration Inventory — everything beyond test cases

> Companion to [migration-status.md](migration-status.md), which tracks `features/*.robot` →
> `.feature` domain-by-domain. **This file tracks everything else** — libraries, services, UI,
> data, config, and CI/reporting infrastructure that the Robot suite depends on but that isn't
> a test case itself. Goal: nothing gets forgotten just because it isn't a `.robot` file.
>
> Not a migration order, not a commitment to migrate everything — some rows are legitimately
> `deferred` or `out of scope`. Update the **Status** column as work happens; add a short note
> + date when a row changes status so this stays a reliable audit trail, not just a wishlist.
>
> Status values: `not started` · `in progress` · `done` · `deferred` (needs prerequisite) ·
> `out of scope` (decided not to migrate, with reason)

## 1. Custom Python keyword libraries (`src/library/*.py`)

These carry real business logic, not just glue — need an equivalent Python module in `tests/`,
not a literal import (most have a hard `from robot.api.deco import keyword` dependency).

| File | Purpose | Target | Status |
|------|---------|--------|--------|
| `faker_utils.py` | Fake Iranian cell numbers / national codes | `tests/services/factories.py` (`_fake_business`) | done — reimplemented with `Faker`, not ported literally |
| `rounding.py` | `round_half_up`/`round_half_down` — **financial rounding rules** | `tests/services/rounding.py` (not created) | not started |
| `rsa-encryption.py` | RSA encrypt/decrypt (signed payloads / OTP) | TBD | not started |
| `mysql_db.py`, `postgres_db.py`, `mongo_db.py`, `redis_db.py` | Module-global `_connection`/`_cursor` DB clients | `MySQLClient`/`PostgresClient`/`MongoDbClient`/`RedisClient` classes + fixtures | done 2026-07-31 for core paths — Redis sentinel/cluster/TLS still not ported |
| `type_converters.py` | Mongo `ObjectId`/`Binary` conversions | alongside `MongoClient` | not started |
| `find_icon.py`, `image_utils.py` | OpenCV SIFT/ORB icon-matching in screenshots | TBD — decide if Playwright locators replace this outright | not started (needs decision) |
| `solve_captcha.py` | `easyocr` CAPTCHA solving | TBD | not started (needs decision) |
| `allocate_utils.py`, `change_excel.py` | Generate `.xlsx` import templates for LMS allocation | TBD | deferred — LMS domain deferred |
| `installment_date_utils.py` | Iranian-calendar (`jdatetime`) installment date generation | TBD | deferred — LMS domain deferred |
| `prometheus.py` | Push custom metrics to Prometheus Pushgateway from test runs | TBD | not started |
| `browser_downloader.py` | Selenium/browser driver management | out of scope — Playwright manages its own browsers | out of scope |

## 2. Backend orchestration services (`src/services/backend/*.resource`)

| File | Purpose | Target | Status |
|------|---------|--------|--------|
| `session-service.resource` | `Create A Session`/`Path Builder`/header building | `tests/api/client.py` (`ApiClient`) | done |
| `auth-service.resource` | `Login For Business`/`Login To Dashboard`/`Login To App` | `tests/services/auth.py` — `login_business()` + `login_to_app()` done | in progress — dashboard login not started |
| `fresh-business-initializer-service.resource` | Fresh business creation | `tests/services/factories.py` (`BusinessFactory`) | done |
| `fresh-user-initializer-service.resource` | **`UserFactory` source** — fresh/predefined user generation with retry-until-unique against `user_db`/`switch_credit_db` | `tests/services/factories.py` (`UserFactory`) | done 2026-07-31 — `create()` + `create_predefined()` |
| `rounding.py` | Financial round half up/down | `tests/services/rounding.py` | done 2026-07-31 |
| `clean-data.resource` Reproduce Amount | Sweep one customer's wallets | `tests/services/clean_data.py` | done 2026-07-31 focused path; full multi-DB wipe still out of scope |
| `user-wallet-initializer-service.resource` | User/business wallet creation + charging + **`Collect All Amount For Tear Down`** balance-sweep teardown | `tests/services/wallet_initializer.py` | done — 2026-07-31 customer + business create/charge + teardown (business-transfer + Nemo config search); Nemo cash-in not needed for charge path |
| `import-allocation.resource` | LMS loan-allocation orchestration (uses `allocate_utils.py`/Excel templates) | TBD | deferred — LMS domain deferred |
| `clean-data.resource` (28 KB) | Mongo cleanup across Wallet Provider / Refund / Topup / Debt-Collection / Credit-Account / Report-Mng — backs the Cortex app's "close/clean account" feature | TBD | not started — test-hygiene tooling, not test logic |
| `purchases.resource` | Wallet/DPG purchase + ticket-setting helpers for a fresh or existing user | `tests/services/purchases.py` | done 2026-07-31 — wallet verified purchase + business settings; DPG card pay left to call sites |
| `ipg-mock-assigning.resource` | Assign/unassign a mock PSP terminal to a business | `tests/services/ipg_mock.py` | done 2026-07-31 — assign + HTTP callbacks; Mongo teardown delete deferred to B5 |
| `mock-pay-service.robot` | End-to-end mocked-PSP purchase flow (see `docs/mock-pay-service.md`) | `IpgMockService` + purchase APIs + Mongo helpers | done 2026-07-31 — compose in scenarios when payment team ports mock-pay features |
| `amount.resource`, `value-handler.resource`, `date-time-service.resource`, `convert-to-persian-digit.resource` | Small formatting helpers (amount separators, epoch conversion, Persian digits) | inline as needed when the domain that uses them is ported | not started |
| `LMS/credit-core/*.resource`, `LMS/installment/*.resource` (+ bank-specific JSON payload models: Saderat/Mellat/Tejarat) | Deep bank-integration installment logic | TBD | deferred — LMS domain deferred |

## 3. Database & queue service layer (`src/services/db/`, `src/apis/db/`)

| File | Purpose | Target | Status |
|------|---------|--------|--------|
| `mysql-db-service.resource` | MySQL query keywords | `MySQLClient` class | done — 2026-07-16; `fetch_all`/`fetch_one`/`execute_query` + per-db config (`wallet_provider_db` / `general_ledger_db` overrides). Table/describe/count helpers not ported (unused by UserFactory / wallet total-balance path) |
| `postgres-db-service.resource` | Postgres query keywords | `PostgresClient` class | done 2026-07-31 — collateral + treasury handlers |
| `mongo-db-service.resource` (28 KB) | MongoDB query keywords | `MongoDbClient` class | done 2026-07-31 — find/find_one/insert/update/delete/count (core); aggregate/indexes later if needed |
| `redis-db-service.resource` (24 KB) | Redis key/OTP lookups | `RedisClient` class | partial — standalone + second_standalone + get/set; sentinel/cluster/TLS not ported |
| `ipg-mock-assigning` / mock-pay Mongo steps | purchase + IPG token lookup / terminal delete | `IpgMockService` + `MongoDbClient` | done 2026-07-31 helpers |
| `prometheus.resource` | Robot-side Prometheus wrapper around `library/prometheus.py` | see §1 | not started |
| `db/rabbit-mq/publish-message-rabbit-mq.resource`, `get-message-rabbit-mq.resource` | RabbitMQ publish/consume for async/event verification | TBD | not started — possible **4th testing angle** (API+DB+UI+queue) beyond the three-angle standard in `target-framework.md` |

## 4. UI / Playwright layer — foundation landed (2026-07-28)

| Item | Purpose | Target | Status |
|------|---------|--------|--------|
| `src/pages/app/*.resource` (hub, home, login, onboarding, …) | Page Object Model for the app UI | `tests/ui/pages/app/` | **partial** — Base + hub/home/login/onboarding + bill landline + pay/top-up/wallet-mgmt/checkout-confirm shells; cookbook in `ui-pom-cookbook.md` |
| `src/services/frontend/browser-service.resource` (Playwright) | Browser session | `tests/ui/browser.py` + fixtures | **done** |
| `src/services/frontend/playwright/front-auth-service.resource` | API/UI login inject | `tests/ui/auth.py` (`AppUiAuth`, `DashboardUiAuth`) | **done** (API inject path); full UI OTP on `LoginPage` |
| `src/services/frontend/playwright/walkthrough.resource`, `Skip-Login-Popup.resource`, `pin-service.resource` | Walkthrough / popup / PIN | `tests/ui/auth.py` + `LoginPage.enter_pin` | **done** |
| Remaining `src/pages/app/*.resource` (c2c, internet, …) | Other domain pages | `tests/ui/pages/app/` | add when a scenario needs them |
| `src/services/AI/*.resource` + icon matching | Image-capture/click utilities | TBD | not started (needs decision — see §1) |

**Note:** `requirements.txt` has **two parallel UI stacks** — `robotframework-seleniumlibrary` +
`robotframework-seleniumtestability` **and** `robotframework-browser` (Playwright-backed). The
new framework standardizes on plain Python Playwright only (`target-framework.md`).

## 5. Shared test data (`src/data/`)

60+ YAML/CSV/XLSX files across every domain (`wallet`, `lms`, `kyc`, `gl`, `settlement`,
`merchant-credit`, `wealth`, `los`, `pcm`, `tms`, `smc`, `Insurance`, `credit-journey`,
`dashboard`, `app`, `backend/payment`, `payment`), plus `src/data/icons/` (reference screenshots
for the icon-matching library in §1) and `src/data/CONSTANTS.yaml`. `AGENTS.md` already says
reuse `src/data/` as read-only — this row is just to record the real scope so it isn't assumed
to be just the 1–2 files we've touched (`health-check.yaml`, `CONSTANTS.yaml`).

**Status:** ongoing — pull in per-file as each domain gets ported, not a batch task.
`CONSTANTS.yaml` is loadable via `tests/config/constants.py` (typed foundation fields +
`raw` / `.get()` for domain keys) as of 2026-07-31.

## 6. Config gaps

| Item | Gap | Status |
|------|-----|--------|
| Shared Settings keys (Mongo/Postgres/Rabbit/Mock/UI paths/business IDs) | Expanded 2026-07-31 in `tests/config/settings.py` | done |
| MS path prefixes | YAML-sourced in `tests/api/ms_paths.py` (2026-07-31) | done |
| `src/config/session-config.py` retry settings (`SESSION_DEFAULT_BACKOFF_FACTOR`, `RETRY_STATUS_LIST`, `RETRY_METHOD_LIST`) | `ApiClient`/`Settings` implement **no retry-on-failure** at all today (plain `httpx.Client`, no adapter). Low real impact today since `RETRY_STATUS_LIST` is empty in the legacy config, but it's a silent gap, not a conscious decision | not started |
| Business login credentials (`PLATFORM_UESERNAME`/`PASSWORD`, `COMPANY_USERNAME`/`PASSWORD`) | Currently rejected by live UAT — see `migration-status.md` "Known gaps" | tracked separately |

## 7. CI/CD, reporting & notifications

| Item | Purpose | Status |
|------|---------|--------|
| Hybrid `.gitlab-ci.yml` `Pytest Migration Suite` | `pip install .` + `playwright install --with-deps chromium` + pytest junit | **done** (B7) |
| Greenfield packaging | pytest README / CI / Dockerfile / copy list | **done** — promoted to repo root (B8); this repo is the greenfield repo |
| `qa-script-api.sh` / `qa-script-api.ps1` | Runs Robot suites inside the deployed pod, per-domain (`pabot`), then strips/summarizes logs | out of scope for pytest (new suite runs directly in CI, no pod) — but the *reporting* steps below still need an equivalent |
| `scripts/strip_robot_logs.py` | Strips verbose Robot XML logs down to a minimal artifact | not started — pytest equivalent would trim `report.xml`/junit output if needed |
| `scripts/summary_table.py` | Builds the human-readable pass/fail summary table posted to chat | not started |
| `scripts/prometheus-reporter.robot` + `library/prometheus.py` | Pushes suite metrics to Prometheus after each run | not started |
| `scripts/installment.py` | Deprecated (marked `# DEPRECATED` in `qa-script-api.sh`) | out of scope |
| `.gitlab-ci.yml` `Collect Full/Minimal Artifacts` jobs | Push results to **Zoho Cliq** and **Microsoft Teams** webhooks | deferred — greenfield CI ships junit/allure artifacts; chat webhooks optional later |

## 8. Adjacent tooling — likely out of scope, flagged for awareness only

| Item | What it is | Recommendation |
|------|-----------|-----------------|
| `mini_apps/cortex/` | Standalone Flask app for *manual* test-account allocation/cleanup; has its own CI job (`build-cortex`) + GitOps deploy | out of scope — not a test, don't touch during migration, just don't break its CI job |
| `robot-claude-agent-setup/` | Pre-Cursor Claude Code agent config for the Robot suite (own `CLAUDE.md`, directory rules) | superseded by `AGENTS.md`/`.cursor/` — candidate for cleanup/removal, not migration |
| `robotframework_mr_code_review_checklist.md` (Persian) | Real, detailed Robot MR review checklist (layering, naming, docs, teardown discipline) | good raw material for an eventual pytest MR checklist — not code to port |
| `CLAUDE.md.backup` | Old backup file at repo root | likely stale — candidate for cleanup, not migration |

---

## Priority call-outs (not a strict order, but worth knowing)

1. **§2 `user-wallet-initializer-service.resource`'s teardown/collection mechanism** — customer
   + business paths landed 2026-07-31 (`WalletInitializer` + fixture teardown). Prefer
   `create_business_with_charged_wallets` over ad-hoc business charges.
2. **`UserFactory` + the 4 DB clients (§1/§3)** — already tracked in `migration-status.md` as a
   foundation follow-up; this file just confirms the real scope (4 engines, not fewer).
3. Everything else in this file can be pulled in incrementally, per-domain, as we get to it —
   no need to batch-port library-by-library ahead of actual test demand.
