# tool_build — recurring bug patterns + discipline rules

Single document for the failure modes that have already shown up more
than once in Phase 1 and the rules build-Claude is expected to follow
to keep them from recurring. Banked from the cross-Claude review wave
after Days 11-15.

When you fix one of these or notice it in review, **don't just patch
the instance** — confirm the rule below still describes the failure,
and update or extend the entry if reality has shifted.

**Updated:** 2026-05-05 (Day 16 cleanup pass)

---

## 1. Schema-version checks must read `SUPPORTED_SCHEMA_VERSIONS`

**The bug.** `runtime.py` (Day 11) hard-coded `'0001'` as the only
acceptable schema version. After migration `0002_started_orig_hero_unique`
landed, the server crashed silently before the lifespan startup log,
because the version check read `0002` and refused to start with no
visible reason.

**Why it recurs.** Each new component that needs schema-aware behavior
re-derives "what version is the schema". The first such derivation in
the codebase was a literal string. New code copies the pattern.

**Rule.** Every comparison against the schema version goes through
`constants.SUPPORTED_SCHEMA_VERSIONS`. When migration `0003+` lands,
add it to that frozenset in **one** place.

**How to apply.**
- Importing? `from constants import SUPPORTED_SCHEMA_VERSIONS`.
- Need to know the *current* head? Read `app_meta.schema_version` from
  state.db. Don't hardcode that either.
- New module checking schema? Audit it for literal `'0001'` /
  `'0002'` strings before merging.

---

## 2. FK-respecting cleanup must use `db.cascading_delete`

**The bug.** Tests opened sqlite connections and ran DELETE statements
in arbitrary order. `PRAGMA foreign_keys = ON` is set in `db.connect()`,
so deleting parents before children raises `IntegrityError: FOREIGN
KEY constraint failed`. Symptom: cleanup half-completes, next test run
fails on stale rows.

**Why it recurs.** Six tests independently reinvented the cleanup
block. Each one had to maintain the FK ordering by hand. New tables
(0002 added `started_orig`, future migrations will add more) silently
expand the graph; per-test blocks don't get updated.

**Rule.** Tests that key their data with `id LIKE 'test_<prefix>_%'`
must use `db.cascading_delete(prefix)`. The helper walks the graph
child-first and is the single place to update when the schema grows.

**How to apply.**
- Default: `db.cascading_delete("test_dXX_")`.
- Test keys data by *some other column* (e.g. `concepts.name LIKE`)?
  Helper doesn't apply — write the cleanup by hand AND add a comment
  explaining why the helper isn't used (so the next reader doesn't
  regress to the helper without thinking).
- Test touches a no-FK table not in the cascade order
  (`cross_ai_captures`, `tool_grammar_configs`, `app_meta`)? Helper
  ignores them; clean those rows directly after the helper call.
- Adding a new artifact table to migration `000N`? Update
  `_CASCADE_DELETE_ORDER` in `db.py` in the same commit.

---

## 3. Console output must tolerate non-ASCII (Windows cp1252)

**The bug.** Five-plus print statements across Days 8, 9, 12, 14, 15
crashed on `cp1252` consoles because they contained `→`, `—`, or
similar non-ASCII glyphs. `UnicodeEncodeError: 'charmap' codec can't
encode character`. Each instance was caught at test-run time, not
during the edit.

**Why it recurs.** It's invisible in source. The character looks fine
to the model writing it; the codec crashes only at runtime, only on
Windows, only on consoles that haven't been reconfigured. Day 10 added
`setup_console_encoding()` — but standalone test scripts didn't import
the module that called it.

**Rule.** Every entry point in `tool_build/` either imports `db`
(which runs `setup_console_encoding()` at module load) or calls the
function directly. There is no longer any need for individual modules
to defend their print statements.

**How to apply.**
- Writing a new test or CLI script? Make sure `import db` happens at
  the top. That's enough.
- Tempted to use a fancy glyph? Fine — the encoding fix is in. But
  consider whether ASCII would communicate the same thing more
  durably (some external log readers also struggle with mixed
  encodings).
