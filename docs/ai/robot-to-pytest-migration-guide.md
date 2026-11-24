# Migrating a Robot scenario into this repo — step by step (A → Z)

> **Audience:** any team member porting Robot Framework scenarios from
> `api-robot-automated-test` into this repo, especially if you're not deeply technical or new
> to working with AI coding agents. Follow this top to bottom the first few times; once it's
> familiar you'll skip steps you don't need.
>
> **The one thing to understand first:** these are **two separate repos** on your computer —
> `api-robot-automated-test` (the old Robot suite — source only, you never write to it) and
> `playwright-e2e-automation` (this repo — where the ported test lands). "Migrating" means
> reading behavior from the old repo and writing new code in this one. Nothing in the old repo
> ever changes.

---

## 0. One-time setup (do this once, not per scenario)

1. Make sure both repos are cloned on your machine:
   - Old: `api-robot-automated-test`
   - New: `playwright-e2e-automation` (this repo)
2. Set up this repo per [`CONTRIBUTING.md`](../../CONTRIBUTING.md):
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   pre-commit install
   playwright install chromium
   ```
   Or: `make install-dev && make browsers`.
3. Make sure you're on your company VPN — `git push`/`git pull` against
   `example.com` only works on the internal network; without VPN you'll get a
   "could not resolve hostname" error.
4. This guide assumes **Claude (Cowork)**. Your connected folder is normally this repo
   (`playwright-e2e-automation`) — reading the old repo needs one small extra step, covered
   in step 4 below.

---

## 1. Pick ONE scenario to migrate — and check it isn't already done

Never start from "let's migrate the payment domain." Start from **one Robot `.robot` file**,
ideally one that covers a single, related group of scenarios.

Before picking, check two files in this repo so you don't duplicate work that's already been
done (this has happened before — a lot of the underlying plumbing is already built):

1. [`docs/framework/migration-status.md`](../framework/migration-status.md) — the "Domains"
   table shows what's already ported per domain, and the "Foundation Gate" section confirms
   the shared platform pieces (auth, factories, DB clients) are done.
2. [`docs/framework/migration-inventory.md`](../framework/migration-inventory.md) — a longer
   list of *everything else* (custom libraries, DB clients, UI pages, config) with a Status
   column. If the thing your scenario needs already says `done`, you reuse it — you don't
   rebuild it.

If you're not sure whether a scenario is already covered, ask Claude to check for you (prompt
example in step 4).

> If your team still opens a branch in the old repo for your own bookkeeping/ticket tracking,
> that's fine and has no technical effect here — we never commit anything back to that repo.

---

## 2. Open the Robot file and see what it pulls in

In the old repo, open your chosen file under `features/{domain}/`. At the top you'll see
`Resource` / `Library` imports — these point at:

- `src/steps/**/*.resource` — the step logic
- `src/apis/**/*.resource` — the HTTP calls
- `src/pages/**/*.resource` — UI page objects (if it's a UI scenario)
- `src/data/**/*.yaml` — test data the scenario reads

You don't need to manually trace every one of these — Claude will do that in step 4 — but skim the
file once so you know roughly what it does. This is "everything needed for running that" the
migration has to bring across, not just the top-level `.robot` file.

---

## 3. Create your branch — in the NEW repo

```bash
cd playwright-e2e-automation
git checkout staging
git pull
git checkout -b <branch-name>
```

Branch name must match one of these (enforced by CI — a wrong name fails the pipeline):

- **Have a Jira ticket:** `feat/ALPHA-1234-port-wallet-cashout`
- **No ticket:** `chore/superapp-port-wallet-cashout` (team name lowercase)

Verify it locally before you push:

```bash
CI_COMMIT_REF_NAME=$(git branch --show-current) python3 scripts/check_branch_name.py
```

---

## 4. Give Claude access to both repos, then ask it to plan the port

Your connected folder in Claude/Cowork is normally this repo
(`playwright-e2e-automation`). To let it also read the old repo, try these in order:

1. **Ask Claude to connect the old repo as well.** Say: *"I also need you to read files from
   `/Users/yourname/Projects/api-robot-automated-test` — can you request access to that
   folder?"* If your Cowork setup supports more than one connected folder, it'll prompt you
   to approve it, same as it did for this repo the first time.
2. **If that's not available, paste the file contents directly into the chat.** Open the
   `.robot` file (and the `.resource` files it imports — see step 2) on your computer in any
   text editor, copy the contents, and paste them into your message to Claude along with the
   file's original path (so it knows what to call it in its notes). This always works and
   needs no setup.
3. **Or copy the specific files into a scratch folder inside this repo.** Create something
   like `docs/ai/_scratch/` inside `playwright-e2e-automation`, copy in *only* the `.robot` +
   `.resource` files you're porting, let Claude read them from there, and **delete that
   folder before you commit** — it should never be pushed. Option 2 (pasting) is simpler for
   one or two files; use this if there are many files to hand over at once.

### The first prompt — plan only, don't let it write code yet

Copy this and fill in the blanks:

```
Read AGENTS.md, then invoke the pytest-migration skill
(.cursor/skills/pytest-migration/SKILL.md) and follow it.

