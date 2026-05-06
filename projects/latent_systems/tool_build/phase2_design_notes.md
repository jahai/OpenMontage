# LATENT SYSTEMS — Tool-build Phase 2 Design Notes

**Date:** 2026-05-06
**Status:** v0.1 DRAFT — initial Phase 2 substrate authored at Phase 2 kickoff
**Source material:** v1 Spec Proposal v0.5 (`tool_build/v1_spec_proposal.md` Phase 2 paragraph), Phase 1 Design Notes v0.4 (`tool_build/phase1_design_notes.md`), banked items (`tool_build/banked_items.md`), Phase 1.5 e2e debrief (banked_items §"Phase 1.5 e2e run — 2026-05-05"), Day 16 cross-Claude review (in-session)
**Purpose:** Detailed design specifications that must be settled before Phase 2 code begins. Mirrors phase1_design_notes structure: failure modes, schema, schemas, lifecycle, build sequence, open questions.

---

## Document scope

The v1 spec proposal commits Phase 2 to addressing F7, F8, F9: audit viewer, multi-AI evaluation flow, verdict capture, hero promotion with doc-update coordination, tool-grammar config expansion to GPT Image 2 + Kling + ElevenLabs, and 3a failure-mode handling hardened. The spec does not specify: vision-API failure-mode behavior, verdict + AI-consultation schema details, rubric loading mechanics, image viewer technical approach, build sequence relative to the 84%-unknown_image data-quality issue surfaced during Phase 1 walker development.

This doc fills those gaps for Phase 2 specifically. Phase 3 design notes will be written when that phase is imminent. This is not a complete Phase 2 design doc — it is the minimum design substrate Phase 2 build needs, plus explicit punts on items that would benefit from one cross-Claude review wave before settling.

If a question in this doc is deferred ("Phase 2 won't decide this; build will"), that's an explicit punt with rationale. If a question seems missing entirely, flag it for v0.2 of this doc.

---

## 1. Failure-mode specifications for Feature 4 (audit viewer + AI-assisted evaluation)

The v1 spec named audit viewer functionality at a high level (project-aware viewer with prompt + lineage + AI consultation). This section specifies Phase 2 behavior for each failure mode that was not pre-specified.

### 4.1 Render file missing (canonical path moved/deleted)

Behavior:
- Audit viewer queries `renders` table for `filepath`; tries to load image bytes.
- If file not found: render row stays in db, but UI shows "render file missing — last seen at <path> on <created_ts>" with three actions: "mark as moved" (prompts for new path; updates row), "mark as deleted" (sets `renders.status = 'deleted'`; excludes from default views), "investigate" (no row change; opens file-explorer at expected path).
- Discipline rule: **render rows are NOT auto-deleted** when file is missing. The audit log of "this render existed and got verdict X" is durable even if file is later moved.

### 4.2 Vision API rate limit (HTTP 429 from Anthropic vision endpoint)

Behavior:
- Per Phase 1 §1 / 3a.1, but with vision-specific cost weight.
- Audit viewer shows "consultation queued — retrying in Ns" badge.
- Vision API costs are the dominant Phase 1.5 e2e cost driver (~$0.30/call placeholder per spec Cost section; 10x text-API). Surface running consultation cost prominently in UI to prevent runaway.
- After 3 consecutive 429s on same render, stop auto-retry; offer "manual retry" or "skip this render."

### 4.3 Vision API auth error

Same as 3a.2: blocking modal, no retry, surface credential-setup link. Distinguished from text-API auth (different env var key per provider).

### 4.4 Vision API timeout

Per Phase 1 §1 / 3a.4 (v0.4 amendment): single auto-retry after 60s; if retry also times out, mark consultation `failed`; UI offers manual retry. Verdict can still be captured manually; AI consultation is optional, not required.

### 4.5 Vision API hallucinated structured response

