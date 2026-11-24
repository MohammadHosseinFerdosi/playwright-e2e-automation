# Migration Status

> **Superseded as the primary entry point by [`STATUS.md`](STATUS.md).** Kept in full for the
> gate decision note, locked design-decision rationale, and per-domain owner/Robot-path table
> below — not duplicated elsewhere. `STATUS.md` §4/§5 has the condensed current picture.

> Update **your domain row only** when you port a slice (other teams' rows stay). Foundation
> is closed. New work is `feat|fix/<JIRA>-<slug>` off `staging` — `migrate/*` is not a valid
> branch prefix.

See [migration-inventory.md](migration-inventory.md) for everything beyond `features/*.robot` —
custom libraries, DB clients, UI/Playwright layer, shared data, and CI/reporting — tracked
separately so it doesn't get lost just because it isn't a test case.

## Foundation Gate

| Item | Owner | Status | MR |
|------|-------|--------|-----|
| docs + AGENTS.md + .cursor rules | — | done | — |
| `tests/` scaffold + pyproject.toml | — | done — folders + `pyproject.toml` + `tests/pytest.ini`, verified on Python 3.11.15 / pytest 9.1.1 | — |
| ApiClient + settings | — | done — `tests/api/client.py` + `tests/config/settings.py`, ported from `session-service.resource`; only app/microservice/dashboard sides so far | — |
| UserFactory + BusinessFactory | — | done — `BusinessFactory` + `UserFactory` (`create` + `create_predefined`); fixtures wired | — |
| MySQLClient (UserFactory prereq) | — | done — `tests/services/db/mysql_client.py` + MySQL settings fields + `mysql_client` fixture; port of `mysql_db.py` + `mysql-db-service.resource` config builder | — |
| RedisClient (UserFactory prereq) | — | done — `tests/services/db/redis_client.py` + standalone host/port settings + `redis_client` fixture; `get_key` only (OTP path); sentinel/cluster/TLS not ported | — |
| conftest.py | — | done — `settings`/`microservice_client`/`business_factory`/`mysql_client`/`redis_client` fixtures wired | — |
| GitLab pytest CI job | — | done — `Pytest Migration Suite` job added, runs on `staging` + MRs targeting the mother branch; existing jobs pinned staging-only so they don't newly fire on migration MRs | — |
| Pilot smoke tests | — | API smoke done (`tests/bdd/features/platform/create_business_smoke.feature`), ran for real against live UAT, PASSED. UI smoke test tracked separately below — decided NOT to block the gate on it | — |
| **FOUNDATION GATE** | — | **CLOSED** (2026-07-13) — see decision note below | — |

> **Gate decision (2026-07-13):** closed with the API pipeline proven end-to-end for real
> (feature → steps → fixtures → ApiClient → live UAT call, passed) and `UserFactory`/UI smoke
> test deliberately deferred rather than treated as gate blockers. Domain work then started
> from `staging` (`migrate/*` was the old prefix — **invalid** on new branches). Two items
> remain as follow-ups, not gate blockers:
> - **UI smoke test** — Playwright + `BasePage` + hub inject smoke (`@platform_ui_hub`) +
>   first domain UI (`@bill_tci_ui`) landed 2026-07-28; run live against UAT to confirm green
> - **`UserFactory`** — done 2026-07-16. **WalletInitializer** customer path 2026-07-16;
>   business create/charge/teardown done 2026-07-31 (foundation checklist B1).

## Design decisions (locked — reference `docs/framework/target-framework.md` for detail)

These were decided in the SDET demo prep session and should NOT be re-litigated in future
migration chats without a good reason:

- **Tag taxonomy**: 4 required axes — `severity`, `type`, `suite`, `domain`
- **No module-level globals** — `ApiClient`, DB clients, factories are classes wired via
  pytest fixtures (fixes the `_connection`/`_cursor` anti-pattern in `src/library/*_db.py`)
- **Parallel execution**: `pytest -n auto` (pytest-xdist), replacing `pabot`
- **Three-angle testing**: API + DB + UI verification for business-critical events,
  formalized as a standard, not ad hoc
- **Improve, don't clone** — Robot is behavior reference only; redesign into reusable
  Outline/helpers, pydantic models, poll-not-sleep (see `.cursor/rules/migration-quality.mdc`)
- **Jira / Zephyr Scale**: BDD create/update sync (`scripts/zephyr_sync.py`) supports Outline/Background/tables/doc strings, labels/priority, and story `issueLinks`. Pytest → new Zephyr testrun via `tests/zephyr_result_collector.py` when `ZEPHYR_CYCLE_NAME` is set. Guide: [`docs/zephyr/Zephyr-Scale-Complete-Guide.pdf`](../zephyr/Zephyr-Scale-Complete-Guide.pdf).

## Domains

| Domain | Owner | Robot path | pytest path | Status | Parity |
|--------|-------|------------|-------------|--------|--------|
| payment | — | `features/payment/` | `tests/bdd/features/payment/` | in progress — health-check.robot 1/11 cases, purchases-refund-inquiry-feature.robot 3/3 cases (file complete) | health-check 1/11, refund-inquiry 3/3 |
| wallet | — | `features/wallet/` | `tests/bdd/features/wallet/` | total-balance 8/8 + user-transfer live | users-total-balance 8/8, user-transfer |
| bill | — | *(none — greenfield)* | `tests/bdd/features/bill/` | validation 10 + config 1 live UAT PASS. **Landline API:** `@bill_tci_validate`. **Landline UI:** `@bill_tci_ui` (Playwright hub→inquiry; first UI domain). Fill secrets YAML. Wallet pay / admin parked | validation + config + validate + UI (skip without secrets/browser) |
| app | — | `features/app/` | `tests/bdd/features/app/` | login onboarding (`@app_login_onboarding`, `@ALPHA-15117`) | login onboarding |
| kyc | — | `features/kyc/` | `tests/bdd/features/kyc/` | digital signature + promissory 37 (`@KYC-2163`) + Shahkar basic inquiry (`@KYC-2201`) + postal-code (`@KYC-2202`) + registration inquiry (`@KYC-2203`) | digital_signature + promissory_note + shahkar_inquiry + postal_code + registration_inquiry |
| debit | — | `features/bank-transfer/` + `features/nemo/` (Robot clone `bank-transfer-tests`) | `tests/bdd/features/debit/` | in progress — 167 SET-T (live/secret gated) | bank-transfer + nemo |
| gl | — | `features/gl/` | `tests/bdd/features/gl/` | in progress — Rahkaran merchant mapping + incoming financial transactions (`@GL-3530`) | detailed-code-management + incoming-transactions |
| lms | — | `features/lms/` | — | deferred | — |

## Known gaps

- **Bill-mng happy-path data** — no curated unpaid UAT bill pool in secrets, no WireMock in
  this repo. Do **not** add SUCCESS inquiry / wallet-pay → ORDERED scenarios until Option E
  (gitignored pool) or Option C (local bill-mng + WireMock) exists. Validation suite does
  not need either. Spike confirmed MS path `/bill-mng/platform/api` on `uatms`.
- **Business login credentials in `src/config/environment-stage.yaml` are currently rejected
  by live UAT** — affects any ported scenario that needs `Login For Business`:
  - `PLATFORM_UESERNAME`/`PLATFORM_PASSWORD` (`platform-username`/`platform-password`) look like
    placeholders to begin with, unlike the real-looking creds next to them. Gets
    `401 AUTHENTICATION_INVALID_CREDENTIALS` (2008).
  - `COMPANY_USERNAME`/`COMPANY_PASSWORD` (`company-ipg-test`/`d1g1k@l@t3st`) look like real
    creds but also fail — confirmed with a raw `httpx` call bypassing all our code, so this
    is not a bug in the port. Gets `401 AUTHENTICATION_FAILURE` (2001), a *different* error
    code than Platform's, suggesting a different underlying cause (e.g. stale/rotated
    password, disabled account) rather than the same placeholder issue.
  - `qa-script-api.sh` runs Robot against this exact committed file with no secrets
    injection step, so both `Health Check Service Activity For Platform Business Token` and
    `purchases-refund-inquiry-feature.robot` are almost certainly broken in Robot too, not
    just in the pytest port.
  - Ported anyway (`tests/bdd/features/payment/health_check.feature`,
    `tests/bdd/features/payment/refund_inquiry.feature`) since the code is correct —
    verified live against UAT that requests reach the real endpoints and get back the
    expected shapes, and sanity-checked the refund-inquiry response parsing/assertions
    offline with synthetic responses. Needs real credentials for both businesses before
    these scenarios can go green. Not a blocker for continuing the `payment` domain port.

## Default branch

- **Name:** `staging` — this repo is greenfield; there is no mother branch to merge back into
- **Historical:** `feat/bdd-pytest-migration` was the original same-repo mother; do not use it for new work