- If a console crash *does* recur, the fix is broken upstream — chase
  the import chain, don't add ASCII-fallbacks per call site.

---

## 4. Edit anchors must include unique trailing context

**The bug.** Twice on Day 14, an `Edit` tool call used `def cost_breakdown`
as the anchor for an insertion. The new content didn't include a
*trailing* `def cost_breakdown(...)` line, so the Edit replaced the
function header with the new content and orphaned the function body.
Symptom: `AttributeError: module 'dispatcher' has no attribute
'cost_breakdown'` on import.

**Why it recurs.** When the goal is "insert before X", it's easy to
forget that Edit is *replacement*, not insertion. The natural mental
model "anchor on X, prepend new code" doesn't survive the tool's
actual semantics.

**Rule.** When using Edit to insert before or after a known anchor,
the `new_string` MUST contain the anchor verbatim. Best discipline:
include enough surrounding context (≥1 line above + ≥1 line below the
edit point) that displacement of the anchor is impossible.

**How to apply.**
- Inserting *before* a function: include the `def funcname(...)` line
  and ideally its first body line in `new_string`.
- Inserting *after* a function: include the function's last line and
  ideally a blank-line separator in `new_string`.
- Refactoring? Verify with a Read of the changed region after every
  Edit, not just at the end of the batch. Catching displacement on
  edit N is cheaper than catching it on import-time crash after edit
  N+5.

---

## 5. `_assert(cond)` must accept a default message

**The bug.** Several test files defined `_assert(cond, msg)` with `msg`
as a required positional arg, then called `_assert(some_condition)`
elsewhere. `TypeError: _assert() missing 1 required positional argument:
'msg'`. The test crashed on the *failing* assertion, masking the actual
test failure.

**Why it recurs.** Helper authors thought "every assert needs a
message"; helper callers thought "this one's obvious enough not to
need a message". Both are reasonable; the conflict only surfaces when
the assert fires.

**Rule.** Every test-helper `_assert` must give `msg` a default value
(`msg="assertion failed"`).

**How to apply.**
- New test file? Copy the signature from `test_acceptance.py`:
  `def _assert(cond, msg="assertion failed"):`.
- Reviewing a PR with a new test helper? Check the signature; this is
  one of the easier review-time catches.
- Don't aim for descriptive defaults — `"assertion failed"` plus the
  traceback is enough; a long default disguises the assert as
  intentional output.

---

## 6. Pydantic model fields must not shadow `BaseModel` attributes

**The bug.** `ConceptCreate` (Day 14) declared a field named `register`,
which shadowed `pydantic.BaseModel.register`. Cosmetic at runtime —
warning at model-class construction — but the warning is noisy and
the shadowed method is genuinely unavailable on the class.

**Why it recurs.** The domain vocabulary ("register" is a discipline
field per the spec) collides with framework internals. Easy to miss
unless you've been bitten before.

**Rule.** Before adding a field to a Pydantic model, scan
`pydantic.BaseModel`'s public attribute surface for a name collision.
Common offenders: `register`, `validate`, `copy`, `dict`, `json`,
`fields`, `parse`, `construct`, `schema`.

**How to apply.**
- Hit a collision? Use `Field(..., alias="register")` so the wire
  contract stays clean (JSON still says `register`) but the Python
  attribute is renamed (e.g. `register_value`).
- If aliasing breaks reads, prefer `model_config =
  ConfigDict(populate_by_name=True)` and access through the alias.
- Phase 2: revisit `ConceptCreate.register` — the warning is currently
  banked but should be properly aliased before the API contract gets
  baked in elsewhere.

---

## How to extend this document

- A pattern lands here once the same root cause has caused **two
  separate bugs**. One-off mistakes go in commit messages, not here.
- The format is: bug, why it recurs, rule, how to apply. The "why it
  recurs" line is what stops this from being a list of platitudes —
  it tells future-you what to look for to recognize the failure mode
  before it bites again.
- When a rule is *enforced by infrastructure* (e.g. `cascading_delete`,
  `setup_console_encoding`), say so explicitly. Rules enforced only
  by reviewer attention drift; rules enforced by code don't.
