# Migration 0004 — DRAFT (Phase 3 Wave 1 Day 1-2 implementation spec)

**Date:** 2026-05-07
**Status:** v1.0 DRAFT — preparatory spec for Wave 1 Day 1-2 implementation. NOT the actual `migrations/versions/0004_*.py` file (that lands when Phase 2 acceptance bridge crosses + Wave 1 Day 1-2 code starts). Surfaces schema decisions + atomicity decisions now so implementation is mechanical transcription.
**Source:** `phase3_design_notes.md` v0.2 §"Migration 0004 schema sketch" + atomicity-per-table table.

---

## Scope

Migration 0004 carries (per phase3_design_notes v0.2):
- ✅ `notes_md_state` (new — F6 status view + template_version tracking)
- ✅ `cross_ai_captures` 7-column expansion (F7 capture surface)
- ✅ `idx_verdicts_flagged` partial index (Phase 2 v0.6 carryover)
- ✅ `unknown_image_terminal` value in `renders.tool` taxonomy (application-level; no schema change)
- ❌ `doc_set` table — DEFERRED to Phase 3.5 (per v0.2 §"What v0.2 still defers")
- ❌ `scenes` / `scene_id` column on renders — NOT NEEDED per F8 adapter mapping decision (scene_id derived at serialization time via `concept.section` join with `'unscoped'` fallback; no schema change)

