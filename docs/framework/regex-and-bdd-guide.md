# Regex & BDD guide — flexible step definitions

> **Audience:** anyone adding or reviewing step definitions in `tests/bdd/steps/`.
> **Rule summary (enforced):** `.cursor/rules/step-patterns.mdc`. This file is the
> teaching companion — the *why* and the worked examples.
> **Reuse workflow (search stems, rewrite Gherkin, new-family ASCII class):**
> `.cursor/skills/bdd-step-regex/SKILL.md`.
> **Team handbook (printable PDF):** [`bdd-regex-handbook.pdf`](bdd-regex-handbook.pdf).
> **Last updated:** 2026-08-23

Regular expressions are how one step definition serves a whole family of Gherkin
sentences. This guide covers Python `re` as used in this repo, the pytest-bdd parser
options, the canonical step shapes, the dispatch and sentinel conventions, and how to
unit-test a step regex.

---

## 1. Python `re` in 10 lines

A regex describes a **text shape**. The building blocks, each shown in a pattern this
repo already runs:

| Block | Meaning | Real example |
|---|---|---|
| `IR`, `duplicate` | literal characters | `tests/services/assert_report.py` IBAN masker |
| `\d`, `\w`, `\S` | one digit / word char / non-space | `\bIR\d{24}\b` |
| `[0-9۰-۹]` | one char from a class | login timer accepts Latin + Persian digits |
| `{24}`, `{1,2}` | exact / bounded repeats | same two patterns |
| `+`, `*`, `?` | 1+, 0+, optional | branch-name gate `scripts/check_branch_name.py` |
| `(a\|b)` | alternation | `(feat\|fix\|chore\|hotfix\|docs)/` |
| `^`, `$` | start / end anchors | every step regex (see §4) |
| `(?P<name>...)` | named capture | `OPEN_FROM_DASHBOARD_STEP` / `OPEN_FROM_HUB_STEP` |
| `(?:...)` | group without capturing | optional clauses |
| lazy `+?` / `*?` | shortest match that works | multi-word captures before a delimiter |

`re.fullmatch` checks the whole string, `re.match` only the start, `re.search` anywhere
inside. pytest-bdd applies step regexes with `re.match` semantics — which is why the
rule requires explicit `^...$` anchors instead of relying on the engine.

## 2. pytest-bdd parsers — decision table

```python
from pytest_bdd import given, when, then, parsers
```

| Parser | Gherkin line | Step signature gets | When to use |
|---|---|---|---|
| literal `@then("...")` | exactly that text | nothing | fixed sentence |
| `parsers.re(r"^...(?P<g>...)...$")` | every sentence the regex matches | one arg per named group | **default** for any variable part |
| `parsers.parse("...{slot}...")` | one wording, free slots | `slot: str` | **legacy only** — convert when the file is touched |
| `parsers.cfparse("...{n:d}...")` | as `parse` + typed/cardinality | `n: int` | **legacy only** — convert when the file is touched |

New steps with a variable part use `parsers.re`. `{slot}` parse variables cannot
constrain the capture, cannot alternate, and cannot absorb `a/an`. Regex is the
stricter option: `(?P<gateway>[\w ]+)` rejects garbage that `{gateway}` would swallow.

Behave (the legacy framework some of our patterns came from) maps directly:
`@then(r'regex')` → `@then(parsers.re(r"regex"))`. The regex design decisions transfer;
the decorator syntax doesn't. Behave's `{field}` parse syntax is what this repo is
migrating *away* from.

## 3. The canonical shapes

### 3.1 UI action

```python
@when(parsers.re(r"^the customer opens (?P<feature>[A-Za-z0-9 -]+) from the hub$"))
def _(feature: str, hub_page: HubPage, ...) -> None:
    open_from_hub(feature, hub_page, ...)

@when(parsers.re(r"^the staff opens (?P<tile>[A-Za-z0-9 -]+) from the dashboard$"))
def _(tile: str, dashboard_super_app_page: DashboardSuperAppPage, ...) -> None:
    open_from_dashboard(tile, dashboard_super_app_page, ...)
```

Hub and dashboard stay **two families** (customer + `HubPage` vs staff + dashboard POM).
Do not merge them into `the (?P<actor>customer|staff) opens … from the dashboard`.

Gherkin stays business language (`When the customer opens landline bill inquiry from
the hub`); the POM resolves the captured phrase → Farsi label via `tests/ui/labels/`
(`.cursor/rules/ui-labels.mdc`). Never `When I click on "استعلام قبض"` — that's banned
by `gherkin-style.mdc` twice over (implementation language + Persian literal).

### 3.2 UI validation

