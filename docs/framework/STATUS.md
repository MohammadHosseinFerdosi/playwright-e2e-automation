# Current status — Platform pytest + Playwright framework

> **Audience:** a new human or AI agent with zero chat history.
> **Purpose:** the one file to read for "what is this, what's built, what's next."
> **Last updated:** 2026-08-29

If you only open **one** file after [`AGENTS.md`](../../AGENTS.md), open this one.
Root install/run: [`../../README.md`](../../README.md). Full doc index: [`README.md`](README.md).

This is the primary status file. Keep §5/§6/§7 current; update **your domain row only**.

---

## 1. What this project is (one paragraph)

Platform UAT automation on **pytest + pytest-bdd + httpx + Playwright**. Config in `config/`,
fixtures in `data/`, suite under `tests/`. One chat = one MR slice. The Robot Framework →
pytest **foundation migration is complete** (gate closed 2026-07-13, B0–B8 finished
2026-07-31) — this is now the steady-state framework, not an in-flight migration. Domain
teams add scenarios and APIs as needed; legacy Robot Framework lives only in separate
origin history / the `staging` clone, not in this tree.

## 2. Read order for new work

| # | File | Why |
|---|------|-----|
| 1 | [`AGENTS.md`](../../AGENTS.md) | Boundaries, hard rules, skills — every chat |
| 2 | **This file** | Current state + what to do next |
| 3 | [`.cursor/skills/coding-standards/SKILL.md`](../../.cursor/skills/coding-standards/SKILL.md) | Layers, class+fixture, assertions/reporting, Gherkin/tags, PR checklist |
| 4 | [`target-framework.md`](target-framework.md) | Stack + locked design decisions |
| 5 | [`ui-pom-cookbook.md`](ui-pom-cookbook.md) | Adding a UI page |

Also load when writing Gherkin: [`.cursor/rules/gherkin-style.mdc`](../../.cursor/rules/gherkin-style.mdc).
When editing `tests/`: [`.cursor/rules/pytest-architecture.mdc`](../../.cursor/rules/pytest-architecture.mdc).

## 3. How we work (non-negotiable)

| Rule | Meaning |
|------|---------|
| Improve, don't clone | Outline, shared steps, pydantic, poll-not-sleep — avoid one-off clone steps |
| Plan → approval → implement | No speculative files; pause if scope grows |
| Class + fixture only | `ApiClient`, DB clients, factories — never module-level globals (xdist-safe) |
| Tags | story (`@ALPHA-####` or other `@PROJECT-####`, e.g. `@KYC-2050`) + type + suite + domain + **feature** (`{domain}_{capability}`) on `Feature:` (story per scenario when they differ); behavior/severity on scenarios when they differ |
| `{status_code, body}` | HTTP envelope only — parse business fields from `body` (or pydantic models) |
| Teardown money | Charged customer wallets **must** be swept (`wallet_initializer` fixture) |
| Mask PII | FAIL text masks phones/IBANs; Allure HTTP JSON dumps request+response and redacts tokens/cookies |
| Assertions | Never a bare `assert` in a step file — use `tests/services/assert_report.py` |
| Pre-push | `make lint && make typecheck && make collect` locally before every push; CI runs lint + typecheck on every MR (`Lint and typecheck` in `.gitlab-ci.yml`). `collect` is local-only |

## 4. Foundation status — CLOSED

Gate closed 2026-07-13; all B0–B8 slices done 2026-07-31. This is the steady-state
framework — do not re-open foundation work.

## 5. Domain progress

| Domain | pytest path | Status |
|--------|-------------|--------|
| payment | `tests/bdd/features/payment/` | health-check 1/11, refund-inquiry 3/3 (file complete) — both blocked on Platform/Company business login creds (ops, not code) |
| wallet | `tests/bdd/features/wallet/` | total-balance 8/8, user-transfer live |
| bill | `tests/bdd/features/bill/` | validation 10 + config 1 + landline API/UI live UAT PASS; wallet-pay → ORDERED parked (no WireMock / SUCCESS pool) |
| app | `tests/bdd/features/app/` | login onboarding (`@app_login_onboarding`, `@ALPHA-15117`) |
| kyc | `tests/bdd/features/kyc/` | digital signature 10; promissory 37 (`@KYC-2163`); Shahkar basic inquiry (`@KYC-2201`); postal-code (`@KYC-2202`); registration inquiry (`@KYC-2203`) |
| debit | `tests/bdd/features/debit/` | bank-transfer + nemo (167 SET-T; live/secret gated) |
| gl | `tests/bdd/features/gl/` | Rahkaran merchant mapping + incoming financial transactions (`@GL-3530`) |
| lms | — | deferred |

Detail, owners, and Robot-path cross-reference: [`migration-status.md`](migration-status.md).

## 6. Known gaps (do not assume these are done)

- **Platform/Company business login creds** in `config/environment-stage.yaml` are rejected
  by live UAT (env/ops issue, confirmed not a code bug) — blocks payment health + refund
  going green.
- **report-mng APIs** — not ported.
- **Bill-mng happy-path / SUCCESS pay** — no curated unpaid UAT bill pool, no WireMock in
  this repo; don't add SUCCESS inquiry / wallet-pay → ORDERED scenarios until that exists.
- **Redis sentinel/cluster** — not ported (standalone `get_key`/`set_key` only).
- **RabbitMQ client** — not built; add only if a scenario needs the event angle.
- Full detail: [`migration-status.md`](migration-status.md) "Known gaps".

## 7. Recommended next work

Foundation is done — next work is **domain-team-owned**: new `.feature` files + API/UI
modules as needed, following the read order above. Ops should refresh Platform/Company
business login creds when payment smoke needs to go green. Don't re-add deleted legacy
Robot trees, don't rebuild packaging from scratch.

A large amount of Robot scenarios in the separate `api-robot-automated-test` repo are still
not ported. If you're picking one up: [`../ai/robot-to-pytest-migration-guide.md`](../ai/robot-to-pytest-migration-guide.md)
is the step-by-step process (written for non-technical team members), and
[`.cursor/skills/pytest-migration/SKILL.md`](../../.cursor/skills/pytest-migration/SKILL.md)
is what the AI agent follows.

## 8. How to run what exists

```bash
# Collection
PYTHONPATH=. pytest --collect-only -q

# Wallet suite (needs VPN / UAT + MySQL + Redis)
PYTHONPATH=. pytest -m wallet -v

# UI platform + TCI landline (needs VPN / UAT + MySQL + Redis + Chromium + secrets)
PYTHONPATH=. pytest -m "platform_ui_hub or bill_tci_ui" -v
```

After pytest, open `allure-dashboard/index.html` to check the run (written for you).
How to read it: [`.cursor/skills/allure-dashboard/SKILL.md`](../../.cursor/skills/allure-dashboard/SKILL.md).

Intermittent nginx 502 from UAT is infrastructure flake, not always a test bug — retry the
single example before rewriting logic.

## 9. End-of-session checklist (every agent)

- [ ] Only approved files changed
- [ ] This file (§5/§6/§7) updated if state changed — **your domain row only**
- [ ] Commit only if the user asked
