# Phase 3 — End-to-end test plan

**Purpose.** Phase 3 acceptance is green against synthetic seeded
graphs (`tests/test_*.py` for whatever lands in Wave 1-5 code).
That tells us nothing about whether the system actually behaves
under your hands with a real F5 hero promotion + F6 NOTES.md
authorship via Claude API + F7 cross-AI capture + F8 OpenMontage
serialization flowing through the full audit-viewer + handoff
pipeline. This plan is the smallest test that exercises every
real-world path Phase 3 promises to support.

**Outcome.** A single section (likely h3_skinner since it's the
canonical SHIPPED reference for production-state pattern) audited
end-to-end through the full Phase 3 flow: hero promotion atomic
action committing canonical file moves, NOTES.md authored via
Claude API + Joseph review, cross-AI capture against a real
external-AI question, asset_manifest JSON serialized to
OpenMontage's pipeline-project directory, with F8 acceptance
criterion verified against an actual OpenMontage compose-stage run.

**Time budget.** ~3-4 hours active Joseph time + 1-3 days
OpenMontage compose-stage reactivation work (signal 5 acceptance
bridge cost — pre-named per `phase3_design_notes.md` v0.2 §"Phase 3
prerequisites"). Plus Joseph's 1-2 weeks of NOTES.md template
authoring (front-loadable during Phase 2 acceptance bridge).

**Cost.** Wave A path: $0 (no AI calls; just F5 atomic action).
F6 NOTES.md per-section: ~$0.05-0.20 per template draft (Claude API
text consultation; ~10 sections = $0.50-$2.00 cumulative).
F7 compressed-input + AI-expansion: ~$0.05 per expansion (text-only;
no vision).
F8 OpenMontage compose-stage: depends on render cost (Remotion local
render or cloud render).

---

## Pre-flight

| Check | Command | Pass condition |
|---|---|---|
| Phase 2 acceptance bridges crossed | check `banked_items.md` for "Phase 2 e2e run YYYY-MM-DD" entry | banked entry present |
| Server is running | `python tool_build/serve.py --status` | reports `running on port 7890` |
| Schema is at head (0004) | `python tool_build/serve.py --migrate-schema` | reports `migrate verified`; schema_version = '0004' |
| Migration 0004 applied | `sqlite3 _data/state.db "SELECT name FROM sqlite_master WHERE type='table' AND name='notes_md_state'"` | returns row |
| Rubric authored | `ls projects/latent_systems/docs/AUDIT_RUBRICS_v*.md` | at least one match |
| Rubric parses | `python -c "from rubric import load_active_rubric; import db; r = load_active_rubric(db.REPO_ROOT); print('OK' if r and r['criteria'] else 'EMPTY')"` | prints `OK` |
| ≥1 NOTES.md template authored | `ls projects/latent_systems/ep1/h3_skinner/NOTES.md` (or whichever section you'll use) | exists |
| API key present | `python -c "import os, dotenv; dotenv.load_dotenv('.env'); print('OK' if os.environ.get('ANTHROPIC_API_KEY') else 'MISSING')"` | prints `OK` |
| Browser ready | open `http://localhost:7890/audit/grid?tool=midjourney&only_unverdicted=1` | grid renders |
| OpenMontage pipeline-project root | `ls OpenMontage/pipelines/latent_systems/` (or your chosen path per F8 adapter mapping §"open architectural questions") | directory exists |

**If any check fails, stop and fix before continuing.** Phase 3
acceptance bridges are larger than Phase 2's; can't recover
gracefully from missing prerequisites mid-run.

---

## Step 1 — Verify Migration 0004 schema integrity

Walker had a chance to populate `notes_md_state` during `--init`
(per `MIGRATION_0004_DRAFT.md` open question 5 settled to
piggyback on `--init`).

```bash
sqlite3 projects/latent_systems/tool_build/_data/state.db \
  "SELECT section, template_version, last_authored FROM notes_md_state \
   ORDER BY section LIMIT 20"
```

**Pass conditions:**
- Rows present for the 10 narrative-bearing sections (cold_open, h1-h9 per Migration 0004 §1 Step 1 seed-at-migration-time recommendation)
- Section you authored a template for shows `last_authored` non-NULL
- Section you haven't authored shows `last_authored = NULL`

This validates F6 schema substrate before F6 endpoint testing.

---

## Step 2 — Mark verdict + run consultation (Phase 2 carryover regression check)

Open `http://localhost:7890/audit/grid?tool=midjourney&only_unverdicted=1`.
Click into a render (use one from h3_skinner if you can — it's the
canonical SHIPPED section so production-state context is rich).

In serial view:
1. Press `2` (mark `strong`).
2. Press `C` (consult AI).
3. Wait for consultation card (10-30s; counter ticks per v0.6
   amendment).
4. Verify result card renders; `verdict_inference` color-coded;
   `criteria_match` populated; cost displayed.

**Pass conditions:**
- Verdict captured (filesystem write per F8 4.9 — verify via
  `_data/verdicts/<id>.yaml`)
- Consultation card persists on reload (Phase 2.5 enhancement)
- Migration 0004 didn't regress Phase 2 audit consultation flow

This is the regression check for Wave 1's Migration 0004 against
existing Phase 2 functionality.

---

## Step 3 — F5 hero promotion atomic action

In serial view of the render you just verdicted:
1. Click "Promote to hero" (button next to verdict marking per
   v0.2 Q1 settle).
2. Confirmation modal opens; review file-move target +
   hero_promotions row + NOTES.md update prompt.
3. Confirm.

**Pass conditions:**
- Render file copies to `projects/latent_systems/ep1/<section>/winners/`
  with proper naming (existing mechanic preserved per Phase 1)
- `hero_promotions` row inserted; `verdict_id` linked
- F6 NOTES.md update prompt fires (defers to Step 4 actual authoring)
- Doc-update coordination summary surfaces in modal review (which
  docs would need updating per F9 calibration)

**Verify F5 atomic-transaction integrity:**
```bash
sqlite3 _data/state.db \
  "SELECT id, render_id, hero_filepath, created FROM hero_promotions \
   WHERE render_id = ?"
```
Row exists; hero_filepath is canonical winners/ path; created is
recent.

---

## Step 4 — F6 NOTES.md authorship via Claude API

In the audit viewer, locate the F6 surface (audit-viewer extension
or dedicated `/audit/notes-md/<section>` page per Wave 1 Day 4-5
implementation decision).

For section h3_skinner (or whatever you used in Step 2-3):
1. Click "Update NOTES.md".
2. Form opens with current NOTES.md content + AI draft button.
3. Click "Generate AI draft".
4. Wait for Claude API response (~5-15s text-only).
5. Review draft; edit as needed; click Save.

**Pass conditions:**
- Draft text generated using `(concept, hero_renders, prior_notes_md,
  current_template_version, project_context, tool_grammar_config)`
  per spec
- Joseph review surface lets you edit before commit
- Save writes to `projects/latent_systems/ep1/<section>/NOTES.md` AND
  updates `notes_md_state.last_authored` + `last_modified_filepath`
- `notes_md_state.last_authored_by = 'claude_assisted'` (vs `human`
  for direct edits)
- `discipline_version` matches `authored_against_discipline_version`
  on the notes_md_state row

**Verify cost-tracking:**
```bash
curl -s http://localhost:7890/api_status | python -c "
import json, sys
d = json.load(sys.stdin)
recent = [r for r in d.get('recent', []) if r.get('purpose') == 'notes_md_authorship']
print(f'F6 calls today: {len(recent)}, total cost: \${sum(r[\"cost_usd\"] for r in recent):.4f}')
"
```

**F6 acceptance bridge note (signal 5):** this step assumes the
NOTES.md template for the section exists with structure Joseph
authored. If the template hasn't been authored yet, F6 falls back
to "no prior_notes_md" mode and produces a thinner draft. Banked
in `phase3_design_notes.md` v0.2 §"F6 acceptance bridge magnitude."

---

## Step 5 — F7 cross-AI capture

Open F7 capture surface (audit viewer extension or dedicated
`/capture` page per Wave 3 implementation decision).

Two flows to test:

**5a. Manual capture (paste verbatim).** Joseph pastes a Perplexity
or ChatGPT response from the channel-architecture decision space
(real captured exchange, not synthetic). Form fields:
- source: select Perplexity / ChatGPT / Grok / Gemini / parallel-Claude
- source_identifier: chat URL or descriptive name
- question_asked: Joseph's question
- answer_received: external AI's response
- relevance_binding: defaults to last-touched (per Q4 v0.2)
- relevance_binding_id: editable; defaults filled

Click Capture.

**Pass conditions:**
- `cross_ai_captures` row inserted with all 7 expansion columns
  populated (per Migration 0004 Step 2)
- YAML file at `_data/cross_ai_captures/<id>.yaml`
- relevance_binding shows up in queries by relevance_binding_id

**5b. Compressed-input + AI-expansion (M3 pattern — novel).**
Joseph pastes a compressed answer ("Daniel could carry it tonally"
type fragment). Click "Expand via Claude".
- Claude API expands using project context per M3 prompt structure
- Result shows: Joseph's compressed input + Claude's expansion
- Both saved as paired records (cross_ai_captures.paired_capture_id
  self-FK)

**Pass conditions:**
- Two `cross_ai_captures` rows: one with original_input_text +
  expansion_text NULL (Joseph's input), one with expansion_text
  populated + paired_capture_id linking back
- M3 prompt structure produces useful expansion (not generic
  Claude rephrasing)
- Cost tracked via `consultation_cost_usd` column

**F7 UX validation Day 1 of Wave 3 banking:** if form friction
surfaces during Step 5a or 5b (fields awkward, defaults wrong,
flow confusing), bank specifics for Wave 3 Day 1 iteration per
v0.2 review Issue 2.

---

## Step 6 — F8 serialization to OpenMontage

In F6 surface, mark section h3_skinner's NOTES.md as "complete"
(explicit user click per Q3 v0.2 Wave 4 Day 1 settle, OR
last_authored recency triggers if that's how Q3 settled).

F8 trigger fires; "Section h3_skinner ready to serialize"
notification appears.

Click "Generate asset_manifest". F8 endpoint produces JSON output.

**Pass conditions:**
- JSON output parsed cleanly against
  `OpenMontage/schemas/artifacts/asset_manifest.schema.json`
- Required fields populated per F8 adapter mapping doc:
  - `version: "1.0"`
  - `assets[]` array with one entry per render in section
  - Each asset: `id`, `type`, `path`, `source_tool`, `scene_id`
- `scene_id` derived from `concept.section` (= "h3_skinner") per
  v0.2 amendment; `'unscoped'` fallback for unbound renders
- `quality_score` populated for renders with non-superseded
  verdicts (per F8 adapter mapping H mapping table)
- `total_cost_usd` summed across asset costs
- `metadata.per_asset[<asset_id>]` carries tool_build-specific
  audit-trail data (verdict reasoning, lineage edges,
  ai_consultation_ids per F8 adapter mapping Finding G)

**Joseph review surface:**
- JSON visible before handoff to OpenMontage compose
- Edit / re-trigger options if shape needs adjustment
- "Hand off to OpenMontage" button initiates step 7

---

## Step 7 — F8 OpenMontage compose-stage handoff (acceptance bridge per signal 5)

This is the F8 acceptance bridge step (~1-3 days Joseph time
banked in v0.2). Hands off the asset_manifest JSON to OpenMontage's
pipeline-project + edit agent + compose stage.

**Pre-step:** OpenMontage's pipeline must be reactivated. Per
project memory, Joseph has stashed OpenMontage Remotion work; this
step requires bringing the compose pipeline back online for
real-asset testing.

Manual flow:
1. Copy serialized `asset_manifest.json` to
   `OpenMontage/pipelines/latent_systems/<episode>/asset_manifest.json`
2. Verify renders exist at the paths listed in the manifest
   (relative to pipeline project root per F8 Finding J).
3. Run OpenMontage edit agent against this asset_manifest to
   produce `edit_decisions.json`.
4. Run OpenMontage compose stage against both files.
5. Output: rendered video file confirming end-to-end serialization
   works.

**Pass conditions:**
- OpenMontage edit agent accepts asset_manifest without schema
  errors
- edit_decisions produced (timing, transitions, layer assignments)
- Compose stage renders without missing-asset errors
- Output video plays cleanly; section content represents the
  audited renders

**Failure modes worth banking (per AUDIT_PATTERNS Pattern #8 —
project-content surface):**
- 8.1 — scene_id mapping mismatch: OpenMontage expects scenes to
  be a known finite set; `'unscoped'` fallback may not be
  recognized. Bank as F8 follow-up if surfaces.
- 8.2 — path translation issue: F8 wrote pipeline-project-relative
  paths but Joseph's pipeline-project-root differs from F8's
  default. Bank in PHASE_3 banking section.
- 8.3 — Remotion composition expectations: edit agent's output
  may require additional composition context tool_build doesn't
  capture (renderer_family from v0.1 review Finding D). Bank
  + flag for Phase 3.5+.

---

## Step 8 — Discipline-drift extension (per v0.2 open question 5)

Verify F6 / F8 interactions with discipline_version tracking work.

```bash
curl -s http://localhost:7890/discipline_drift | python -m json.tool
```

**Pass conditions:**
- F6 NOTES.md authored at template_version 1.0 appears in totals
  (likely as discipline_version = 1.0 grouping)
- F8 serialization output's metadata block surfaces in drift query
  if cross-cut
- F7 captures' discipline_version groups correctly
- No regression on Phase 1 + Phase 2 drift query behavior

This validates that Phase 3 features didn't break Feature 9.

---

## Step 9 — Verdict supersession + F5 un-promotion paths

Two reverse-flow tests:

**9a. Verdict supersession.** In serial view of the render
verdicted in Step 2, mark a different verdict with
`supersedes_verdict_id: <prior>` body parameter.

```bash
PRIOR_VID="<prior verdict_id from step 2>"
curl -X POST http://localhost:7890/audit/render/<rid>/verdict \
  -H "Content-Type: application/json" \
  -d "{\"verdict\":\"weak\",\"verdict_reasoning\":\"on closer inspection apparatus geometry occluded\",\"supersedes_verdict_id\":\"$PRIOR_VID\"}"
```

**Pass conditions:** new verdict; old preserved as audit-trail; only
new verdict surfaces as `current` in get_render_detail (per Phase 2
v0.2 supersession query layer).

**9b. F5 un-promotion (per channel staple #12).** From audit viewer
hero-promotion surface, click "Un-promote" on a hero render. Modal
prompts for reason (REQUIRED per F9 calibration; refuses to
proceed without). Confirm.

**Pass conditions:**
- File moves from `winners/` to `_work/<context>/_DEPRECATED_<reason>/`
- Reason field captured in `hero_promotions.reversed_reason`
- `reversed_at` timestamp set
- Updated NOTES.md prompt fires (F6 update for un-promotion event)

This validates the F5 reverse-flow per channel staple #12.

---

## Step 10 — F8 re-serialization after supersession

Per v0.2 §F8 open architectural question 5: re-serialization is
explicit-trigger, not automatic. Verify that's the actual behavior.

After Step 9a (verdict superseded):
1. Open the section's F8 surface
2. Should see "section X has updated verdicts; regenerate
   manifest?" prompt
3. Click regenerate
4. New asset_manifest.json reflects the superseded verdict
   (`quality_score` updated to match new verdict)
5. Old asset_manifest.json archived (or overwritten — settled
   Wave 4 implementation)

**Pass conditions:**
- Trigger surfaces correctly
- Regenerated JSON has new quality_score values
- Audit-trail preserved (old manifest accessible somehow)

---

## What this catches that synthetic tests can't

| Failure mode | Synthetic test | E2E plan |
|---|---|---|
| Real F5 atomic transaction across file-move + db row + NOTES.md prompt | not exercised | exercised |
| Real F6 Claude API draft quality against actual project context | mocked | real |
| Real F7 M3 compressed-input + AI-expansion against actual Joseph compressed inputs | mocked | real |
| Real F8 OpenMontage schema validation against actual edit agent | not exercised | exercised |
| Real OpenMontage compose-stage rendering against asset_manifest | not exercised | exercised |
| Real path translation between tool_build repo-relative + OpenMontage pipeline-project-relative | not exercised | exercised |
| Real Migration 0004 schema integrity against existing Phase 2 data | partial | full |
| Real NOTES.md authoring time / quality / iteration cycle (signal 5) | not exercised | exercised (1-2 weeks Joseph time) |
| Real F8 acceptance bridge OpenMontage compose reactivation | not exercised | exercised |

If any step above fails in a way the synthetic tests didn't catch,
that failure mode goes into `AUDIT_PATTERNS.md` as a new rule (per
the "every operational task is also a spec audit pass" banking
principle from Phase 1).

---

## Banking after the run

Whether the run passes or finds bugs, write a multi-section result
in `banked_items.md` under "Phase 3 e2e run YYYY-MM-DD" heading:

**Per-feature acceptance:**
- F5: passed / partial / failed; specific atomic-action behavior
  observed; un-promotion reverse path verified.
- F6: NOTES.md authored for section X; template version 1.0 stuck;
  cumulative Joseph editorial time across all sections.
- F7: capture surface UX friction summary; M3 expansion quality
  verdict (useful vs generic); pair-tracking integrity.
- F8: asset_manifest JSON validated against schema; OpenMontage
  edit agent + compose stage produced output video; F8 compose-
  stage reactivation cost (Joseph hours).

**Cumulative metrics:**
- Total wall-clock time (active Joseph + waiting + iteration cycles)
- Total cost (Claude API for F6 + F7; OpenMontage compose if cloud)
- Bug-count surfaced (and whether patched same-session or banked)

**Acceptance verdict:**
- Phase 3 acceptance-validated: Y/N
- If N: which specific paths still need work to bridge from
  "code-shipped" to "acceptance-validated"
- If Y: Phase 4 design notes can start

**Decision-bank for Phase 4:**
- Five Phase-3-estimating signals re-applied to Phase 4 estimate
- New signals surfaced from Phase 3 run (signal 6+)
- Cumulative-effort calibration: Phase 3 actual code days vs
  v0.2 estimate (17-24); Phase 3 acceptance bridge actual time
  vs estimate (1.5-2.5 weeks); compression vs estimate-undercut
  ratio for Phase 4 input

---

## Document maintenance

- **v1.0 (2026-05-07):** initial Phase 3 e2e plan. 10-step real-API
  run analog to Phase 1.5 + Phase 2 plans. Pre-flight specifies
  Phase 2 acceptance-bridge gate + rubric + ≥1 NOTES.md template
  + Migration 0004 applied. Steps 1-3 verify schema + Phase 2
  regression; Steps 4-7 exercise F5/F6/F7/F8 forward paths;
  Steps 8-10 exercise discipline-drift extension + supersession
  + F8 re-serialization. "What this catches" table mirrors prior
  plans. Banking section specifies per-feature acceptance + cumulative
  metrics + Phase 4 input. Lives at `tool_build/PHASE_3_E2E_PLAN.md`
  (sibling to Phase 1.5 + Phase 2 plans). Implementation transcribes
  from this when Wave 1-5 code lands.