Behavior:
- Claude vision API is asked for structured response (verdict + reasoning + criteria-match per rubric). If response doesn't parse: log raw response in `verdict.ai_consultations[].raw_response`, mark consultation `parse_failed`, surface raw text in UI. Joseph can read the raw text + manually capture key points.
- Phase 2 ships parse-tolerant — strict JSON validation rejects valid responses too aggressively. Best-effort extraction with fallback to raw display.

### 4.6 Multi-AI consultation partial completion

Behavior:
- Multi-AI flow: Perplexity, ChatGPT, Grok, Gemini consulted (in sequence; per-provider configurable via `audit_rubrics_config.yaml`).
- If one provider fails (timeout, auth, quota): record `verdict.ai_consultations[].status = 'failed'` with reason; continue with remaining providers; UI shows "3 of 4 consultations completed" status badge.
- Joseph can mark verdict with partial consultations. Verdict object stores which providers responded and which didn't.

### 4.7 Rubric file missing or malformed

Behavior:
- Audit viewer reads `docs/AUDIT_RUBRICS_v*.md` at session start (versioned per Q5; latest version becomes active rubric).
- If file missing: surface blocking error "no rubric available — create `docs/AUDIT_RUBRICS_v1_0.md` first." App still works for non-AI verdict capture (Joseph can mark hero/strong/weak/reject without rubric); just no AI consultation.
- If malformed (parse error): surface error with line number; refuse to use partial rubric (would mislead AI consultations); fall back to non-AI mode.
- Rubric file lives in `docs/` per Q5 — read-only to v1 per AD-5.

### 4.8 Image-too-large for vision API payload

Behavior:
- Anthropic vision API has size limits (~5MB per image, base64-encoded). Some MJ outputs at upscale resolutions can exceed.
- Pre-check image size; if over limit: downscale to fit (keep aspect; max edge 1568px per Anthropic docs); cache downscaled copy at `_data/_audit_thumbnails/<render_id>.jpg`; send downscale.
- Verdict object records `consultation_used_downscale: true` so audit trail is honest.

### 4.9 Verdict marked but write-fail (filesystem error)

Behavior:
- Verdict capture writes filesystem-instantly per spec ("no save button"). If write fails (disk full, permissions, etc.): surface non-blocking toast; queue verdict in memory; retry on next user action; if still failing after 3 retries, surface blocking modal.
- Discipline: **never lose a verdict to UI race**. Verdicts are the audit trail; their loss is more costly than UI friction.

### General principle

**Vision API costs are the dominant Phase 2 cost driver.** Every consultation visible in UI with running-total. If batch cost crosses a configurable threshold (default $1.00), pause and prompt for confirmation (existing OpenMontage budget governance pattern).

---

## 2. State.db schema additions for Phase 2 (Migration 0003)

Per AD-5: state.db is cache, not source of truth. Additions:

```sql
-- Migration 0003: extend verdicts for AI consultation; add audit-rubric tracking
ALTER TABLE verdicts ADD COLUMN ai_consultations TEXT;  -- JSON array of consultation records
ALTER TABLE verdicts ADD COLUMN consultation_cost_usd REAL DEFAULT 0;
ALTER TABLE verdicts ADD COLUMN audit_session_id TEXT;  -- groups verdicts marked in same session

-- Track audit sessions for batch view + cost rollups
CREATE TABLE audit_sessions (
    id TEXT PRIMARY KEY,
    started TEXT NOT NULL,
    ended TEXT,
    rubric_version TEXT NOT NULL,
    discipline_version TEXT NOT NULL,
    total_consultations INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0,
    notes TEXT
);
CREATE INDEX idx_audit_sessions_started ON audit_sessions(started);
CREATE INDEX idx_audit_sessions_rubric ON audit_sessions(rubric_version);

-- Audit thumbnails cache (small downscaled copies for vision API + UI grid view)
CREATE TABLE audit_thumbnails (
    render_id TEXT PRIMARY KEY,
    thumbnail_path TEXT NOT NULL,
    source_hash TEXT NOT NULL,  -- canonical_hash at time of generation; invalidate if changed
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    bytes INTEGER NOT NULL,
    created TEXT NOT NULL,
    FOREIGN KEY(render_id) REFERENCES renders(id)
);
```

