# LATENT SYSTEMS — Tool-build Phase 3 Design Notes

**Date:** 2026-05-07
**Status:** v0.2 — cross-Claude review wave on v0.1 SCAFFOLD folded in (5 must-fix amendments + 8 nice-to-haves + 3 reorderings + Joseph's Q1 pick (a)). Phase 3 doesn't start (code-wise) before Phase 2 acceptance bridges; v0.2 is the substrate Wave 1 starts from once that gate crosses.
**Source material:** v1 Spec Proposal v0.5 (`tool_build/v1_spec_proposal.md`) Phase 3 paragraph; Phase 2 Design Notes v0.6 maintenance log (5 banked Phase-3-estimating signals); `banked_items.md` Phase 3 territory section; F6 / F7 / F8 / F12 / M4 / M5 audit findings; OpenMontage `schemas/artifacts/edit_decisions.schema.json` + `asset_manifest.schema.json` (read in v0.1 review wave); v0.1 → v0.2 cross-Claude review wave (10 pressure-tests + 6 Issues + 16 ranked amendments).
**Purpose:** Settle Phase 3 entry assumptions before Wave 1 code starts. v0.2 commits to schema decisions + scope refinements + revised estimate that v0.1 SCAFFOLD deferred or under-counted.

---

## Document scope

**What v0.2 commits to:**
- F8 scope: asset_manifest only; edit_decisions explicitly deferred to OpenMontage's edit agent (per Finding C-D in v0.1 review).
- scene_id mapping decision (per Finding B): derived at serialization time via `prompt → concept → section` join; `'unscoped'` fallback for unbound renders. NOT a stored schema column → Migration 0004 doesn't add it.
- F5 + F7 reclassified from substrate-on-substrate to partially-novel (~1-2 days estimate adjustment per).
- F6 acceptance bridge magnitude: ~1-2 weeks Joseph editorial work (~10 sections × 200-500 words/template). Joseph picked option (a) — accept and bank as-is; templates authored in parallel with Phase 3 Wave 1-3 code so both ready by Wave 5.
- Phase 2 acceptance bridge gate expanded: explicit Phase 2 v0.6 must-fix amendments checklist (all confirmed landed in commit `f10b2b6`).
- Migration 0004 atomicity notes per-table.
- cross_ai_captures expansion sketched (7 new columns named).
- F8 schema-read pulled forward to Wave 1 Day 1 (Revision 1).
- Wave 1 explicit sequencing (Migration 0004 → F6 code → F5 atomic action).
- Wave 3 explicit UX validation day for F7 capture surface.
- `unknown_image_terminal` → renders.tool taxonomy extension.
- Code days vs acceptance days separation in wave estimates.
- Settle Q1 (hero promotion in audit viewer with confirmation modal).
- Revised estimate: 21-32 days code (median ~3.5-4 weeks) + 1-2 weeks acceptance bridge in parallel.

**What v0.2 still defers to v0.3+:**
- doc_set schema (Item 7b deferred to Phase 3.5; F12 reference resolution rides on existing canonical-doc structure for v0.1 of F12).
- Concrete Migration 0004 SQL (sketched per-table; full SQL lands in code).
- Detailed failure-mode behavior per F5 / F6 / F7 / F8 (categories named in v0.1; behavior detail at code time).
- F6 NOTES.md template seed scaffolding (Claude work; lands during Wave 2).
- F7 capture surface UX shape (validated Day 1 of Wave 3 against real capture session before form locks).
- v0.3 cross-Claude review wave on v0.2 (optional — recommend after Phase 2 acceptance bridges to fold real-world data).

---

## Phase 2 acceptance bridge gate (expanded checklist)

Per cross-Claude review v0.6 + v0.1 review Issue 6: Phase 3 doesn't start before Phase 2 acceptance bridges from "code-shipped" to "acceptance-validated." Bridge components:

**Phase 2 v0.6 must-fix amendments (all landed):**
- ✅ `consult_render` default change to `create_verdict_if_missing=True` (Joseph's Q1 v0.6 pick — bulk-seed workflow). Banked in commit `f10b2b6`.
- ✅ `_SAFETY_REFUSAL_RE` tightening to verb-aware pattern. Commit `f10b2b6`.
- ✅ `PHASE_2_E2E_PLAN.md` v0.6 amendments (latency methodology, Step 10.5 supersession, multi-AI deferral). Commit `f10b2b6`.
- ✅ Fifth Phase-3-estimating signal banked. Commit `f10b2b6`.
- ✅ Rubric seed scaffold landed. Commit `03cbbe6`.

**Acceptance-validation bridge (still pending):**
- ⏳ Joseph: rubric authoring (~5-15 min copy + ~3-4 hours editorial work; revised from "~5-15 min" per Phase 2 review actual measurement).
- ⏳ One real Wave B firing per `PHASE_2_E2E_PLAN.md` (~30 min + ~$0.30).
- ⏳ Bank result in `banked_items.md`.

Until acceptance-validation bridge crosses, Phase 3 Wave 1 code is on hold. v0.2 (this doc) is preparatory.

---

## Banked Phase-3 estimating signals (revised application per v0.1 review)

Per Phase 2 design-notes maintenance log + v0.1 review item 1 (signal application correction):

1. **spec-estimate-undercut** (Phase 1): first-phase estimates undershoot by ~50%.
2. **spec-mechanism-undercut** (Phase 2 Day 1): inspect actual data Day 1 of each phase before committing to mechanism. *Applied in v0.2 by reading OpenMontage schemas during v0.1 review wave (Findings A-E surfaced scene_id + edit_decisions issues that would have cascaded as late-phase risk).*
3. **spec-role-overspecification** (Phase 2 Day 2): distinguish mechanical vs decision work explicitly. *Applied in v0.2 via separate "code days" vs "acceptance bridge time" estimates per wave.*
4. **spec-overestimate-when-substrate-is-mature** (Phase 2 close): substrate-on-substrate compresses 5-10×; novel external integration doesn't. *Applied in v0.2 by reclassifying F5/F7 from substrate-on-substrate to partially-novel; F8 stays novel-external.*
5. **user-blocking work** (Phase 2 v0.6): user-prerequisites are e2e-acceptance blockers even when design says non-blocking. *Applied in v0.2 by naming F6 NOTES.md template authoring (~1-2 weeks Joseph) and F8 OpenMontage compose-stage testing as bridge costs upfront.*

**v0.2 Phase 3 estimate:**

Code days: **21-32 days (median ~3.5-4 weeks)**, revised from v0.1's 17-28 days. Drivers:
- F5 reclassification from substrate-on-substrate to partially-novel (+~1-2 days for atomic-transaction coordination over net-new doc_set + F6 prompt).
- F7 reclassification (+~1-2 days for M3 compressed-input + AI-expansion novel pattern).
- F8 schema-read pulled forward (+~1-2 days Wave 1 Day 1).

Acceptance bridge time (parallelizable with code days): **~1.5-2.5 weeks**, dominated by:
- F6 NOTES.md template authoring: 5-15 hours Joseph editorial (~10 sections × 200-500 words/template); 2-3 iteration cycles before stabilization.
- F8 OpenMontage compose-stage real-asset testing: ~1-3 days compose pipeline reactivation + iteration.
- Joseph drives both in parallel with Wave 1-4 code.

**Total time-to-Phase-3-acceptance:** 4-6 weeks calendar (code + acceptance bridges parallel), assuming Joseph editorial bandwidth permits parallel work. Spec said 2-3 weeks; v0.1 SCAFFOLD said ~3 weeks median; v0.2 honest revised range matches signal 1's empirical pattern (~50% undercut on first authoring; v0.2 review wave is the correction).

---

## Phase 3 features overview (v0.2 reclassifications applied)

### F5 — Hero promotion atomic action (PARTIALLY-NOVEL, revised from v0.1's substrate-on-substrate)

Per v0.1 review item 2: F5's atomic action requires (a) verdict marking ✅ substrate, (b) hero_promotions schema ✅ substrate, (c) file-move to `winners/` ✅ substrate, (d) NOTES.md update prompt ⚠️ depends on F6 net-new, (e) doc-set data model lookup ⚠️ net-new (or deferred per v0.2 doc_set decision below), (f) atomic-action transaction across all of above ⚠️ net-new coordination work.

**Code days revised:** ~3-4 days (not the 1-2 of pure substrate work) because the atomic transaction coordinates across new components.

**v0.2 Q1 settled (per v0.1 review Issue 4):** F5 hero-promotion button ships in audit viewer (next to verdict-marking buttons). Single button + confirmation modal. Modal exposes the multi-step action: file move + hero_promotions row write + NOTES.md update prompt (when F6 ready) + doc-update coordination summary. Joseph confirms before commit; avoids accidental clicks committing irreversible state. Avoids context-switch (Joseph already in audit viewer when deciding "this is a hero").

### F6 — NOTES.md authorship via Claude API (substrate-on-substrate code; user-blocking acceptance)

Per v0.1 review item 5: code path is genuinely substrate-on-substrate (existing llm.py + template-menu pattern + api_calls table). **Code days: ~3-4.** Acceptance is the dominant cost.

**Acceptance bridge magnitude (per Joseph's Q1 v0.2 pick (a)):** ~1-2 weeks Joseph editorial. ~10 EP1 sections × 200-500 words/template. 2-3 iteration cycles likely as template structure surfaces (design work disguised as authoring).

**Strategic implication:** Joseph starts NOTES.md template scaffolding during Phase 2 acceptance bridge (in parallel with rubric authoring + Wave B firing). Front-loads the work so Phase 3 code lands against partial templates. Phase 2 acceptance bridge pending; Phase 3 v0.2 settling now creates a window where Joseph can begin template work without blocking on Phase 2 close.

Claude work supports the bridge:
- Wave 2 Day 1: scaffold templates per-section using existing canonical content (`HANDOFF_2026-05-02.md`, `EP1_STRUCTURAL_ARCHITECTURE_v*.md`, `render_craft_exemplars/`). Scaffolds carry per-section structure; Joseph fills in body content.
- Estimated Claude scaffold work: ~3-5 hours for 10 templates.

### F7 — Cross-AI / cross-Claude capture surface (PARTIALLY-NOVEL, revised from v0.1's substrate-on-substrate)

Per v0.1 review item 3: code path uses existing llm.py + form-handling substrate, BUT the M3 compressed-input + AI-expansion pattern is explicitly novel ("hasn't been built before" per spec). The capture-surface UX shape is also unproven (Q4 v0.2 default not yet validated against real capture friction).

**Code days revised:** ~4-6 days (not v0.1's 3-4) matching Phase 2 audit-consultation effort. Includes:
- ~1 day form scaffold + endpoint
- ~1-2 days M3 compressed-input + AI-expansion prompt structure design + iteration
- ~1 day pair-tracking (Joseph-input + Claude-expansion paired records)
- ~1 day source attribution + relevance binding logic
- ~1 day UX validation against real capture session before form locks (per v0.1 review Issue 2 → Wave 3 Day 1)

### F8 — Serialization to OpenMontage (NOVEL EXTERNAL — scope reduced to asset_manifest only per v0.2)

**v0.2 scope amendment (per v0.1 review Finding C-D + Issue 5):** F8 ships `asset_manifest` only. `edit_decisions` deferred to OpenMontage's edit agent — that requires editorial timing decisions (in_seconds/out_seconds on cuts) tool_build doesn't capture and is structurally OpenMontage's responsibility, not tool_build's.

**Architectural division banked:** tool_build produces asset inventory (asset_manifest); OpenMontage edit agent produces editorial decisions (edit_decisions). Per spec AD-2 OpenMontage / tool-build boundary, this division is consistent: tool-build owns upstream-of-compose, OpenMontage owns compose+render. asset_manifest is the upstream-of-compose handoff; edit_decisions is the compose-stage's input.

**scene_id mapping (per v0.1 review Finding B):** scene_id is required on every `asset_manifest.assets[]` entry but tool_build has no scenes concept. **v0.2 decision: scene_id derived at serialization time, NOT a stored schema column.**
- Bound renders (renders.prompt_id NOT NULL): `scene_id := concept.section` via prompt→concept join.
- Unbound renders (renders.prompt_id NULL — applies to all 1707 pre_v1 renders + any future unbound): fallback `scene_id := "unscoped"`.
- No Migration 0004 column needed for scene_id; serialization computes.

**Code days: ~3-5 days** (asset_manifest only). Includes:
- ~1-2 days schema-aware mapping (already partially done via v0.1 review schema-read; full mapping doc in Wave 1 Day 1)
- ~1 day per-section trigger via NOTES.md-complete event
- ~1 day Joseph review surface for serialized JSON
- ~1 day scene_id mapping + unscoped fallback + edge cases

**v0.2 amendment per v0.1 review Revision 1 (F8 schema-read forward):** Wave 1 Day 1 reads OpenMontage schemas + drafts adapter mapping doc. Splits F8 into:
- Wave 1 Day 1: schema-read + adapter mapping draft (no code yet).
- Wave 4: trigger + serialization + review surface implementation (depends on F6 NOTES.md-completion event).

This surfaces blockers early (item 6 found scene_id + edit_decisions issues that would have cascaded as late-phase risk if discovered Wave 4).

### Phase 2 carryovers

Per banked_items.md Phase 3 territory section + v0.1 review:

- **Tool-grammar config expansion to GPT Image 2 + Kling + ElevenLabs** — depends on Phase 1 + Phase 2 successful_examples accumulation. Trigger: when verdict-confirmed-strong outputs seed enough data per Q3.
- **3a hardening review** — largely landed Phase 1 Day 12; Phase 3 audit confirms no remaining gaps after real Wave B usage.
- **Render-group compare-and-rank view (F5+ extension)** — banked design questions in `banked_items.md`. Phase 3.5 if friction surfaces.
- **Filepath-heuristics recovery + `unknown_image_terminal`** — per v0.2 amendment item 8g: extend `renders.tool` enum with `unknown_image_terminal` value (single-column query consistency with existing `unknown_image` recovery-state encoding). Phase 3 Wave 1 walker pass attempts filepath heuristics on the 367 truly-opaque files; remainder marked `unknown_image_terminal` to stop indefinite recovery work.

---

## Migration 0004 schema sketch (v0.2; SQL deferred to Wave 1 Day 1-2)

**Atomicity notes per-table** (per v0.1 review item 8b):

| Table | Operation | Atomicity pattern |
|---|---|---|
| `notes_md_state` | NEW table | Additive — simple CREATE TABLE |
| `cross_ai_captures` | ALTER + add columns | Additive — ALTER TABLE ADD COLUMN per column |
| `audit_thumbnails` (carryover) | unchanged | n/a |
| `verdicts` | NEW partial index `idx_verdicts_flagged` | Additive — CREATE INDEX |
| `renders` | NEW value `unknown_image_terminal` in tool enum | Application-level; SQLite TEXT column accepts; no DB-level enum constraint |
| `doc_set` | DEFERRED to Phase 3.5 | n/a; F12 reference resolution rides on canonical-doc structure for v0.1 of F12 |

No table requires temp-table-and-copy pattern (Phase 2 Migration 0003's verdicts rebuild was the only one needing that pattern; Migration 0004 is fully additive).

**`notes_md_state` table sketch:**

```sql
CREATE TABLE notes_md_state (
    section TEXT PRIMARY KEY,        -- canonical section name (h1_hook, h5_slot_machine, etc.)
    template_version TEXT NOT NULL,  -- version of the template used (1.0, 1.1, ...)
    authored_against_discipline_version TEXT NOT NULL,
    last_authored TEXT,              -- ISO timestamp of most recent authoring pass
    last_modified_filepath TEXT,     -- canonical filepath of the NOTES.md file
    last_authored_by TEXT,           -- 'human' | 'claude_assisted'
    notes TEXT,                      -- free-text notes (e.g., reasons for staleness)
    yaml_path TEXT NOT NULL,
    created TEXT NOT NULL,
    modified TEXT NOT NULL
);
CREATE INDEX idx_notes_md_state_template_version ON notes_md_state(template_version);
CREATE INDEX idx_notes_md_state_authored_against ON notes_md_state(authored_against_discipline_version);
```

Section ↔ concept many-to-many handled via existing `concepts.section` foreign-key relationship per v0.1 review item 7a Option C: `SELECT concepts.* FROM concepts WHERE concepts.section = notes_md_state.section`. notes_md_state stores per-section state; concepts attach via existing schema. No junction table needed.

**`cross_ai_captures` expansion** (per v0.1 review item 7c — 7 new columns):

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

`paired_capture_id` is self-FK pattern matching `verdicts.supersedes_verdict_id` (Phase 2 Q2 precedent). `provider` mirrors `ai_consultations.provider` for consistency. `consultation_cost_usd` enables cost rollup parallel to ai_consultations.

**`verdicts` partial index** (carryover from Phase 2 v0.6 deferred per Q2):

```sql
CREATE INDEX idx_verdicts_flagged ON verdicts(flags_needs_second_look) WHERE flags_needs_second_look = 1;
```

Makes the Phase 2 Wave A `flagged_only` filter in `list_audit_queue` use index seek instead of sequential scan. Tiny migration, makes the v0.6 indexed-query promise real.

**`renders.tool` enum extension:** add `unknown_image_terminal` as a valid value. No schema change (column is TEXT); walker code adds the value when filepath-heuristics pass exhausts recovery options for a render previously marked `unknown_image`.

**`doc_set` table:** DEFERRED to Phase 3.5. Reasoning: "references-as-data primitives" is concept work, not schema work. Without sketches of (entry shape, what entries point at, how created, versioning) Joseph hasn't authored, a v0.2 attempt at the schema would be guessing. F12 reference resolution rides on existing canonical-doc structure (free-text in NOTES.md / docs/) for v0.1 of F12; doc_set ships when reference-resolution friction surfaces.

---

## High-level failure-mode outline (v0.2; behavior detail at code time)

Per Phase 2 §1 pattern. v0.2 lists categories; Wave 1 code adds behavior detail.

**F5 hero promotion failure modes:**
- 5.1 Render file missing at promotion time
- 5.2 Hero `winners/` directory doesn't exist for that section (auto-create with explicit confirmation)
- 5.3 NOTES.md update prompt fires but F6 isn't ready (graceful degradation: surface as "needs follow-up" without blocking promotion)
- 5.4 Doc-update coordination fails mid-loop (per-doc retry queue parallel to api_calls retry pattern)
- 5.5 Un-hero (reverse promotion) per channel staple #12 — `_DEPRECATED_<reason>` directory + reason-required validation (Joseph confirms reason in modal)

**F6 NOTES.md authorship failure modes:**
- 6.1 Claude API rate limit (mirrors 3a.1 — uses retry queue)
- 6.2 Claude API auth error (mirrors 3a.2 — surface modal)
- 6.3 Claude API timeout (mirrors 3a.4 v0.4 amendment — single 60s auto-retry then manual)
- 6.4 Hallucinated NOTES.md content (Joseph review catches; never auto-commits to canonical)
- 6.5 Template version mismatch with discipline_version
- 6.6 Template body too long (Anthropic context window check; truncate prior_notes_md if needed)

**F7 cross-AI capture failure modes:**
- 7.1 Compressed-input + AI-expansion: Claude API down → manual capture fallback (form lets Joseph paste both Joseph-input + AI-expansion manually)
- 7.2 Source attribution missing — required field; form refuses submit
- 7.3 Relevance binding ambiguous — default to last-touched; editable; surface in capture record
- 7.4 Paired-capture orphan (Joseph-input row exists; AI-expansion row never created or reverse) — UI surfaces orphan list

**F8 serialization failure modes:**
- 8.1 Render not in any concept's section → `scene_id := "unscoped"` (graceful degradation)
- 8.2 OpenMontage `asset_manifest` schema rejects shape — log diff against schema; Joseph reviews
- 8.3 Per-section trigger fires before NOTES.md is actually complete (defensive check on `notes_md_state.last_authored` being recent)
- 8.4 Real assets too large for asset_manifest fields (path length, hash size, etc.) — schema-validate before write

---

## Build sequence (v0.2 revised; code-days vs acceptance-bridge separation)

Per v0.1 review Issue 1: every wave estimate distinguishes "code days" from "acceptance bridge time." Acceptance bridges run parallel with code days; total wall-clock is `max(code, bridge)` not `code + bridge`.

### Wave 1 — Substrate + F5 atomic action (5-7 code days)

**v0.2 explicit sequencing (per v0.1 review item 8c — resolves dependency cycle):**
- **Day 1:** Read OpenMontage schemas; draft F8 adapter mapping doc (no F8 code yet — surfaces blockers early per Revision 1).
- **Day 1-2:** Migration 0004 (notes_md_state + cross_ai_captures expansion + idx_verdicts_flagged + unknown_image_terminal value). All additive; no temp-table-and-copy.
- **Day 2-3:** F6 NOTES.md authorship Claude API integration (uses existing llm.py). Endpoint + business logic, NOT YET wired to F5.
- **Day 4-5:** F5 hero-promotion atomic action (depends on F6 prompt-scaffold being ready from step above). Endpoint + audit viewer button + confirmation modal (per Q1 v0.2 settled).
- **Day 5-7:** Audit viewer extension wiring F5 button + F6 NOTES.md update prompt. Includes confirmation-modal UI per v0.2 Q1 settle.

### Wave 2 — F6 acceptance bridge (~1-2 weeks Joseph parallel; ~3-5 hours Claude)

**Code days:** ~0 (F6 code shipped Wave 1).

**Claude work:** ~3-5 hours scaffold ~10 NOTES.md template seeds at `tool_build/seeds/notes_md_template_<section>_v1_0_seed.md`. Each seed:
- Pulls section-specific structure from existing canonical content (`HANDOFF_2026-05-02.md`, `EP1_STRUCTURAL_ARCHITECTURE`, `render_craft_exemplars/`, current section's `NOTES.md` if exists).
- Carries placeholder body marked TODO for Joseph to fill in.
- Includes `template_version: "1.0"` + `authored_against_discipline_version: "1.0"` front-matter.

**Joseph editorial:** ~1-2 weeks (5-15 hours actual + 2-3 iteration cycles). Front-loaded by starting during Phase 2 acceptance bridge (in parallel with rubric authoring).

### Wave 3 — F7 cross-AI capture (4-6 code days)

**Day 1: F7 UX validation against real capture session** (per v0.1 review Issue 2). Joseph runs an actual cross-AI capture session using the v0.1 form; Claude observes friction; iterate form before locking. Prevents "ship form → discover Joseph routes around it" trap that Phase 1 originally hit with M3.

**Day 2-6:** Form scaffold + endpoint + M3 compressed-input + AI-expansion prompt design + pair-tracking + source attribution + relevance binding logic. Substantial work on the M3 novel pattern.

**Day 6:** Bank: which form fields stayed; which iterated; capture surface decisions for Phase 3.5+ refinement.

### Wave 4 — F8 OpenMontage serialization (3-5 code days; asset_manifest only per v0.2 scope)

Wave 4 picks up F8 schema-read draft from Wave 1 Day 1 + adapter mapping doc.

- **Day 1:** Per-section trigger via NOTES.md-complete event (detects `notes_md_state.last_authored` recency; surfaces "section X ready to serialize" action).
- **Day 2-3:** Serialization JSON output. scene_id derived via `concept.section` join; `'unscoped'` fallback for unbound renders.
- **Day 3-4:** Joseph review surface (serialized JSON visible before handoff to OpenMontage compose).
- **Day 4-5:** Edge cases (renders with prompt but no concept; renders with no prompt; renders too large for schema fields).

### Wave 5 — Phase 3 close + acceptance bridge (1-2 code days; F8 acceptance bridge ~1-3 days Joseph parallel)

**Code days:**
- F5/F6/F7/F8 e2e plans documented.
- Discipline-drift query surface extension if needed (per v0.2 open question added).
- Phase 3 close-out doc (analog Phase 2 v0.5 close).

**Acceptance bridge:**
- F6: NOTES.md template authoring complete → real F6 e2e run.
- F8: OpenMontage compose-stage reactivation + real-asset test pipeline + real serialization run end-to-end.
- Bank both results in `banked_items.md`.

### Total Phase 3 estimate

**Code days: 13-19 days** (Wave 1 5-7 + Wave 3 4-6 + Wave 4 3-5 + Wave 5 1-2; Wave 2 has ~0 code days). Add ~3-5 days slack for cross-Claude review rounds (3-4 rounds × ~1 day amend each per v0.1 review Issue 3) → **17-24 days code total**.

**Acceptance bridge time: ~1.5-2.5 weeks** (Joseph editorial F6 templates + F8 compose-stage testing; parallel with code).

**Total time-to-Phase-3-acceptance: 4-6 weeks calendar** (parallel paths). Spec said 2-3 weeks; signal 1's ~50% undercut pattern holds; v0.2's revised range matches honest empirical estimate.

---

## Phase 3 prerequisites

| Prereq | Status |
|---|---|
| Phase 2 v0.6 must-fix amendments | ✅ all landed (commit `f10b2b6`) |
| Phase 2 acceptance bridges (rubric authored + one real Wave B firing + result banked) | ⏳ |
| Cross-Claude review wave on v0.1 SCAFFOLD | ✅ landed (this v0.2 folds findings) |
| Phase 3 v0.2 design notes settled | ✅ this commit |
| F6 user-prerequisite identified upfront (signal 5) | ✅ named (~1-2 weeks Joseph editorial; option (a) accepted) |
| F8 user-prerequisite identified upfront (signal 5) | ✅ named (~1-3 days OpenMontage compose-stage reactivation + real-asset test) |
| OpenMontage `schemas/artifacts/edit_decisions.schema.json` + `asset_manifest.schema.json` read | ✅ read in v0.1 review wave; findings A-E folded into v0.2 |
| Migration 0004 schema decisions settled | ✅ this v0.2 (atomicity per-table; doc_set deferred; scene_id derived not stored) |
| F8 scope decision settled | ✅ asset_manifest only; edit_decisions deferred to OpenMontage edit agent |
| F5 ↔ audit viewer composition decision (Q1) | ✅ in audit viewer with confirmation modal per v0.2 |
| Optional v0.3 cross-Claude review wave on v0.2 | ⏳ (recommended after Phase 2 acceptance bridges to fold real-world data) |

---

## Open questions (v0.2 surfaced + carryovers)

1. **NOTES.md template scope per section.** Each section gets its own template, or shared per concept-type? Settle Wave 2 Day 1 when scaffolds are authored — initial pattern is per-section since EP1's section-level structure is canonical.
2. **Cross-AI capture relevance binding default refinement.** Q4 v0.2 said "last-touched finding/decision." v0.1 review Issue 2 added: validate against real capture session Day 1 of Wave 3. Default may shift after validation.
3. **F8 trigger granularity.** Per-section (Q6 v0.2 confirmation) — but "NOTES.md complete" means `notes_md_state.last_authored` recency? Or Joseph explicitly clicks done? Settle Wave 4 Day 1 with the "last_authored vs explicit_marked_done" decision.
4. **`unknown_image_terminal` post-Phase-3 trigger.** When does walker mark a render `unknown_image_terminal`? After filepath-heuristics pass exhausts? After explicit Joseph "give up on this one" action? Settle Wave 1 Day 2 schema work.
5. **Discipline-version drift extension for F6/F8** *(v0.2 added per v0.1 review item 8a)*. Does `discipline_drift` query show per-template-version drift? Does serialization output include `discipline_version` metadata? When `discipline_version` bumps (1.0 → 1.1), do existing templates auto-flag stale? Settle Wave 4 Day 3 when Joseph review surface design firms up.
6. **Multi-AI batch consultation trigger** *(deferred per Phase 2 4.12)*. Phase 3 trigger to ship: 3+ providers exist + bulk consultation requested. v0.2 names trigger; doesn't add unless trigger fires.
7. **renderer_family question (banked Phase-3.5+)**. OpenMontage asset_manifest has renderer_family at proposal stage. tool_build doesn't capture this. Defer until F8 actually fires; revisit if OpenMontage's edit agent surfaces "what renderer to use" as tool_build's responsibility.

---

## Document maintenance

- **v0.1 SCAFFOLD (2026-05-07):** initial draft at Phase 2 close. Five banked Phase-3-estimating signals applied to draft estimate (~3 weeks median). Phase 2 acceptance bridge gate explicitly named. Migration 0004 schema sketch (named, not specified). High-level failure-mode outline. 5-wave build sequence sketch. Detailed schema + failure-mode + JSON-shape work deferred to v0.2.
- **v0.2 (2026-05-07):** cross-Claude review wave on v0.1 SCAFFOLD folded in. **Five must-fix amendments landed:** (1) scene_id mapping decision (derived at serialization, NOT a stored column — no Migration 0004 schema change for it; concept.section join with 'unscoped' fallback for unbound renders); (2) F8 scope reduced to asset_manifest only (edit_decisions deferred to OpenMontage edit agent per AD-2 boundary); (3) F5 + F7 reclassified from substrate-on-substrate to partially-novel (estimate adjustment +~3-4 days total); (4) F6 acceptance bridge magnitude sharpened to ~1-2 weeks Joseph editorial work (per Joseph's Q1 v0.2 pick (a)); (5) Phase 2 acceptance bridge gate expanded with explicit Phase 2 v0.6 must-fix amendments checklist. **Eight nice-to-haves landed:** code-days vs acceptance-bridge separation in wave estimates; Wave 1 explicit sequencing (Migration 0004 → F6 code → F5 atomic); discipline-drift extension Q added to open-questions list; Migration 0004 atomicity per-table notes; cross_ai_captures 7-column expansion sketched; F8 schema-read pulled forward to Wave 1 Day 1 (Revision 1); F7 UX validation day Wave 3 Day 1 (Issue 2); `unknown_image_terminal` decided as `renders.tool` taxonomy extension. **Three reorderings applied:** F8 schema-read forward (Revision 1); F5 partially-novel (Revision 2); F7 partially-novel (Revision 3). **One Q1 settled:** F5 hero-promotion lives in audit viewer (single button + confirmation modal next to verdict marking). **Phase 3 estimate revised:** 17-24 code days + 1.5-2.5 weeks acceptance bridge in parallel = 4-6 weeks calendar. **Banked-as-Phase-3.5+:** doc_set schema (defer until F12 reference-resolution friction surfaces); renderer_family question; cross-Claude review overhead (~10-15 hours absorbed across phase); multi-AI batch consultation trigger. **Optional v0.3 review wave** (recommended after Phase 2 acceptance bridges land so real-world data informs).