```python
@then(parsers.re(r"^the (?P<element>[\w ]+) is (?P<state>shown|hidden|enabled|disabled)$"))
def _(element: str, state: str, page_asserts: PageAsserts) -> None:
    page_asserts.assert_element_state(element, state)
```

One step definition, four states, hundreds of future `Then` lines. The
element-name → locator mapping and the state dispatch both live in the service/POM
layer, keeping the step body at one call.

### 3.3 Rejection / outcome family (live in this repo)

```python
# tests/bdd/steps/conftest.py
@then(parsers.re(DUPLICATE_ROUTE_STEP))
def _duplicate_route_single_row(route_kind: str, bt_ctx: BankTransferContext) -> None:
    assert_duplicate_route_single_row(bt_ctx, route_kind)
```

`DUPLICATE_ROUTE_STEP` (in `tests/services/debit/duplicate_route_asserts.py`) replaced
six near-identical `@then` definitions across five debit step files:

```text
duplicate Shahin routes keep a single transfer row            -> Shahin
duplicate manual routes keep a single transfer row            -> manual
duplicate Mellat routes keep a single transfer row            -> Mellat   (was in 2 files)
duplicate Mellat dashboard routes keep a single transfer row  -> Mellat dashboard
the duplicate IBAN Mellat route keeps a single transfer row   -> IBAN Mellat
```

The pattern `^(?:the )?duplicate (?P<route_kind>[\w ]+?) routes? keeps? a single
transfer row$` absorbs the article, the singular/plural, and the route kind; the
captured kind dispatches through a `dict[str, Callable]` to the same assert functions
the six originals called. Feature files did not change.

### 3.4 Value check with sentinel support

```python
@then(parsers.re(r'^the (?P<field>[\w ]+) shown is "(?P<expected>[^"]*)"$'))
def _(field: str, expected: str, ctx: SomeContext) -> None:
    some_asserts.assert_field_shown(ctx, field, resolve_expected_value(expected))
```

See §6 — `resolve_expected_value` turns a sentinel Examples cell into a live lookup.

## 4. Writing the regex — house rules

Condensed from `.cursor/rules/step-patterns.mdc`; rationale here.

1. **Anchor `^...$`.** Unanchored, `the customer inquires` would also match
   `the customer inquires Shahkar`, stealing a more specific step's sentence
   depending on registration order.
2. **Named groups matching parameter names.** pytest-bdd injects by group name; a
   positional group silently injects nothing.
3. **Distinct group names per alternation branch.** The legacy mega-regex reused
   `product_id` across branches and needed a post-match reassignment
   (`if product_id_only: product_id = product_id_only`) — the branch structure was
   invisible in the signature. Distinct names make `if group is not None` (in the
   service) unambiguous.
4. **Constrained captures.** `[\w ]+` for business phrases, `[^"]*` inside quotes, an
   explicit alternation for a closed set. Bare `.+` will eventually match a sentence
   you didn't intend. (The legacy catalog cycled `[^"]+` → `.+?` → `.*?` on one step,
   each a production bug fix — quoted JSON broke `[^"]+`, empty values broke `.+?`.)
5. **Lazy quantifier before a literal delimiter.** `(?P<kind>[\w ]+?) routes?` lets the
   engine give back ` routes` correctly when the capture is multi-word.
6. **`(?i)` for case-insensitivity**, never `[Bb]oth` classes — the class version
   silently misses `BOTH`.
7. **Put the regex on the decorator as** ``r"..."``. Named constants next to dispatch
   tables must equal that same string (unit-tested) so tests and live steps cannot drift.

## 5. Dispatch belongs in services

`scripts/check_step_style.py` forbids `if`/`for`/`try` and bare `assert` in step files
(max 8 statements). So a regex step that fans out to different behaviors dispatches via
a dict in `tests/services/`:

```python
_DUPLICATE_ROUTE_CHECKS: dict[str, Callable[[BankTransferContext], None]] = {
    "Shahin": peers_assert.assert_shahin_dup,
    "manual": _manual_dup,
    "Mellat": bt_assert.assert_duplicate_route_single_mongo_row,
    "Mellat dashboard": _dsh_dup,
    "IBAN Mellat": bt_assert.assert_duplicate_iban_second_handled,
}
```

An unknown key raises `KeyError` naming the known keys — a `.feature` typo fails with
an actionable message instead of a silent no-match.

## 6. Sentinel values — one step, three layers (UI/API/DB)

`tests/services/gherkin_values.py` provides:

- `coerce_gherkin_value(raw)` — Examples cells are always strings; this turns `"null"`
  → `None`, `"[]"` → `[]`, `"42"` → `42`, valid JSON → parsed, anything else → the
  original string. Leading-zero digit strings (`"0912…"` — phone numbers) stay strings
  on purpose.