I want to port this Robot scenario into this repo:
- Old repo path: /Users/yourname/Projects/api-robot-automated-test
- File: features/<domain>/<name>.robot
- Also read every .resource file it imports (steps/apis/pages) so you understand full behavior

Before proposing anything:
1. Check docs/framework/migration-status.md — confirm this isn't already ported
2. Check docs/framework/migration-inventory.md — tell me what prerequisites (DB clients,
   factories, API modules, UI pages) already exist in this repo that we should reuse, vs.
   what's genuinely missing and needs to be built

Give me a PLAN ONLY — list of files you intend to create or edit, and which existing pieces
you're reusing. Do not write any code yet. Wait for my approval.
```

Claude should come back with a plan, not code. This matches the repo's
plan → approval → implement rule
([`.cursor/rules/review-before-implement.mdc`](../../.cursor/rules/review-before-implement.mdc)) —
if it jumps straight to writing files, stop it and ask for the plan first.

---

## 5. Review the plan before approving

Read the plan for two things specifically:

1. **Duplication** — does it propose building something `migration-inventory.md` already
   marks `done`? If you're unsure, ask directly: *"Are any of these already built? Check
   migration-inventory.md again."*
2. **Correct location** — sanity-check against this table:

   | This kind of thing | Belongs in |
   |---|---|
   | HTTP call (thin, returns `{status_code, body}`) | `tests/api/{team}/{endpoint}.py` |
   | Gherkin scenario | `tests/bdd/features/{domain}/{name}.feature` |
   | Step definitions (thin orchestration) | `tests/bdd/steps/{domain}_steps.py` |
   | Reused business logic (factories, wallet helpers, DB queries) | `tests/services/` |
   | UI page object | `tests/ui/pages/...` (inherits `BasePage`) |
   | New fixture | `tests/conftest.py` — flag this one, shared fixtures need care |

If the plan looks right, approve it: *"Approved, go ahead."*

---

## 6. Let Claude implement, then verify locally yourself

Once it's written the files, run these yourself — don't just trust "it should work":

```bash
make lint
make typecheck
make collect
```

Then run just the scenario you ported:

```bash
PYTHONPATH=. pytest -k "<part of your scenario name>" -v
```

If anything fails, paste the error back to Claude and ask it to fix it — then re-run the same
commands. Don't move on until all three `make` commands pass clean.

---

## 7. Update the tracking docs — so the next person doesn't duplicate you

Ask Claude to do this as part of finishing the task (it's already in the pytest-migration skill's
checklist, but confirm it happened):

- [`docs/framework/migration-status.md`](../framework/migration-status.md) — the domain row's
  parity/status updated
- [`docs/framework/migration-inventory.md`](../framework/migration-inventory.md) — updated if
  you built a new prerequisite piece (so the next person sees it as `done`, not `not started`)

Prompt:

```
Update docs/framework/migration-status.md and migration-inventory.md for the work we just
did, following the existing format in each file.
```

---

## 8. Final check before you push

Ask Claude to review your own change like a second pair of eyes:

```
Read .cursor/skills/code-review/SKILL.md and review my changes on this branch before I push.
```

This runs `make lint`/`make typecheck`/`make collect` again and walks the diff against
[`docs/code-review/code-review-standard.md`](../code-review/code-review-standard.md) — the
same checklist a human reviewer uses. Fix anything it flags with a 🚫 before pushing.

---

## 9. Push and open the MR

```bash
git push -u origin <branch-name>
```

GitLab prints an MR link in the push output — open it, target **`staging`**, and in the
description note which Robot file(s) you ported and paste the updated
`migration-status.md` row.

A human still reviews every MR — Claude review alone isn't enough
(see `docs/code-review/code-review-standard.md` → "Before approving").

---

## Quick reference — every prompt, start to finish

For a fast recap once you've done this a few times:

1. *(plan)* `Read AGENTS.md, invoke pytest-migration skill, plan (don't code) porting <file> from <old repo path>, checking migration-status.md and migration-inventory.md for duplication first.`
2. *(approve)* `Approved, go ahead.`
3. *(verify — you run these, not AI)* `make lint && make typecheck && make collect`
4. *(docs)* `Update migration-status.md and migration-inventory.md for this work.`
5. *(review)* `Read .cursor/skills/code-review/SKILL.md and review my changes before I push.`
6. *(push — you run this)* `git push -u origin <branch-name>`

---

## Common mistakes to avoid

- **Writing to the old repo.** Never commit there as part of a port — it's read-only source.
- **Skipping the migration-status.md / migration-inventory.md check.** This is how you
  duplicate work someone already did.
- **Letting Claude write code before you've seen a plan.** Always ask for a plan first.
- **Branch name typos.** `migrate/*` is not valid here — use `feat/<JIRA>-<slug>` or
  `chore/<team>-<slug>`.
- **Skipping `make lint && make typecheck && make collect`.** There's no CI job that catches
  this for you — it's the only gate, and it's on you to run it.
- **Forgetting to update `migration-status.md`.** If you don't, the next person doing step 1
  won't know your scenario is done, and might redo it.
