# Reusable prompt template — migrate one Robot scenario

Fill in the `< >` blanks and paste as the first message in a new AI chat. Full walkthrough
of what each step means: [`../robot-to-pytest-migration-guide.md`](../robot-to-pytest-migration-guide.md).

This is the generic version — use this template when starting a **new** scenario nobody
has scoped yet.

---

## Step 1 — plan only

```
Read AGENTS.md, then invoke the pytest-migration skill
(.cursor/skills/pytest-migration/SKILL.md) and follow it.

I want to port this Robot scenario into this repo:
- Old repo path: <e.g. /Users/yourname/Projects/api-robot-automated-test>
- File: <e.g. features/wallet/wallet-cashout-feature.robot>
- Also read every .resource file it imports (steps/apis/pages) so you understand full behavior

Before proposing anything:
1. Check docs/framework/migration-status.md — confirm this isn't already ported
2. Check docs/framework/migration-inventory.md — tell me what prerequisites (DB clients,
   factories, API modules, UI pages) already exist in this repo that we should reuse, vs.
   what's genuinely missing and needs to be built

Give me a PLAN ONLY — list of files you intend to create or edit, and which existing pieces
you're reusing. Do not write any code yet. Wait for my approval.
```

## Step 2 — approve (after you've read the plan against the guide's duplication/location checks)

```
Approved, go ahead.
```

## Step 3 — verify (you run this yourself, in your terminal)

```bash
make lint
make typecheck
make collect
PYTHONPATH=. pytest -k "<part of your scenario name>" -v
```

## Step 4 — update tracking docs

```
Update docs/framework/migration-status.md and migration-inventory.md for the work we just
did, following the existing format in each file.
```

## Step 5 — review before push

```
Read .cursor/skills/code-review/SKILL.md and review my changes on this branch before I push.
```

## Step 6 — push (you run this yourself)

```bash
git push -u origin <branch-name>
```

---

## Optional — behavior inventory table

If the Robot file has several test cases (like an Outline candidate), filling this in before
step 1 gives the AI a much better starting plan. Not required, but speeds things up on
anything non-trivial:

| # | Robot test case | Severity | Behavior to preserve |
|---|-----------------|----------|----------------------|
| 1 | | | |
| 2 | | | |

Shared data files the scenario reads: `<src/data/... .yaml paths>`
