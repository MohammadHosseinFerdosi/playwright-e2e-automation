# New-agent onboarding prompt

Short handoff for a **brand-new chat** (zero prior context). Paste the block below as the
first message, fill in `Task:`, and the agent can reconstruct state from the repo.

For same-tool, same-project chats that already load workspace rules, the opener in
[`AGENTS.md`](../../AGENTS.md) is enough. Prefer this longer paste when handing off to a
different tool, a truly fresh agent, or after a long gap.

> **Historical note:** Older versions of this file described an in-repo Robot → pytest
> migration (`feat/bdd-pytest-migration` mother branch, `migrate/*` / `platform/*` prefixes).
> That era is over — this repo **is** the pytest framework. Robot source lives only in a
> separate read-only reference repo. Do not resurrect those branch names or folder
> boundaries.

---

## Copy-paste block

```
You are starting work on Platform UAT automation (pytest + pytest-bdd + httpx + Playwright).
Read in this order before writing or suggesting code:

1. AGENTS.md — entry point, stack, hard rules, skills table
2. docs/framework/STATUS.md — primary handoff: what is built, how we work, what's next
3. .cursor/skills/coding-standards/SKILL.md — layers, class+fixture, assertions,
   Gherkin/tags, PR checklist (read before any new code)
4. docs/framework/target-framework.md — locked design decisions (skim)
5. .cursor/rules/gherkin-style.mdc — before any .feature edit
6. .cursor/rules/pytest-architecture.mdc — when editing under tests/
7. .cursor/rules/review-before-implement.mdc — plan → approval → implement (always)

=== WHAT THIS PROJECT IS ===

Repo: playwright-e2e-automation (greenfield pytest suite). Platform UAT API + UI automation
via BDD. Python 3.10–3.11 only. No mother branch — branch off staging per
scripts/check_branch_name.py:
  Ticketed: <feat|fix|chore|hotfix|docs>/<JIRA-KEY>-<slug>
  No ticket: <chore|hotfix|docs>/<team>-<slug>
migrate/* and platform/* are NOT valid prefixes.

Test code → tests/ only. Config → config/environment-stage.yaml. Fixtures → data/.
Secrets → secrets/*.example.* in git; real files local/CI only.

=== WHERE TO LOOK FOR STATE ===

- Current status / next work: docs/framework/STATUS.md
- Domain/scenario inventory (detail): docs/framework/migration-status.md
- Beyond test cases (DB, services, UI): docs/framework/migration-inventory.md
- Porting from Robot (separate repo): .cursor/skills/pytest-migration/SKILL.md +
  docs/ai/robot-to-pytest-migration-guide.md — never write into the Robot repo

=== HARD RULES (non-negotiable) ===

- Improve, don't clone — Outline, pydantic, class+fixture, poll-not-sleep
  (.cursor/rules/migration-quality.mdc)
- Plan → approval → implement — no speculative files
- Class + fixture only — never module-level HTTP/DB/factory singletons (xdist-safe)
- Tags: every scenario resolves to story (@PROJECT-####) + severity + type (api/e2e) +
  suite (smoke/regression) + domain + feature ({domain}_{capability})
- HTTP envelope {status_code, body} only via ApiClient + ms_path helpers
- Assertions: never bare assert in step files — use tests/services/assert_report.py
- Steps: thin orchestration — enforced by scripts/check_step_style.py
- Pre-push: make lint && make typecheck && make collect
- Mask PII (phone, NID, IBAN) in logs

=== ZEPHYR ===

Built: scripts/zephyr_sync.py (case create/update) + tests/zephyr_result_collector.py
(result push into a new cycle). Skill: .cursor/skills/zephyr/SKILL.md

=== FIGMA ===

QA designs for agents: copy secrets/figma.example.env → secrets/figma.env and paste
FIGMA_ACCESS_TOKEN (gitignored). Cursor + Claude Code MCP: figma-qa via
scripts/figma_mcp.sh. Human steps: docs/ai/figma-setup.md. Skill: .cursor/skills/figma/SKILL.md
Never echo or commit the token.

=== KNOWN OPS GAP ===

Platform / Company business login values in config/environment-stage.yaml may be rejected
by live UAT until ops refreshes them — payment health/refund stay red until then. Do not
"fix" by inventing credentials.

Task: [one specific MR slice — one file, one feature, or one platform piece]
Working agreement: plan → wait for approval → implement; update STATUS.md
only when state actually changed
```

---

## Why this exists

`AGENTS.md` stays short on purpose. This file is the self-contained paste when workspace
rules may not be loaded, or when you want one message that points at the current
entry points without chasing historical migration docs first.