**Atomicity:** all changes additive. No temp-table-and-copy pattern needed (Phase 2 Migration 0003's verdicts rebuild was the only one needing that).

**Bumps `app_meta.schema_version` 0003 → 0004** per migration boilerplate (Phase 1 Day 5-9 §3.7 / F5 pattern; see 0001 + 0002 + 0003 precedents).

---

## SQL — per-table operations

### Step 1: `notes_md_state` (new table)

Per v0.2 §"Migration 0004 schema sketch": per-section row for F6 NOTES.md status tracking. Section-as-PRIMARY-KEY because canonical sections are the durable unit (per v0.1 review item 7a Option C — concepts attach via existing `concepts.section` foreign-key relationship, no junction table needed).

```sql
CREATE TABLE notes_md_state (
    section TEXT PRIMARY KEY,
    template_version TEXT NOT NULL,
    authored_against_discipline_version TEXT NOT NULL,
    last_authored TEXT,                  -- ISO timestamp of most recent authoring pass
    last_modified_filepath TEXT,         -- canonical filepath of the NOTES.md file
    last_authored_by TEXT,               -- 'human' | 'claude_assisted'
    notes TEXT,                          -- free-text notes (e.g., reasons for staleness)
    yaml_path TEXT NOT NULL,
    created TEXT NOT NULL,
    modified TEXT NOT NULL
);
CREATE INDEX idx_notes_md_state_template_version ON notes_md_state(template_version);
CREATE INDEX idx_notes_md_state_authored_against ON notes_md_state(authored_against_discipline_version);
```

**Population pattern** (Wave 1 walker extension, NOT this migration):
- Walker pass on `projects/latent_systems/ep1/<section>/NOTES.md` discovers existing files; populates one row per section with current state.
- F6 `author_notes_md` endpoint inserts/updates rows when Joseph saves through audit-viewer-extension UI.
- F8 trigger reads `last_authored` recency to decide whether section is "ready to serialize."

**Why `section` as PRIMARY KEY (not synthetic id):** sections are stable (h1_hook never renames to h1_intro mid-project; would be an architecture change requiring discrete handling). Stable natural key removes the join-by-derived-id pattern that test infrastructure had to work around (per AUDIT_PATTERNS Pattern #7).

**FK to anything?** No. Section is a TEXT primary key; concept.section reference resolves via match (`concepts.section = notes_md_state.section`). No FK constraint enforced because Phase 1 concepts.section had no constraint either; preserving the unconstrained convention.

### Step 2: `cross_ai_captures` expansion (ALTER + 7 new columns + 2 indexes)

Per v0.2 §"Migration 0004 schema sketch" + v0.1 review item 7c: expansion needed for F7 capture surface. Existing schema (`id, source, discipline_version, yaml_path, captured`) is insufficient for relevance-binding + compressed-input + AI-expansion pair-tracking.

```sql
ALTER TABLE cross_ai_captures ADD COLUMN relevance_binding_type TEXT;
ALTER TABLE cross_ai_captures ADD COLUMN relevance_binding_id TEXT;
ALTER TABLE cross_ai_captures ADD COLUMN original_input_text TEXT;
ALTER TABLE cross_ai_captures ADD COLUMN expansion_text TEXT;
ALTER TABLE cross_ai_captures ADD COLUMN paired_capture_id TEXT;
ALTER TABLE cross_ai_captures ADD COLUMN provider TEXT;
ALTER TABLE cross_ai_captures ADD COLUMN consultation_cost_usd REAL DEFAULT 0;
CREATE INDEX idx_cross_ai_captures_relevance ON cross_ai_captures(relevance_binding_type, relevance_binding_id);
CREATE INDEX idx_cross_ai_captures_paired ON cross_ai_captures(paired_capture_id) WHERE paired_capture_id IS NOT NULL;
```

**Column rationale:**
- `relevance_binding_type` + `relevance_binding_id`: which finding/decision/concept this capture relates to. Type discriminates the binding scope (e.g., "concept" / "verdict" / "decision_log_entry"); id is the target's ID. v0.2 default per Q4 confirmation: last-touched finding/decision; editable before save.
- `original_input_text`: Joseph's compressed input verbatim (separate from the YAML body which carries the captured exchange).
- `expansion_text`: Claude's expansion of compressed input via M3 pattern (separate from raw external-AI capture).
- `paired_capture_id`: self-FK pattern matching `verdicts.supersedes_verdict_id` (Phase 2 Q2 precedent). When a Joseph-input + Claude-expansion pair gets stored as two rows, the second row's `paired_capture_id` references the first.
- `provider`: which external AI produced the captured exchange (Perplexity / ChatGPT / Grok / Gemini / parallel-Claude). Mirrors `ai_consultations.provider` for consistency.
- `consultation_cost_usd`: cost rollup parallel to `ai_consultations`; relevant when M3 compressed-input expansion runs against Claude API.

**FK on `paired_capture_id`?** Self-FK same shape as `verdicts.supersedes_verdict_id`. NOT enforced via SQLite FK constraint (would require temp-table-and-copy for ALTER TABLE; this migration commits to additive-only). Application-level integrity: F7 endpoint validates referenced capture exists before INSERT. Acceptable since cross_ai_captures is append-mostly + integrity violation surfaces as orphan paired_capture_id which `_sweep_orphans`-style cleanup catches.

### Step 3: `verdicts` partial index (Phase 2 v0.6 carryover)

Per Phase 2 v0.6 deferral + v0.1 review item 12: makes the `flagged_only` filter in `audit.list_audit_queue` use index seek instead of sequential scan.

```sql
CREATE INDEX idx_verdicts_flagged ON verdicts(flags_needs_second_look)
    WHERE flags_needs_second_look = 1;
```

Partial index — only flagged verdicts indexed. Tiny migration, makes the v0.6 indexed-query promise real. Currently sequential scan on ~1700-verdict scale; index seek matters as verdict count grows in Wave A audit work.

### Step 4: `renders.tool` taxonomy extension (application-level)

Per v0.2 §"Migration 0004 schema sketch" + v0.1 review item 10 + AUDIT_PATTERNS Pattern #8 (content-matching specification too-broad-by-default): add `unknown_image_terminal` as a valid `renders.tool` value.

**No SQL change required.** SQLite `tool TEXT` column accepts the new value without schema modification. Walker code adds the value via `walker.classify()` extension when filepath-heuristics pass exhausts recovery options for a render previously marked `unknown_image`.

**Code-level changes (Wave 1 Day 2-3, separate from migration but tracked here for completeness):**

```python
# walker.py — extend classify() return values
# Existing: midjourney | gpt_image_2 | kling | flux | frame_extract |
#           video | audio | unknown_image | unknown
# Extension: + unknown_image_terminal

def classify(filename: str) -> tuple[str, Optional[int]]:
    """... existing logic ... fallback to unknown_image for .png ..."""
    # No change to classify() itself; walker's reclassify-by-filepath-heuristics
    # pass marks 'unknown_image' rows as 'unknown_image_terminal' when recovery
    # via filepath inspection exhausts options.

def reclassify_by_filepath(*, dry_run=False) -> dict:
    """Wave 1 Day 2-3: extend filename-pattern recovery with filepath
    heuristics. For renders still tagged 'unknown_image' after Phase 2
    Day 1's filename pass, inspect filepath context. Recover ~50% of
    the 367 truly-opaque files (per v0.1 review item 7 estimate).
    Mark remainder 'unknown_image_terminal' to stop indefinite recovery
    work (per AUDIT_PATTERNS Pattern #8 banking)."""
    pass
```

### Step 5: schema_version bump

Per migration boilerplate (Phase 1 Day 5-9 §3.7 / F5 pattern; see 0001 + 0002 + 0003 precedents):

```sql
INSERT OR REPLACE INTO app_meta (key, value, updated)
VALUES ('schema_version', '0004', '<iso_now_at_migration_time>');
```

Update `constants.py`:
```python
SUPPORTED_SCHEMA_VERSIONS = frozenset({"0001", "0002", "0003", "0004"})
```

Per AUDIT_PATTERNS Pattern #1: schema_version checks must read `SUPPORTED_SCHEMA_VERSIONS`. After 0004 lands, `runtime.py` + walker schema-check + serve.py startup all pick up the new version automatically since they read from constants.

---

## downgrade() — reverse migration

```python
def downgrade() -> None:
    # Reverse step 5: bump back to 0003
    now = datetime.now(timezone.utc).isoformat()
    op.execute(
        f"INSERT OR REPLACE INTO app_meta (key, value, updated) "
        f"VALUES ('schema_version', '0003', '{now}')"
    )

    # Reverse step 3: drop verdicts partial index
    op.execute("DROP INDEX IF EXISTS idx_verdicts_flagged")

    # Reverse step 2: drop cross_ai_captures indexes + columns.
    # SQLite ALTER TABLE DROP COLUMN requires SQLite 3.35+ (modern
    # Python ships with newer; check before relying on this). For
    # portability use temp-table-and-copy pattern OR accept that
    # downgrade leaves columns in place (data harmless; columns nullable).
    op.execute("DROP INDEX IF EXISTS idx_cross_ai_captures_paired")
    op.execute("DROP INDEX IF EXISTS idx_cross_ai_captures_relevance")
    # Per Migration 0002 precedent: leave columns in place rather than
    # ALTER TABLE DROP COLUMN. Data is harmless; columns are nullable;
    # re-applying upgrade is idempotent (ALTER TABLE ADD COLUMN
    # silently fails if column exists, OR runs successfully against
    # fresh tables). Bank decision in this docstring.

    # Reverse step 1: drop notes_md_state + indexes
    op.execute("DROP INDEX IF EXISTS idx_notes_md_state_authored_against")
    op.execute("DROP INDEX IF EXISTS idx_notes_md_state_template_version")
    op.execute("DROP TABLE IF EXISTS notes_md_state")

    # Step 4 has no schema-level reverse: 'unknown_image_terminal' is
    # an application-level taxonomy extension. Walker code change
    # reverts via git revert; database-side is no-op.
```

---

## Migration test plan

**Pre-migration state assertions:**
- `app_meta.schema_version = '0003'`
- `notes_md_state` table does NOT exist
- `cross_ai_captures` columns: id, source, discipline_version, yaml_path, captured
- `idx_verdicts_flagged` index does NOT exist
- `renders.tool` enum contains the 9 Phase 2 values (no `unknown_image_terminal` yet)

**Post-migration state assertions (run via test_acceptance.py extension at Wave 1 close):**
- `app_meta.schema_version = '0004'`
- `notes_md_state` table exists with the 11 declared columns + 2 indexes
- `cross_ai_captures` columns: original 5 + 7 new = 12 total + 2 new indexes
- `idx_verdicts_flagged` index exists (verify via `PRAGMA index_list(verdicts)`)
- Walker can write `unknown_image_terminal` to `renders.tool` without schema rejection

**Data preservation assertions:**
- `verdicts` row count unchanged (all rows have `flags_needs_second_look = 0` post-migration; partial index empty initially)
- `cross_ai_captures` row count unchanged (currently empty in production state; new columns NULL on existing rows)
- `renders` rows unchanged (no taxonomy reclassification at migration time; that's Wave 1 Day 2-3 walker work)

**Round-trip test (downgrade → upgrade):**
- Apply Migration 0004 upgrade
- Apply Migration 0004 downgrade
- Verify post-downgrade state matches pre-migration state (modulo cross_ai_captures columns which stay per Migration 0002 precedent — accepted cost banked above)
- Re-apply upgrade: idempotent

---

## Open questions for Wave 1 Day 1-2 implementation

1. **`notes_md_state.section` PRIMARY KEY constraint.** Sections are stable but the canonical section list isn't enumerated anywhere queryable. Should Migration 0004 also seed `notes_md_state` with the 16 known EP1 sections (h1_hook through h9_ep2_tease + cold_open + section_1c + card-* + k1_compulsion_choice + k_frames + audio + beds + references + stills + typography), with `last_authored = NULL` for sections without existing NOTES.md? Or seed only the narrative-bearing sections (10 entries: h1-h9 + cold_open)?

   **Recommendation:** seed the 10 narrative-bearing sections at migration time. Production-support sections (audio, beds, references, stills, typography, k_frames) get added by F6 walker pass as they earn NOTES.md coverage. Bank decision in 0004 migration.

2. **`cross_ai_captures.relevance_binding_type` enum constraint.** Bind types: concept | verdict | decision_log_entry | finding | (open list). Phase 3 v0.2 doesn't enumerate; F7 endpoint validates application-level. Should Migration 0004 add a CHECK constraint, or leave open?

   **Recommendation:** leave open (TEXT, no CHECK). F7 endpoint validates against an expanding list; new types land via application-level update without schema migration. Mirrors `ai_consultations.provider` permissive TEXT pattern.

3. **`paired_capture_id` self-FK enforcement.** Phase 2 Migration 0003 used temp-table-and-copy to add FK on `verdicts.audit_session_id` + `verdicts.supersedes_verdict_id`. Should `cross_ai_captures.paired_capture_id` use same pattern, or accept application-level integrity?

   **Recommendation:** application-level. Migration 0004 commits to additive-only atomicity (per v0.2 atomicity table). The integrity violation surface is small (orphan paired_capture_id; cleanup catches via _sweep_orphans-style walks). Phase 3.5 may upgrade to FK if integrity issues surface in real F7 use.

4. **`unknown_image_terminal` filepath-heuristics scope.** The Wave 1 Day 2-3 reclassify-by-filepath-heuristics pass is preparatory work mentioned but not scoped in detail in v0.2. What filepath patterns recover the 367 truly-opaque files? Sketch should land before Wave 1 Day 2 starts to scope honestly.

   **Recommendation:** author `FILEPATH_HEURISTICS_DRAFT.md` as separate preparatory doc (Wave 1 Day 2 input). Out of Migration 0004 scope; tracked here for forward visibility.

5. **`notes_md_state` walker enumeration trigger.** Walker discovers NOTES.md files at `--init` time + when explicitly invoked. F6 endpoint also writes to the table when Joseph saves. Should Wave 1 Day 1 add an explicit `walker --enumerate-notes-md` flag, or piggyback on existing `--init` walker pass?

   **Recommendation:** piggyback on `--init`. Walker's existing canonical-file enumeration just gets extended with NOTES.md → notes_md_state insertion. Single-pass discipline; no new CLI flag required.

---

## Migration file path + Alembic revision

When Wave 1 Day 1-2 lands the actual migration:
- Path: `projects/latent_systems/tool_build/migrations/versions/0004_<short_descriptor>.py`
- Suggested descriptor: `notes_md_state_and_cross_ai_expansion`
- Alembic revision: `0004`; down_revision: `0003`
- Module docstring: reference this draft + phase3_design_notes.md v0.2

Mirrors Phase 2 Migration 0003's file layout + docstring pattern.

---

## Document maintenance

- **v1.0 DRAFT (2026-05-07):** Phase 3 Wave 1 Day 1-2 preparatory spec. SQL drafted + atomicity decisions banked + downgrade plan + test plan + 5 open questions for implementation. Lives in `tool_build/` (sibling to PHASE_2_E2E_PLAN.md + F8_OPENMONTAGE_ADAPTER_MAPPING.md as design-spec docs). Implementation transcribes from this when Phase 2 acceptance bridge crosses + Wave 1 Day 1-2 unblocks.