- `register_db_sentinel(name)` / `resolve_expected_value(raw, **context)` — a step's
  expected value normally compares literally, but a registered sentinel cell computes
  it live:

```python
@register_db_sentinel("FeeFromDb")
def _fee_from_db(*, tracking_code: str, **_: object) -> int:
    return FeeDb().fee_for(tracking_code)

# in any Then step / assert service:
expected = resolve_expected_value(raw_expected, tracking_code=ctx.tracking_code)
```

One Gherkin sentence now validates against a literal *or* a DB-derived value, chosen by
the Examples table — no parallel `"… matches the DB"` step needed. This was the single
cleanest idea in the legacy framework's catalog, generalized so new sentinels don't
touch existing steps.

## 7. Unit-testing a step regex

Template (`tests/unit/test_step_regexes.py`):

```python
@pytest.mark.parametrize(
    ("text", "route_kind"),
    [
        ("duplicate Shahin routes keep a single transfer row", "Shahin"),
        ("the duplicate IBAN Mellat route keeps a single transfer row", "IBAN Mellat"),
    ],
)
def test_duplicate_route_step_matches(text: str, route_kind: str) -> None:
    match = re.fullmatch(DUPLICATE_ROUTE_STEP, text)
    assert match is not None
    assert match.group("route_kind") == route_kind


@pytest.mark.parametrize("text", ["duplicate routes keep a single transfer row"])
def test_duplicate_route_step_rejects(text: str) -> None:
    assert re.fullmatch(DUPLICATE_ROUTE_STEP, text) is None
```

Cover: every wording currently in `.feature` files, the captured values, and at least
one must-NOT-match sentence. Editing a regex then breaks a fast unit test, not a
30-minute BDD run. Every dispatch table key should also be asserted to have a matching
wording test, so table and features can't drift apart.

## 8. Anti-patterns (seen in the legacy framework — do not import)

| Anti-pattern | Why it's wrong | Do instead |
|---|---|---|
| `locals()[key] = int(...)` for coercion | doesn't reliably rebind locals in CPython | `coerce_gherkin_value()` |
| Reused group names across branches + post-match reassignment | branch structure invisible, fragile edits | distinct names per branch (§4.3) |
| Bare `.+` captures | steals unintended sentences | constrained classes (§4.4) |
| `[Bb]oth` casing classes | misses casings | `(?i)` flag |
| Generic `step_impl` names | ambiguous stack traces | this repo's `_descriptive_name` convention |
| One mega-step hiding several product checks | violates Visible-outcomes rule in `gherkin-style.mdc` | one Then line = one check |
| Technical Gherkin (`I POST to /wallets with header X`) | violates business-language rule | business sentence; tech detail only in API-contract scenarios |
| Same step text, different bodies in two modules | same sentence means two things | distinct wording or one shared step (see step-patterns.mdc "Traps") |

## 9. Where this is going (status)

- Shared infrastructure (`gherkin_values.py`, regex unit tests) and the first
  consolidated cluster (duplicate-routes, 6 → 1) landed on
  `chore/superapp-flexible-regex`.
- Login onboarding and dashboard bill UI now use canonical shapes 1–2.
- Shared `conftest.py` parse steps converted to constrained `parsers.re`
  (`cash-out goes through`, Nemo capability, telephone-pool `a/an`, bill rejections).
  Remaining `parsers.parse` steps migrate when that file is touched — not big-bang.
- Remaining cluster candidates: debit `treasury requests a … ACH direct payout …`,
  `the customer routes the same … tracking code twice`, Nemo fee-prediction families.
  Consolidate one cluster per MR, feature files unchanged, `make collect` count
  identical before/after.
- Same-text/different-body trap: Manual portal vs Nemo app split-weights must
  stay on distinct sentences (`DSH splits cash-out weights evenly between Manual
  and Mellat` vs `DSH splits Nemo cash-out weights evenly between Manual and
  Mellat`). Do not merge the step functions — they bind different fixtures.

## 10. IDE shows "Undefined step"?

Gherkin plugins scan step files for **quoted strings on the decorator**. Keep the
regex inline: ``@then(parsers.re(r"^...$"))``. An imported constant
(``parsers.re(SOME_STEP)``) is invisible to the plugin even though pytest-bdd binds it.

If the plugin still flags a line after the regex is inline, that is remaining plugin
limitation — runtime binding is the source of truth:

```bash
make steps-audit
```

That runs `pytest --generate-missing`. Two known false positives are pre-existing
`Scenario Outline` templates (`<product>`, `<tel status>`): the checker matches the
raw placeholder text, while pytest-bdd substitutes Examples first.