### Schema migration: Alembic 0003

Alembic version `0003_audit_consultation`. App refuses to start if version mismatch detected without `--migrate-schema` flag (per Phase 1 pattern). Update `SUPPORTED_SCHEMA_VERSIONS` in `constants.py` to `frozenset({"0001", "0002", "0003"})`.

### Regen-from-filesystem path

If state.db corrupts: existing regen logic walks YAMLs at `_data/<artifact_type>/`. New for Phase 2: walks `_data/verdicts/*.yaml` and `_data/audit_sessions/*.yaml` to repopulate. Audit thumbnails are cache-only and regenerable from canonical render files.

### What state.db does NOT do for Phase 2

- Full AI consultation prompts/responses live in YAML, not state.db. Cache stores summary (provider, status, cost, ts) for fast queries; full text requires reading the YAML.
- Rubric content lives in `docs/AUDIT_RUBRICS_v*.md`, not state.db. Cache stores `rubric_version` in `audit_sessions` for join queries; full rubric text comes from filesystem read.

---

## 3. Verdict object + AI consultation schema

### Verdict YAML format (`_data/verdicts/<id>.yaml`)

```yaml
id: <16-char hex>
render_id: <render_id>
discipline_version: "1.0"

verdict: hero_zone | strong | weak | reject  # required
verdict_reasoning: |
  <Joseph's free-text rationale; can be empty for quick-pass verdicts>

rubric_version: <e.g., "1.0">
rubric_criteria_match:  # optional; populated by AI consultation OR Joseph's structured rating
  composition: pass | fail | partial | not_evaluated
  register_coherence: pass | fail | partial | not_evaluated
  apparatus_fidelity: pass | fail | partial | not_evaluated
  # additional criteria per concept-type rubric

audit_session_id: <id>  # links to audit_sessions row
mode: quick_pass | deep_eval

ai_consultations:  # zero or more
  - provider: anthropic-claude-vision | perplexity | chatgpt | grok | gemini
    model: <e.g., "claude-opus-4-7">
    consulted_at: <iso>
    status: completed | partial | failed | parse_failed
    cost_usd: 0.30
    consultation_used_downscale: true | false
    raw_response: |
      <verbatim API response text>
    parsed:  # nullable if parse_failed
      verdict_inference: hero_zone | strong | weak | reject
      criteria_match: { composition: pass, ... }
      key_observations: ["...", "..."]
    failure_reason: <iff status != completed>

audited_by: human | claude_assisted | multi_ai_assisted
created: <iso>
```

### AI consultation API call shape

For Anthropic vision specifically (Phase 2 baseline):
- System prompt: rubric criteria for the concept-type + audit-mode instructions
- User message: render image (downscaled if needed) + concept context + lineage chain + rubric questions
- Response shape: structured JSON with `verdict_inference`, `criteria_match`, `key_observations`. Parse-tolerant per failure mode 4.5.

For other providers (Perplexity, ChatGPT, Grok, Gemini): per-provider adapters in `tool_build/audit_providers/<provider>.py`; same call shape exposed; per-provider failure-mode handling encapsulated. Phase 2 ships Anthropic baseline; other providers added iteratively as needed.

### Multi-AI attribution discipline

