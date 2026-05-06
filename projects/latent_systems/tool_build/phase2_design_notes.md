# LATENT SYSTEMS — Tool-build Phase 2 Design Notes

**Date:** 2026-05-06
**Status:** v0.3 DRAFT — Phase 2 Day 1 spec/reality finding folded in (router_log cross-reference ineffective; recovery mechanism revised to filename-pattern extension + frame_extract tool category)
**Source material:** v1 Spec Proposal v0.5 (`tool_build/v1_spec_proposal.md` Phase 2 paragraph), Phase 1 Design Notes v0.4 (`tool_build/phase1_design_notes.md`), banked items (`tool_build/banked_items.md`), Phase 1.5 e2e debrief (banked_items §"Phase 1.5 e2e run — 2026-05-05"), Day 16 cross-Claude review (in-session), v0.2 cross-Claude review wave 2026-05-06 (8 pressure-tests + 7 issues + ranked v0.2 amendments list), Phase 2 Day 1 spec-audit finding 2026-05-06 (banked-flush mechanism revision).
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

### 4.10 Vision API safety filter rejection (v0.2 — added per review)

Anthropic vision API can refuse images for content-policy reasons. Real risk for this project specifically: H#3 reenactment imagery (rat/human collapsed prone), later episodes' subject matter (addiction, manipulation patterns) will hit safety filters with non-zero probability.

Behavior:
- API returns parseable response, but the body contains a refusal pattern ("I can't", "I cannot", "for safety reasons") near the start rather than a structured verdict.
- Distinguished from 4.5 parse_failed (response parses fine; semantically refuses).
- Detection: response-text pattern-match for refusal phrases at the start of the response body.
- Mark consultation `status='safety_refused'`; preserve raw response in `raw_response`; surface to Joseph as "AI declined to evaluate (safety filter); manual verdict only."
- Do NOT auto-retry — safety refusals are deterministic for given image+prompt content; retries waste cost.
- Verdict can still be captured manually; consultation is optional, not required.

### 4.11 Context window exceeded (v0.2 — added per review)

Long lineage chains + rubric criteria + concept text + image base64 can exceed Claude vision API's context window. Already a real risk for thesis_image work where lineage chains run 10+ entries.

