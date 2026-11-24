# AI Workflow — Cursor + Claude

## Principle

**Chat history is not shared memory.** These repo files are:

- `AGENTS.md` — entry point (repo root, fixed location)
- `docs/framework/STATUS.md` — **primary handoff** (what we built + next step)
- `docs/framework/README.md` — index of all framework docs
- `docs/ai/onboarding-prompt.md` — long paste for a zero-context agent
- `docs/ai/prompts/` — optional paste-ready task prompts
- `.cursor/rules/` — auto-loaded in Cursor (fixed location)
- `.cursor/skills/` — invoke explicitly when the task matches

Claude Agent users: point `CLAUDE.md` to `AGENTS.md` (same docs for both tools).

## Cursor setup

### Rules (under `.cursor/rules/`)

| File | When |
|------|------|
| `migration-core.mdc` | Always on — stack, branches, boundaries |
| `migration-quality.mdc` | Always on — improve, don't clone |
| `review-before-implement.mdc` | Always on — plan → approval → implement |
| `pytest-architecture.mdc` | When editing `tests/` |
| `gherkin-style.mdc` | When editing `*.feature` |
| `python-code-style.mdc` | Python style (type hints, docstrings) |
| `step-definitions.mdc` | Thin-step contract for `tests/bdd/steps/` |
| `ui-labels.mdc` | UI pages, labels, EN→FA copy |
| `typecheck.mdc` | When editing `scripts/` or `tests/` |
| `zephyr.mdc` | Zephyr / Jira ATM work |

### Skills (under `.cursor/skills/` — invoke explicitly)

| Skill | When |
|-------|------|
| `coding-standards/SKILL.md` | **Read first** for any new code |
| `pytest-migration/SKILL.md` | Porting a Robot scenario from the separate Robot repo |
| `code-review/SKILL.md` | Review a diff / check before push |
| `zephyr/SKILL.md` | Zephyr Scale sync + result push |
| `figma/SKILL.md` | QA Figma MCP (`secrets/figma.env`) |
| `ui-labels/SKILL.md` | English→Farsi UI labels |

## New chat template

**Preferred handoff:** paste [`docs/ai/onboarding-prompt.md`](onboarding-prompt.md) (full
block), or for a quick same-tool chat use the short opener in `AGENTS.md`.

**Generic:**

```
@AGENTS.md @docs/framework/STATUS.md @.cursor/skills/coding-standards/SKILL.md

Branch: <feat|fix|chore|hotfix|docs>/<JIRA-KEY|-or-team>-<slug>  (off staging)
Task: [one specific task only]

Constraints:
- New code under tests/ only
- Improve, don't clone (migration-quality.mdc)
- Plan → approval before any file write (review-before-implement)
- Tags: story (@PROJECT-####) + severity + type + suite + domain + feature
- Follow docs/framework/target-framework.md

Reference (if porting):
@[path in separate Robot repo and/or already-ported tests/ files]
```

## Chat strategy

| Do | Don't |
|----|-------|
| One chat per MR / task | One chat for an entire domain |
| `@` specific files | "migrate everything in payment" |
| Update `STATUS.md` after real progress | Rely on chat memory |
| Invoke the matching skill | Free-form without reading `AGENTS.md` |
| Branch off `staging` with a valid prefix | Use retired `migrate/*` / `platform/*` names |

## Invoke skills explicitly

In Cursor chat:

```
Follow .cursor/skills/coding-standards/SKILL.md
Add the API client + feature slice for @tests/bdd/features/...
```

```
Follow .cursor/skills/pytest-migration/SKILL.md
Port the Robot scenario described in @docs/ai/robot-to-pytest-migration-guide.md
```

```
Follow .cursor/skills/zephyr/SKILL.md
Export all scenarios in this feature to Zephyr, folder /Bill/TCI
```

## Team sync

- Check `docs/framework/STATUS.md` (and `migration-status.md` for domain ownership) before starting
- Same docs for Cursor and Claude users
- Human reviews every MR — AI review is not enough