Each consultation records:
- `provider` (which AI)
- `model` (which version of that AI's model)
- `consulted_at` (timestamp for review trail)
- `status` (so partial-completion is visible)

This satisfies F11a/M1 (cross-AI attribution as durable artifact) and F8 (audit verdicts with multi-AI consultation logged).

---

## 4. Audit rubric loading

Per Q5: rubrics live at `docs/AUDIT_RUBRICS_v*.md` (read-only to v1 per AD-5).

### File format

Markdown with YAML front-matter:

```markdown
---
version: "1.0"
discipline_version: "1.0"
applies_to_concept_types: [schematic_apparatus, cinematic_atmospheric, ...]
---

# Audit Rubric v1.0

## Common criteria (all concept types)

### Composition
[criteria description]
- pass: [definition]
- partial: [definition]
- fail: [definition]

### Register coherence
[...]

## Per concept-type criteria

### schematic_apparatus

#### Apparatus fidelity
[...]
```

### Loading mechanism

- Audit viewer reads latest `docs/AUDIT_RUBRICS_v*.md` (highest version) on session start.
- Parses YAML front-matter for version + applicable concept types.
- Parses markdown body for criteria definitions; passes structured form to vision API.
- Caches in `audit_sessions.rubric_version` for the session; does not re-read mid-session unless Joseph explicitly switches rubrics.

### Versioning + drift handling

When rubric bumps to `1.1`:
- New verdicts written against `1.1` get `rubric_version: "1.1"`.
- Old verdicts at `1.0` still queryable via `discipline_drift` surface (cross-artifact F10 query).
- Rubric upgrades are NEVER retroactive (per F10 design principle); old verdicts stay at their rubric.

### Phase 2 prerequisite (NOT Phase 1)

`docs/AUDIT_RUBRICS_v1_0.md` must exist before audit viewer ships. Authoring the rubric is **Joseph's work, not Claude's** — the rubric is project-vocabulary-specific and reflects the project's earned discipline (per F10). Phase 2 includes a placeholder + sample rubric structure; Joseph writes the real one.

---

## 5. Image viewer technical approach

### Stack (Phase 1 pattern)

- Backend: FastAPI endpoints (already in `app.py`).
- Frontend: HTMX + minimal JS in `templates/index.html` (Phase 1 baseline).
- Image serving: FastAPI `FileResponse` for canonical files; thumbnail cache served from `_data/_audit_thumbnails/`.

### Endpoints (Phase 2 additions to app.py)

- `GET /audit/sessions` — list active and completed sessions.
- `POST /audit/sessions` — start new session (returns `session_id`, takes optional `concept_id` filter).
- `GET /audit/render/{render_id}` — render detail view (image + concept + lineage + verdict if exists).
- `GET /audit/queue?session_id=...&filter=...` — return ordered list of renders to audit.
- `POST /audit/render/{render_id}/verdict` — capture verdict (instant write).
- `POST /audit/render/{render_id}/consult?providers=...` — invoke multi-AI consultation.
- `GET /audit/cost?session_id=...` — running cost for active session.

### Serial view (default)

- Single render at a time, full-size in viewport.
- Prev / Next navigation (keyboard: `←` / `→`).
- Quick-mark keys: `1` = hero_zone, `2` = strong, `3` = weak, `4` = reject (configurable in user prefs Phase 3).
- Sidebar: concept context, prompt, lineage chain, AI consultation panel (collapsible).

### Grid view (4×5)

- 20 renders per page; thumbnail-only with per-render verdict badge if marked.
- Click → opens serial view at that render.
- Bulk-action: select N renders → invoke "AI consultation on selection" → batch consultation request.
- Use `audit_thumbnails` table to avoid regenerating thumbnails per page-load.

### Quick-pass vs deep-eval mode toggle

- Mode-toggle button in header; defaults to last-used mode per session.
- Quick-pass: keyboard-driven, sidebar collapsed, AI consultation deferred to deep-eval.
- Deep-eval: full sidebar visible, AI consultation panel pre-loaded with last consultation if any.

### Performance budget

- Render detail view loads in <500ms (image lazy-loads; sidebar pre-fetched).
- Grid view paginated 20-per-page; thumbnails pre-generated for visible page only.
- Multi-AI consultation: completes in <30s for 4 providers (parallel calls; longest-tail dominates).

---

## 6. Phase 2 build sequence + the audit-viewer-first vs banked-flush-first decision

This is the open sequencing question raised at Phase 2 kickoff. Two positions emerged:

### Position A: Audit viewer first (Joseph's earlier preference, per spec ordering)

Spec Phase 2 paragraph orders audit viewer first. Building it first makes the audit phase project-aware — the highest-leverage F8 fix per the audit findings.

**Risks:** building viewer on top of dirty data (84% of pre_v1 renders classified as `unknown_image` per banked_items §"Phase 2 confirmed"; 21 `_unclassified/` GPT renders with no section attribution). First user experience: open viewer, see "84% of my renders have unknown tool" status. Devalues the deliverable.

### Position B: Banked-flush first, then audit viewer (Day 16 cross-Claude reviewer's recommendation)

Quick-win mechanical work to clean data before viewer ships:

1. **`tools/router_log.md` cross-reference** for tool attribution recovery on the 1698 pre_v1 renders. The router log has tool attribution at routing time; current walker classifies post-routing where tool info is lost. Cross-referencing recovers ~84% of the unknown_image classifications. Estimated 1 day.
2. **21 `_unclassified/` GPT renders triage** to specific Phase 1 directions. Mechanical: read each, assign section/concept by inspection. Estimated half-day.

Then audit viewer ships on clean data. First user experience: open viewer, see well-attributed render set with sensible filtering by section + tool.

**Risks:** delays audit viewer ship by 1.5 days; data-quality work is "polish" relative to F4 capability.

### Recommendation: Position B (banked-flush first)

Reasoning:

1. **Audit viewer's value is data visibility.** A viewer over data with 84% unknown tool attribution shows the audit-of-the-data, not the audit-of-the-renders. The viewer is supposed to surface render-level signal; data-quality issues drown that signal.
2. **The flush is mechanical and deterministic.** Both items (router_log cross-reference, _unclassified triage) are well-scoped, low-risk, no design ambiguity. The work doesn't need design-notes; just execution.
3. **Audit viewer benefits compound.** Every subsequent Phase 2/3 feature (verdict capture, hero promotion, multi-AI consultation) builds on the audit viewer. Shipping the viewer on clean data means downstream features inherit clean data; shipping it dirty means every downstream feature fights the same `unknown_image` tax.
4. **1.5 days is small in Phase 2's 2-3 week budget.** The trade-off is favorable.

If Joseph picks Position A despite this, the design notes still cover audit viewer first; the data-quality work shifts to Phase 2 Week 2 instead of Week 1.

### Proposed Phase 2 build sequence (assumes Position B)

**Week 1: Banked-item flush (data-quality prerequisites for audit viewer).**
- Day 1: `tools/router_log.md` cross-reference logic in walker. Re-walk pre_v1 renders; ~84% should resolve to specific tool attribution.
- Day 2: 21 `_unclassified/` GPT renders triage. Inspect each; assign section + concept. Update YAMLs.
- Day 3: Verify data quality post-flush. Run discipline_drift + render-by-tool queries. Confirm `unknown_image` rate drops below 10%.

**Week 2-3: Audit viewer (Feature 4 + AI-assisted evaluation).**
- Migration 0003: schema additions (verdicts AI columns, audit_sessions, audit_thumbnails).
- Endpoints + serial view.
- Verdict capture (instant write).
- Anthropic vision API integration (single-AI baseline).
- Audit rubric loader.
- Image-too-large downscale logic.

**Week 3-4: Audit viewer hardening + multi-AI flow.**
- Grid view (4×5).
- Quick-pass vs deep-eval mode toggle.
- Multi-AI consultation (Perplexity / ChatGPT / Grok / Gemini adapters).
- Cost rollups + budget threshold.
- Phase 2 acceptance test against success criterion 5 (F8 verdict durability).

**Week 4-5 (slack budget):** Hero promotion (F5) atomic action. If Phase 2 timeline runs long, Hero promotion can slip to Phase 2.5 / early Phase 3.

**Phase 2 acceptance test:** mark a render hero_zone with multi-AI consultation captured; close session; reopen day later; verdict + consultations + reasoning all recoverable; F8 success criterion verified.

### Items deferred from Phase 2 spec to Phase 3 (revisit at Phase 2 close)

- **Hero promotion (F5) atomic action** — spec puts in Phase 2; banked_items.md "Phase 3 territory" had it. Recommend keeping in Phase 2 as Week 4-5 stretch goal; if Week 1 banked-flush extends, slip to Phase 3 Week 1.
- **Tool-grammar config expansion to GPT Image 2 + Kling + ElevenLabs** — spec puts in Phase 2; depends on Phase 1 usage data. Phase 2 ships with Anthropic vision config only; expansion to image/video/voice tool-grammar happens when Phase 1 prompt-drafting flow generates enough successful_examples to seed the configs (per Q3).
- **3a hardening** — spec puts in Phase 2. Already largely landed via v0.4 amendment + retry queue work in Phase 1 Day 12. Phase 2 review at Week 4 to confirm no remaining gaps.

---

## 7. Open questions for Phase 2 build

Phase 2 design notes punt the following to be answered during build:

1. **Multi-AI provider adapters: in-tree or library?** Phase 1 keeps llm.py Anthropic-specific. Phase 2 needs Perplexity / ChatGPT / Grok / Gemini. Two paths: (a) per-provider adapters at `tool_build/audit_providers/`, each minimal SDK wrapper. (b) Use a library like `litellm` to abstract providers. Default: **(a) per-provider** for control + cost-tracking integration. Library introduces transitive dependencies and obscures cost reporting.

2. **Vision API thumbnail caching strategy.** Cache hit when `audit_thumbnails.source_hash == renders.canonical_hash`. Cache miss: regenerate. Question: on rubric/concept change, do we invalidate thumbnails? Default: **no** — thumbnails are about image data, not metadata. Rubric/concept changes don't invalidate.

3. **Audit session boundary semantics.** When does a session start/end? Default: **explicit start via `POST /audit/sessions`; explicit end OR auto-end after 4h idle**. Cost rollups depend on session boundaries; auto-end prevents indefinite "this session" cost accumulation.

4. **Multi-AI consultation: parallel or sequential?** Parallel = fastest (longest-tail wins). Sequential = lets Joseph see partial results faster (Perplexity returns at 3s, shows that first; ChatGPT returns at 12s, appended). Default: **parallel; UI streams results as they arrive** via Server-Sent Events. Sequential is fallback if SSE adds complexity.

5. **Deep-eval vs quick-pass mode persistence.** Per-session, per-user, or per-concept-type default? Default: **per-session toggle, defaulting to last-used mode**. Per-concept-type defaults can be Phase 3 polish.

**Note:** rubric authoring is Joseph's work, not Claude's. Phase 2 ships with a sample rubric structure + parser; Joseph writes the real `docs/AUDIT_RUBRICS_v1_0.md` before Phase 2 acceptance.

---

## 8. Phase 2 prerequisites (must land before Day 1)

- **Joseph confirms Position A or B** (build sequence section 6). Default proposal is Position B; if Joseph picks A, sequence shifts.
- **`docs/AUDIT_RUBRICS_v1_0.md` authored** — Joseph's work; not Claude's. Without it, audit viewer ships in non-AI mode only.
- **Cross-Claude review of this design notes v0.1** — same review pattern as Phase 1 (v0.1 → v0.2 with reviewer wave → v0.3 settling). Phase 2 build does not start before v0.2+ exists.
- **Phase 2 effort re-estimate after design-notes review.** v1 spec estimated Phase 2 at 2-3 weeks; reviewer may sharpen given current sequencing decision and the data-quality flush insertion.

---

## Document maintenance

- **v0.1 (2026-05-06):** initial draft authored at Phase 2 kickoff. Eight sections specifying Phase 2 build prerequisites: F4 failure modes (4.1-4.9 incl. vision-specific failure modes 4.5-4.8), state.db Migration 0003 schema, verdict + AI consultation schema, audit rubric loading mechanics, image viewer technical approach (HTMX-based, serial + grid + mode-toggle), Phase 2 build sequence with explicit audit-viewer-first vs banked-flush-first decision (recommends Position B), open questions deferred to build. Ready for cross-Claude review wave before Phase 2 Day 1.