Behavior:
- Pre-check token count before sending (Anthropic's `count_tokens` API).
- If projected request exceeds 80% of context window: truncate concept-context lineage to most-recent N entries.
- Insert explicit `<lineage truncated; N-of-M most-recent entries shown>` marker so the AI's response can acknowledge the truncation.
- Preserve full pre-truncation request in `raw_response` so audit trail shows what was actually sent.
- If the rubric+image alone exceeds context (no lineage to truncate): mark consultation `status='context_exceeded'`; offer Joseph the option to consult against a degraded rubric (criteria subset).

### 4.12 Multi-image batch consultation (deferred to Phase 3)

The grid view (§5) might invite "consult on selected 4-image batch" — single API call evaluating multiple renders against same criteria. Phase 2 explicitly does NOT ship this. Single-image consultation only. If batch-consultation friction surfaces during Phase 2 use, promote in Phase 3 with its own failure-mode design (per-image partial completion, comparative reasoning across batch, etc.).

Banking this deferral explicitly prevents scope creep during Phase 2 build.

### General principle

**Vision API costs are the dominant Phase 2 cost driver.** Every consultation visible in UI with running-total. If batch cost crosses a configurable threshold (default $1.00), pause and prompt for confirmation (existing OpenMontage budget governance pattern).

---

## 2. State.db schema additions for Phase 2 (Migration 0003)

Per AD-5: state.db is cache, not source of truth.

**v0.2 revision per cross-Claude review:** v0.1 stored `ai_consultations` as a JSON column on `verdicts` for convenience. Reviewer surfaced three concrete query patterns Phase 2 needs (verdicts-by-provider-failure, cost-rollup-by-provider, all-failed-consultations) where JSON-in-SQLite is awkward, unindexed, and slow at scale. Splitting to a separate table now is cheap; Migration 0004 to split it later is expensive. v0.2 lands ai_consultations as a first-class table with FK to verdicts.

**Also v0.2 per review:** verdicts gets FK on audit_session_id (SQLite ALTER TABLE can't add FK to existing table → temp-table-and-copy pattern), audit_sessions gets scope columns + mode column, verdicts gets supersedes_verdict_id (speculative-but-cheap, follows lineage_edges temporal-dimension precedent).

```sql
-- Migration 0003: audit consultation as first-class table; FK enforcement;
-- audit-session scope tracking; verdict re-audit semantics.

-- Step 1: rebuild verdicts with FK on audit_session_id + new columns.
-- (SQLite ALTER TABLE can't add FK to existing tables, so temp-table-and-copy.)
CREATE TABLE verdicts_new (
    id TEXT PRIMARY KEY,
    render_id TEXT NOT NULL,
    rubric_used TEXT,
    rubric_version TEXT,
    verdict TEXT NOT NULL,
    audited_by TEXT,
    audit_session_id TEXT,
    consultation_cost_usd REAL DEFAULT 0,
    flags_needs_second_look INTEGER DEFAULT 0,  -- boolean stored as 0/1 per SQLite convention
    supersedes_verdict_id TEXT,
    discipline_version TEXT NOT NULL,
    yaml_path TEXT NOT NULL,
    created TEXT NOT NULL,
    FOREIGN KEY(render_id) REFERENCES renders(id),
    FOREIGN KEY(audit_session_id) REFERENCES audit_sessions(id),
    FOREIGN KEY(supersedes_verdict_id) REFERENCES verdicts(id)
);
INSERT INTO verdicts_new (id, render_id, rubric_used, verdict, audited_by, discipline_version, yaml_path, created)
SELECT id, render_id, rubric_used, verdict, audited_by, discipline_version, yaml_path, created
FROM verdicts;
DROP TABLE verdicts;
ALTER TABLE verdicts_new RENAME TO verdicts;
CREATE INDEX idx_verdicts_render_id ON verdicts(render_id);
CREATE INDEX idx_verdicts_verdict ON verdicts(verdict);
CREATE INDEX idx_verdicts_audit_session ON verdicts(audit_session_id);
CREATE INDEX idx_verdicts_flags ON verdicts(flags_needs_second_look) WHERE flags_needs_second_look = 1;
CREATE INDEX idx_verdicts_supersedes ON verdicts(supersedes_verdict_id) WHERE supersedes_verdict_id IS NOT NULL;

-- Step 2: audit_sessions with scope + mode (groups verdicts marked in same session).
CREATE TABLE audit_sessions (
    id TEXT PRIMARY KEY,
    started TEXT NOT NULL,
    ended TEXT,
    rubric_version TEXT NOT NULL,
    discipline_version TEXT NOT NULL,
    mode TEXT DEFAULT 'quick_pass',           -- quick_pass | deep_eval; per Q5 storage decision
    scope_concept_id TEXT,                    -- if session filtered to one concept
    scope_section TEXT,                       -- if session filtered to a section
    scope_filter_json TEXT,                   -- additional filter criteria (status, register, etc.)
    total_consultations INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0,
    notes TEXT
);
CREATE INDEX idx_audit_sessions_started ON audit_sessions(started);
CREATE INDEX idx_audit_sessions_rubric ON audit_sessions(rubric_version);
CREATE INDEX idx_audit_sessions_concept ON audit_sessions(scope_concept_id) WHERE scope_concept_id IS NOT NULL;

-- Step 3: ai_consultations as first-class table, FK to verdicts.
-- Replaces v0.1's JSON column on verdicts. Indexed for analytical queries
-- (cost-rollups by provider, all consultations with status=failed, etc.).
CREATE TABLE ai_consultations (
    id TEXT PRIMARY KEY,
    verdict_id TEXT NOT NULL,
    provider TEXT NOT NULL,                   -- anthropic-claude-vision | perplexity | chatgpt | grok | gemini
    model TEXT,                               -- e.g., "claude-opus-4-7"
    consulted_at TEXT NOT NULL,
    status TEXT NOT NULL,                     -- completed | partial | failed | parse_failed | safety_refused | context_exceeded
    cost_usd REAL DEFAULT 0,
    used_downscale INTEGER DEFAULT 0,         -- 0/1 boolean (per 4.8 image-too-large)
    raw_response TEXT,                        -- verbatim API response
    parsed_json TEXT,                         -- structured parse, if status in (completed, partial)
    failure_reason TEXT,                      -- iff status not in (completed, partial)
    yaml_path TEXT,                           -- consultation YAML at _data/ai_consultations/<id>.yaml
    FOREIGN KEY(verdict_id) REFERENCES verdicts(id)
);
CREATE INDEX idx_ai_consultations_verdict_id ON ai_consultations(verdict_id);
CREATE INDEX idx_ai_consultations_provider ON ai_consultations(provider);
CREATE INDEX idx_ai_consultations_status ON ai_consultations(status);
CREATE INDEX idx_ai_consultations_consulted_at ON ai_consultations(consulted_at);

-- Step 4: audit thumbnails cache (small downscaled copies for vision API + UI grid view).
CREATE TABLE audit_thumbnails (
    render_id TEXT PRIMARY KEY,
    thumbnail_path TEXT NOT NULL,
    source_hash TEXT NOT NULL,                -- canonical_hash at time of generation; invalidate if changed
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    bytes INTEGER NOT NULL,
    created TEXT NOT NULL,
    FOREIGN KEY(render_id) REFERENCES renders(id)
);
```

### Schema migration: Alembic 0003

Alembic version `0003_audit_consultation`. App refuses to start if version mismatch detected without `--migrate-schema` flag (per Phase 1 pattern). Update `SUPPORTED_SCHEMA_VERSIONS` in `constants.py` to `frozenset({"0001", "0002", "0003"})`.

`_CASCADE_DELETE_ORDER` in `db.py` extends to walk the new tables child-first: `ai_consultations` (child of verdicts) before verdicts; verdict supersession edges sweep via `WHERE id LIKE ? OR supersedes_verdict_id LIKE ?` — the AUDIT_PATTERNS Pattern #2 mechanic stays uniform.

### Regen-from-filesystem path

If state.db corrupts: existing regen logic walks YAMLs at `_data/<artifact_type>/`. New for Phase 2: walks `_data/verdicts/*.yaml`, `_data/ai_consultations/*.yaml`, and `_data/audit_sessions/*.yaml` to repopulate. Audit thumbnails are cache-only and regenerable from canonical render files.

### What state.db does NOT do for Phase 2

- Full AI consultation raw_response/parsed_json text lives in YAML at `_data/ai_consultations/<id>.yaml`. State.db `raw_response` and `parsed_json` columns store reference text for indexed queries; the YAML is source of truth for unbounded prose.
- Rubric content lives in `docs/AUDIT_RUBRICS_v*.md`, not state.db. Cache stores `rubric_version` in `audit_sessions` for join queries; full rubric text comes from filesystem read.

---

## 3. Verdict object + AI consultation schema

**v0.2 revision:** AI consultations move from a JSON array on verdict YAML to separate consultation YAMLs at `_data/ai_consultations/<id>.yaml`, each linked back to a verdict via `verdict_id`. Verdict YAML carries only the verdict commitment; consultation records are first-class. Schema-mirror of §2 Migration 0003 split decision. Verdict gets `flags.needs_second_look` (minimal scope per Q3 call) and `supersedes_verdict_id` (per Q2 call).

### Verdict YAML format (`_data/verdicts/<id>.yaml`)

```yaml
id: <16-char hex>
render_id: <render_id>
discipline_version: "1.0"

verdict: hero_zone | strong | weak | reject  # required, commits Joseph
verdict_reasoning: |
  <Joseph's free-text rationale; can be empty for quick-pass verdicts.
   If a rubric question surfaces ("the rubric needs updating to handle
   X"), use a "[RUBRIC]" prefix tag here — pattern-recognition during
   audit pass without a dedicated field. If this prefix shows up across
   two separate audit sessions, promote to a structured flag in
   Phase 2.5 / Phase 3.>

rubric_version: <e.g., "1.0">
rubric_criteria_match:  # optional; populated by AI consultation OR Joseph's structured rating
  composition: pass | fail | partial | not_evaluated
  register_coherence: pass | fail | partial | not_evaluated
  apparatus_fidelity: pass | fail | partial | not_evaluated
  # additional criteria per concept-type rubric

audit_session_id: <id>  # links to audit_sessions row

flags:
  needs_second_look: false  # boolean; default false. Surfaces in
                            # "flagged for second look" view; clearable
                            # in follow-up audit pass without changing
                            # the verdict itself. Minimal scope per
                            # v0.2 Q3 call: handles the most-frequent
                            # informal pattern (REVISIT in reasoning)
                            # without forcing Joseph to choose between
                            # two text fields per verdict.

# Re-audit semantics (per v0.2 Q2 call). NULL until rubric bumps to 1.1
# and re-audits begin. Speculative-but-cheap addition following
# lineage_edges temporal-dimension precedent. Default queries return
# non-superseded verdicts; full history queryable for audit-trail.
supersedes_verdict_id: null  # or <verdict_id> when this verdict supersedes a prior one

# AI consultations no longer inline; reference IDs only. Full records
# live in ai_consultations table + _data/ai_consultations/*.yaml.
ai_consultation_ids: []  # list of ai_consultations.id values

audited_by: human | claude_assisted | multi_ai_assisted
created: <iso>
```

### AI consultation YAML format (`_data/ai_consultations/<id>.yaml`)

```yaml
id: <16-char hex>
verdict_id: <verdict_id>
discipline_version: "1.0"

provider: anthropic-claude-vision | perplexity | chatgpt | gemini
model: <e.g., "claude-opus-4-7">
consulted_at: <iso>

status: completed | partial | failed | parse_failed | safety_refused | context_exceeded
cost_usd: 0.30
used_downscale: true | false  # per 4.8 image-too-large

raw_response: |
  <verbatim API response text — full prose; uncapped length>

parsed:  # nullable if status in (failed, parse_failed, safety_refused, context_exceeded)
  verdict_inference: hero_zone | strong | weak | reject
  criteria_match:
    composition: pass | fail | partial | not_evaluated
    register_coherence: pass | fail | partial | not_evaluated
    # ... per rubric
  key_observations:
    - "..."
    - "..."

failure_reason: <iff status not in (completed, partial)>
truncated_lineage: <iff context-handling per 4.11 invoked: count of trimmed lineage entries>
```

### AI consultation API call shape

For Anthropic vision (Phase 2 baseline):
- System prompt: rubric criteria for the concept-type + audit-mode instructions
- User message: render image (downscaled per 4.8 if needed) + concept context + lineage chain (truncated per 4.11 if needed) + rubric questions
- Response shape: structured JSON with `verdict_inference`, `criteria_match`, `key_observations`. Parse-tolerant per 4.5.
- Pre-flight: token-count check per 4.11 to avoid context-window failure.

For other providers (Perplexity, ChatGPT, Gemini): per-provider adapters in `tool_build/audit_providers/<provider>.py`; same call shape exposed; per-provider failure-mode handling encapsulated.

### Per-provider role-mapping (v0.2 — added per review)

Per the project briefing's role calibration, each AI plays a distinct audit role. v0.2 honest framing of which providers actually ship vs aspirational:

| Provider | Audit role | Phase 2 status |
|---|---|---|
| Anthropic vision (claude-opus-4-7) | Primary verdict consultation; rubric-aligned structural read | Baseline; ships Day 1 of Wave B |
| Perplexity | External resistance / cross-check against Anthropic's read | Phase 2 Week 2 if confirmed during testing |
| ChatGPT | Adversarial structural editor (NOT execution authorship) | Phase 3 if confirmed need |
| Grok | Low-trust until proves it can follow briefing | Deferred indefinitely |
| Gemini | Coordinator / Google-ecosystem; production tooling | Phase 3 if confirmed need |

Phase 2 ships Anthropic-only as Wave B baseline. Perplexity adapter is the next-most-likely addition; built only after Joseph confirms during testing that Perplexity adds signal beyond Claude's read. ChatGPT/Gemini deferred to Phase 3 absent confirmed need. Grok deferred indefinitely per role calibration.

This is honest about what the project actually does vs spec aspiration. Avoids shipping 4 unproven adapters; builds evidence first.

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

### Parser contract (v0.2 — added per review)

The format choice (markdown body + YAML front-matter) is right: human-friendly authoring + structured metadata. The risk is parser brittleness — if Joseph writes a heading differently in v1.1 (`### Composition` → `## Composition`), the parser breaks silently. v0.2 makes the parser contract explicit so Joseph has a target to write against.

**The parser extracts:**
- YAML front-matter as structured metadata (`version`, `discipline_version`, `applies_to_concept_types`).
- Markdown headings at H3 level (`###`) as criteria names.
- Body text under each H3 (until next H3 or end-of-document) as criteria definition.
- Bullet points under H3 prefixed with `pass:`, `partial:`, `fail:` (case-insensitive) as evaluation guidance.

**Parser handling:**
- **Malformed YAML front-matter:** refuse to load; surface error with line number; fall back to non-AI verdict capture per 4.7.
- **Missing H3 headings under per-concept-type sections:** criteria default to `not_evaluated`; AI consultation marks as `criteria_match: not_specified`.
- **Body text without `pass:`/`partial:`/`fail:` bullets:** treat as criteria-without-grading-scale; AI consultation given description but no structured evaluation guidance.
- **Permissive on:** whitespace inside body, casing of `pass:`/`partial:`/`fail:` prefixes, ordering of bullet points within a criterion, additional H4+ subheadings (treated as elaboration of the H3 criterion).
- **Strict on:** H3 as the criterion-level heading anchor (no fallback to H2 or H4); YAML front-matter delimited by `---` lines at file start.

This gives Joseph a defined contract for rubric authoring. Without it, "what counts as malformed" drifts and rubric-version bumps risk silent parser breakage.

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
- `POST /audit/sessions` — start new session (returns `session_id`; takes optional `scope_concept_id`, `scope_section`, `scope_filter_json`, `mode`).
- `GET /audit/render/{render_id}` — render detail view (image + concept + lineage + verdict if exists).
- `GET /audit/queue?session_id=...&filter=...` — return ordered list of renders to audit.
- `POST /audit/render/{render_id}/verdict` — capture verdict (instant write).
- `POST /audit/render/{render_id}/consult?providers=...` — invoke AI consultation (sequential per Q4 default).
- `GET /audit/thumbnail/{render_id}` — serve thumbnail with hash-stable invalidation.
- `GET /audit/cost?session_id=...` — running cost for active session.

### Thumbnail-serve endpoint logic (v0.2 — added per review)

§2 specifies `audit_thumbnails.source_hash` for invalidation, but v0.1's §5 didn't describe the serve-side hash-compare logic. Without specification, an implementer might serve stale thumbnails after canonical regeneration. v0.2 makes the contract explicit:

```python
# Pseudocode for thumbnail-serve endpoint
@app.get("/audit/thumbnail/{render_id}")
def get_thumbnail(render_id: str):
    thumb = db.get_thumbnail(render_id)            # row from audit_thumbnails
    render = db.get_render(render_id)              # row from renders
    if render is None:
        raise HTTPException(404, "render not found")
    if thumb and thumb.source_hash == render.canonical_hash:
        # cache hit: still valid for current canonical
        return FileResponse(thumb.thumbnail_path)
    # cache miss OR stale (canonical regenerated since thumbnail was made)
    new_thumb = generate_thumbnail(render)         # downscale + persist + insert/update row
    return FileResponse(new_thumb.thumbnail_path)
```

Without the `source_hash == canonical_hash` check, the schema's invalidation column is decorative.

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

## 6. Phase 2 build sequence (Position B confirmed; v0.2 two-wave shipping plan)

### Sequencing decision: Position B (banked-flush first, then audit viewer) — confirmed

Joseph confirmed Position B at Phase 2 kickoff. Reasoning preserved here for the design-notes record:

1. **Audit viewer's value is data visibility.** A viewer over data with 84% unknown tool attribution shows the audit-of-the-data, not the audit-of-the-renders. Data-quality issues drown render-level signal.
2. **The flush is mechanical and deterministic.** Both items (router_log cross-reference, `_unclassified/` triage) are well-scoped, low-risk, no design ambiguity. The work doesn't need design-notes; just execution.
3. **Audit viewer benefits compound.** Every downstream Phase 2/3 feature (verdict capture, AI consultation, hero promotion) inherits whatever data quality the viewer ships against. Clean data once vs `unknown_image` tax forever.
4. **The cost is small relative to Phase 2 budget.** Even at the high end of the amended estimate (below), the trade-off is favorable.

**v0.2 amendment per review:** the v0.1 estimate of "1.5 days" for the flush was optimistic. Real coverage of the router_log.md cross-reference is probably 60-75% rather than the 84% the walker initially showed as recoverable — renders predating the router's introduction have no log entries; manually-moved files (camera, screenshot, drag-drop) bypass it; router_log.md is markdown not structured YAML, so first-pass parsing may need a second pass for header/format drift edge cases.

**Amended estimate: 1.5-2.5 days.** Lower bound if recovery lands above 70%; upper bound if structural edge cases surface (router-log format drift, manual-move subset >20%). The 21 `_unclassified/` triage at half-day is mechanical inspection and remains solid.

Position B holds even at the upper bound — going from 84% unknown to ~30% unknown is a major data-quality win even at imperfect recovery, and the compounding-benefit argument is unaffected.

### Proposed Phase 2 build sequence

**v0.3 amendment per Day 1 spec-audit finding (2026-05-06):** the v0.2 plan built Week 1 around `tools/router_log.md` cross-reference. Day 1 inspection of the actual log + actual unknown_image renders showed the mechanism was wrong: router_log.md has only ONE logged run (the entire log is 27 lines), recovering ~0 of the 1434 unknown_image rows. The router itself was added late in the project; almost all pre_v1 renders predate it. Banking this as a fresh example of "spec/reality gaps surface during build" (banked_items.md Banking Principle #4 — every operational task is also a spec audit pass).

The actual recovery mechanism is **filename-pattern extension + new `frame_extract` tool category**. Distribution of the 1434 unknown_image filenames discovered on Day 1:

| Pattern | Count | % of unknowns | Real tool |
|---|---|---|---|
| `frame_NNNN.png` | 734 | 51.2% | frame extract (NEW category) |
| Has `_mj_<hex>_` infix | 92 | 6.4% | midjourney (current MJ_RE missed these) |
| `fNN_NN.png` | 89 | 6.2% | frame extract |
| `phase1_*` prefix | 87 | 6.1% | mostly MJ (filepath heuristic deferred to Phase 3) |
| `h3_` / `H3_` prefix | 55 | 3.8% | mixed; deferred to Phase 3 |
| GPT/DALL-E markers | 29 | 2.0% | gpt_image_2 |
| `t_X.X` / `_final_tX` | 23 | 1.6% | frame extract |
| `shotXseedY` | 16 | 1.1% | flux |
| `flux`/`kontext` markers | 4 | 0.3% | flux |
| **No pattern matches** | **367** | **25.6%** | genuinely opaque (LOCKED/DEPRECATED manually-named files) |

**Realistic recovery target: ~70-75%** via filename-pattern extension alone. Filepath heuristics for `phase1_`/`h3_` prefixes deferred to Phase 3 to keep Day 1-2 scope tight.

**Week 1: Banked-item flush (revised mechanism).**
- Day 1: Extend `walker.classify()` with broader patterns: MJ_INFIX_RE (matches `_mj_<hex>_<variant>.png`), GPT_INFIX_RE (broader gpt/dalle markers), FLUX_RE (flux + kontext), FRAME_RE (4 frame-extract patterns). Add `frame_extract` to tool taxonomy. Reclassify unknown_image rows in state.db + YAMLs via `walker --reclassify-unknowns` CLI.
- Day 2: 21 `_unclassified/` GPT renders triage. Inspect each; assign section + concept. Update YAMLs.
- Day 3 (slack/contingency): Verify recovery rate post-classification. Run discipline_drift + render-by-tool queries. Confirm `unknown_image` rate drops to ~25%. Document residual unknowns for Phase 3 follow-up.

**Tool taxonomy extension (v0.3):** `tool` field gains `frame_extract` and `flux` as values. Existing values (`midjourney`, `gpt_image_2`, `kling`, `video`, `audio`, `unknown_image`, `unknown`) preserved. Audit viewer can filter by tool category — `frame_extract` is intentionally excluded from default "audit-worthy generation outputs" view since frame extracts are derived, not generated.

**Filepath heuristics deferred to Phase 3.** The 367 truly-opaque files plus 142 prefix-only files (`phase1_`, `h3_`) sum to ~509 (~30% of unknowns). Phase 3 can add filepath-context recovery if friction surfaces during audit viewer use ("why are 30% of my renders unattributed?"). Phase 2 banks the residual honestly.

**`tools/router_log.md` cross-reference is NOT abandoned** — it stays as forward-looking infrastructure. Every NEW render routed via the router from now on has tool attribution captured at routing time. The mechanism is correct for new data; just doesn't help with existing pre_v1 backlog.

### Two-wave audit viewer shipping plan (v0.2 — added per review)

The reviewer's pressure on "rubric-authoring as non-blocking" was right: a non-AI-mode audit viewer is useful but degraded. Rather than ship one degraded artifact and patch it later, v0.2 commits to an explicit two-wave plan:

**Wave A — Non-AI audit viewer (Week 2):**
- Migration 0003 lands (schema for verdicts, ai_consultations placeholder, audit_sessions, audit_thumbnails, supersedes_verdict_id, flags.needs_second_look).
- Endpoints: `/audit/sessions`, `/audit/render/{render_id}`, `/audit/queue`, `/audit/render/{render_id}/verdict`, `/audit/thumbnail/{render_id}`, `/audit/cost`.
- Serial view + grid view (4×5).
- Verdict capture (instant filesystem write per 4.9; flags.needs_second_look surfaced; supersedes_verdict_id null until rubric 1.1).
- Quick-pass vs deep-eval mode toggle.
- Image-too-large downscale logic per 4.8.
- **Wave A delivers:** verdict capture + reasoning + serial/grid views + lineage display + flagged-for-second-look view. Replaces ad-hoc Windows Media Player viewing pattern. Satisfies F8 success criterion 5 (verdict durability) even without AI. Joseph uses this immediately while authoring the rubric.

**Wave B — AI consultation layered on top (Week 3-4):**
- Anthropic vision API integration (`tool_build/audit_providers/anthropic.py`).
- `/audit/render/{render_id}/consult` endpoint (sequential per Q4 default).
- Audit rubric loader (per §4 parser contract).
- Failure-mode handling for vision API: 4.1-4.12.
- Cost rollups + budget threshold.
- **Wave A users transparently get AI consultation** when they next open the viewer. Verdicts marked in Wave A stay valid; new verdicts from Week 3 onward gain ai_consultation_ids references.
- Perplexity adapter (`tool_build/audit_providers/perplexity.py`) — only if Joseph confirms during Wave B testing that Perplexity adds signal beyond Claude's read.

This makes "non-AI mode" honest about its value while preventing the rubric from blocking Day 1 work. Joseph can ship Wave A immediately and let Wave B land when the rubric is authored. The two-wave plan also creates a natural rubric-authoring deadline: Wave B can't ship without `docs/AUDIT_RUBRICS_v1_0.md`, but Wave A ships independent of it.

**Phase 2 acceptance test:** mark a render hero_zone in Wave A; close session; reopen day later; verdict + reasoning + flag state recoverable. After Wave B: same render gets AI consultation; consultation record persists in `_data/ai_consultations/`; recoverable independent of session. F8 success criterion verified across both modes.

### Phase 2 effort re-estimate: 4-5 weeks (v0.2 — revised from v1 spec 2-3 weeks)

The v1 spec estimated Phase 2 at 2-3 weeks. v0.2's proposed sequence implies 4-5 weeks. Honest banking of the four expansion drivers:

1. **Multi-AI provider integration overhead** — even with Phase 2 shipping Anthropic-only baseline + conditional Perplexity, the per-provider adapter pattern requires shared abstractions, cost-tracking integration, per-provider failure-mode handling. Real work even at minimal adapter count.
2. **Rubric authoring is Joseph's work** — days of his time, parallelizable but on his calendar, not Claude's. Wave B timeline is partly bounded by rubric availability.
3. **Vision API integration is genuinely new** — cost discipline (per-call running total surfaced in UI), token management (4.11 context-exceeded handling), safety filter handling (4.10), multi-failure-mode coverage (4.5/4.6/4.10/4.11). All Phase 2 firsts.
4. **Position B kickoff overhead + amended estimate** — 1.5-2.5 days of Week 1 banked-flush before viewer work starts.

This expansion follows Phase 1's pattern: spec estimate undercut actual by ~50%. Worth banking for Phase 3 estimating — see Document maintenance section below.

### Items deferred from Phase 2 to Phase 3

**v0.2 amendment per Q1 call (Joseph): Hero promotion (F5) moves from Phase 2 stretch to Phase 3 default.**

F5's "atomic action" promise depends on F6 (NOTES.md authorship) and Phase 3's doc-set data model (per spec):
- Steps 1-2 (copy render to canonical `winners/`; write hero_promotion object) are partially landed in Phase 1 (router copies; `hero_promotions` schema exists).
- Step 3 (trigger NOTES.md update prompt) requires F6 — Phase 3.
- Step 4 (coordinate updates to enumerated docs per F9 calibration) requires the doc-set data model — Phase 3.

If F5 lands in Phase 2 stretch: steps 1-2 ship as a real endpoint; steps 3-4 ship degraded (surfaces "section X needs NOTES.md update" but can't author it; lists docs to update without doing it). Phase 3 then rebuilds steps 3-4 when F6 lands. **Building it twice.**

If F5 moves to Phase 3 default: Phase 2 keeps the manual file-move pattern Joseph uses today (no regression). F5 lands in Phase 3 alongside F6 — atomic action is genuinely atomic, no rebuild.

The reviewer's "scope-tightening" framing was right but for a different reason than they named: not just budget, but avoiding work that has to be redone.

**Pull-forward note:** if Phase 2 lands ahead of schedule (Wave A clean in Week 2; Wave B clean in Week 3), Week 4 has real slack. F5 partial endpoint (steps 1-2 only, with steps 3-4 explicitly stubbed for Phase 3) could pull forward as Phase 2.5 — making the Phase 1 partially-landed pieces a real queryable hero-promotion event without the full atomic action. Pull-forward is opportunity, not obligation.

`banked_items.md` updated in same commit as v0.2: F5 moves from "Phase 2 territory" back to "Phase 3 territory" with the pull-forward annotation.

**Other items deferred from Phase 2 spec to Phase 3:**

- **Tool-grammar config expansion to GPT Image 2 + Kling + ElevenLabs** — depends on Phase 1 successful_examples accumulation. Phase 2 ships Anthropic vision config only; expansion to image/video/voice tool-grammar happens when Phase 1 prompt-drafting flow generates enough successful_examples to seed the configs (per Q3).
- **3a hardening** — largely landed via v0.4 amendment + retry queue work in Phase 1 Day 12. Phase 2 Week 4 review confirms no remaining gaps.
- **ChatGPT, Grok, Gemini provider adapters** — deferred per §3 role-mapping table.
- **Multi-image batch consultation** — deferred per 4.12.
- **SSE for parallel consultation streaming** — deferred per Q4 (sequential is Phase 2 default).
- **Per-concept-type mode defaults** — deferred per Q5 simplification.

---

## 7. Open questions for Phase 2 build

Phase 2 design notes punt the following to be answered during build:

1. **Multi-AI provider adapters: in-tree or library?** Phase 1 keeps llm.py Anthropic-specific. Phase 2 needs Perplexity / ChatGPT / Grok / Gemini. Two paths: (a) per-provider adapters at `tool_build/audit_providers/`, each minimal SDK wrapper. (b) Use a library like `litellm` to abstract providers. Default: **(a) per-provider** for control + cost-tracking integration. Library introduces transitive dependencies and obscures cost reporting.

2. **Vision API thumbnail caching strategy.** Cache hit when `audit_thumbnails.source_hash == renders.canonical_hash`. Cache miss: regenerate. Question: on rubric/concept change, do we invalidate thumbnails? Default: **no** — thumbnails are about image data, not metadata. Rubric/concept changes don't invalidate.

3. **Audit session boundary semantics.** When does a session start/end? Default: **explicit start via `POST /audit/sessions`; explicit end OR auto-end after 4h idle**. Cost rollups depend on session boundaries; auto-end prevents indefinite "this session" cost accumulation.

4. **Multi-AI consultation: parallel or sequential?** v0.2 default per review: **sequential** — call provider, await, render result, repeat. For Phase 2's actual provider count (Anthropic baseline; Perplexity conditional Week 2), sequential keeps complexity low. Total wait at 4 providers @ 5s each = ~20s, acceptable. Parallel + SSE streaming was v0.1's default; reviewer correctly flagged that as design-padding (event-stream backend, EventSource frontend, reconnection handling, partial-event recovery — substantial complexity for unproven value at current provider count). Phase 3 promotes to parallel-with-SSE if the 20s wait surfaces friction.

5. **Deep-eval vs quick-pass mode persistence.** Per-session, per-user, or per-concept-type default? Default per Q5 + reviewer: **per-session, persisted as `audit_sessions.mode` column** (added in Migration 0003 §2). New session reads previous session's mode as default; pure session-state, no separate prefs table. Per-concept-type defaults can be Phase 3 polish.

**Note:** rubric authoring is Joseph's work, not Claude's. Phase 2 ships with a sample rubric structure + parser; Joseph writes the real `docs/AUDIT_RUBRICS_v1_0.md` before Phase 2 acceptance.

---

## 8. Phase 2 prerequisites (must land before Day 1)

| Prereq | v0.1 status | v0.2 status |
|---|---|---|
| Position A vs B sequencing | open | ✅ Position B confirmed |
| Cross-Claude review wave | open | ✅ wave 1 complete (8 pressure-tests + 7 issues + 15 ranked amendments folded into this v0.2) |
| Phase 2 effort re-estimate | open | ✅ 4-5 weeks (revised from 2-3 weeks); 4 drivers banked in §6 |
| `docs/AUDIT_RUBRICS_v1_0.md` authored | open | ⏳ Joseph's work; non-blocking for Wave A; required for Wave B Week 3 |
| Migration 0003 schema landed | open | ⏳ ships Day 1 of Wave A (Week 2) |
| Existing-file 84%-unknown_image flush | open | ⏳ Phase 2 Week 1 (Position B banked-flush) |

**Wave A (non-AI viewer Week 2)** is unblocked once v0.2 commits. **Wave B (AI consultation Week 3-4)** additionally requires Joseph's rubric authoring.

A second cross-Claude review wave on v0.2 is optional rather than required: most reviewer items already folded; the doc is substantially more complete than v0.1 was. If a second wave reveals must-fix items, those land in v0.3 before Wave A starts. Default expectation is v0.2 settles Phase 2 design.

---

## Document maintenance

- **v0.1 (2026-05-06):** initial draft authored at Phase 2 kickoff. Eight sections specifying Phase 2 build prerequisites: F4 failure modes (4.1-4.9 incl. vision-specific failure modes 4.5-4.8), state.db Migration 0003 schema, verdict + AI consultation schema, audit rubric loading mechanics, image viewer technical approach (HTMX-based, serial + grid + mode-toggle), Phase 2 build sequence with explicit audit-viewer-first vs banked-flush-first decision (recommends Position B), open questions deferred to build. Ready for cross-Claude review wave before Phase 2 Day 1.
- **v0.2 (2026-05-06):** cross-Claude review wave folded in. 12 default-accept items + Joseph's three calls (Q1 F5→Phase 3 default with pull-forward note; Q2 supersedes_verdict_id included in Migration 0003 per lineage_edges temporal precedent; Q3 minimal flags scope — needs_second_look bool only). Major changes: §1 adds 4.10 safety_refused / 4.11 context_window_exceeded / 4.12 batch-deferred-to-Phase-3; §2 splits ai_consultations from JSON column to first-class table, adds FK on audit_session_id via temp-table-and-copy, adds scope/mode columns to audit_sessions, adds supersedes_verdict_id to verdicts; §3 restructures verdict YAML around the schema split, adds per-provider role-mapping table (Anthropic baseline / Perplexity Week 2 conditional / ChatGPT+Gemini Phase 3 / Grok deferred); §4 adds explicit parser contract subsection; §5 adds thumbnail-serve invalidation logic; §6 commits Position B 1.5-2.5 days, two-wave shipping plan (Wave A non-AI Week 2, Wave B AI consultation Week 3-4), F5 banked to Phase 3 with pull-forward note, effort re-estimated to 4-5 weeks with 4 drivers; §7 Q4 default flips to sequential consultation (SSE deferred to Phase 3), Q5 specifies storage as audit_sessions.mode column; §8 updates prereq table for v0.2 status. Bundled with banked_items.md correction moving F5 back to Phase 3 territory.
- **v0.3 (2026-05-06):** Phase 2 Day 1 spec-audit finding folded in. v0.2 §6 built Week 1 around `tools/router_log.md` cross-reference; Day 1 inspection found that mechanism is wrong (the log has 1 logged run; near-zero recovery on existing pre_v1 backlog). Real recovery comes from filename-pattern extension + new `frame_extract` tool category (51%+ of unknowns are video frame extracts the Phase 1 walker didn't have a category for). §6 build sequence revised: Day 1 extends `walker.classify()` with broader regexes (MJ_INFIX_RE, GPT_INFIX_RE, FLUX_RE, FRAME_RE) + adds `frame_extract` tool taxonomy value + reclassifies via `walker --reclassify-unknowns`. Recovery target revised from ~84% to ~70-75% (filepath heuristics for prefix-only files like `phase1_`/`h3_` deferred to Phase 3). Bank as fresh example of "spec/reality gaps surface during build" — Banking Principle #4 working as intended.

**Spec-estimate-undercut pattern banked for Phase 3 estimating (v0.2 — added per Joseph):** Phase 1 spec said 2-4 weeks; v0.4 design notes raised to 3-6 weeks; actual was 16 days (with subsequent Day 16-17 cleanups). Phase 2 spec said 2-3 weeks; v0.2 raises to 4-5 weeks (actual TBD). Two data points isn't a settled pattern, but ~50% expansion from spec-optimistic to design-notes-realistic is recurring. When Phase 3 design notes get authored, **start estimating from the realistic baseline (1.5x to 2x spec) rather than re-deriving from spec-optimistic.** The expansion drivers are typically: schema correctness work that surfaces during build, multi-component integration overhead, real-world failure-mode coverage that the spec doesn't anticipate, Joseph-facing work (rubric authoring etc.) that's parallelizable but has its own clock.

**Spec-mechanism-undercut pattern banked (v0.3 — added per Day 1 finding):** distinct from the estimate-undercut pattern: even when an estimate is realistic, the *mechanism* the design assumes can be wrong. v0.2 estimated banked-flush at 1.5-2.5 days assuming router_log cross-reference was the recovery path. The estimate was probably right; the mechanism wasn't. When Phase 3 design notes get authored against existing-data assumptions, **inspect actual data on Day 1 of the relevant phase before committing to a mechanism.** Spec-driven mechanism choices that aren't grounded in inspection of the data they operate on are a recurring failure mode worth one explicit Day-1 audit pass per phase.
