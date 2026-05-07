# LATENT SYSTEMS — Tool-build Phase 3 Design Notes

**Date:** 2026-05-07
**Status:** v0.1 SCAFFOLD — Phase 3 prerequisites + outline + draft estimate banked. Full failure-mode + schema detail deferred to v0.2 (after Phase 2 acceptance bridge crosses + cross-Claude review wave).
**Source material:** v1 Spec Proposal v0.5 (`tool_build/v1_spec_proposal.md`) Phase 3 paragraph; Phase 2 Design Notes v0.6 maintenance log (5 banked Phase-3-estimating signals); `banked_items.md` Phase 3 territory section; F6 / F7 / F8 / F12 / M4 / M5 audit findings.
**Purpose:** Lay v0.1 substrate so the cross-Claude review wave that closes Phase 2 acceptance can pressure-test Phase 3 entry assumptions before code starts.

---

## Document scope

**What v0.1 commits to:**
- Phase 3 features overview (F5 hero promotion + F6 NOTES.md authorship + F7 cross-AI capture + F8 serialization to OpenMontage + Phase 2 carryovers).
- Apply all 5 banked Phase-3-estimating signals to a draft estimate.
- Sketch Migration 0004 schema (notes_md_state, doc_set, cross_ai_captures expansion, lineage_edges layer-3, filepath_heuristics if Phase 2 review-banked unknown_image_terminal status pattern lands).
- High-level failure-mode outline per feature.
- Build sequence sketch (waves).
- Phase 3 prerequisites + open questions.

**What v0.1 explicitly defers to v0.2+:**
- Detailed failure-mode specifications (analog to Phase 2 §1 4.1-4.12).
- Concrete Migration 0004 SQL.
- YAML schemas for notes_md_state, cross_ai_capture, doc_set artifacts.
- F6 NOTES.md template versioning detail.
- F8 OpenMontage serialization JSON shape (depends on OpenMontage's `edit_decisions` + `asset_manifest` schema details).
- Cross-Claude review wave on this v0.1 (analog to Phase 2 v0.1 → v0.2 wave).

This SCAFFOLD lets review-Claude pressure-test Phase 3 entry assumptions before substantial code or schema work begins. v0.2 folds review findings + Phase 2 acceptance-bridge real-world data from the Wave B firing.

---

## Phase 2 acceptance bridge gate

Per cross-Claude review v0.6, **Phase 3 should not start before Phase 2 acceptance bridges from "code-shipped" to "acceptance-validated."** Bridge components:

1. ✅ Phase 2 code shipped (Wave A + Wave B + Phase 2.5)
2. ✅ Synthetic tests green (16/16)
3. ✅ Rubric seed scaffolded (`tool_build/seeds/AUDIT_RUBRICS_v1_0_seed.md`)
4. ⏳ Joseph: rubric authoring (~5-15 min; copy seed → `docs/AUDIT_RUBRICS_v1_0.md` + fill `pass:`/`partial:`/`fail:` bullets per criterion)
5. ⏳ One real Wave B firing per `PHASE_2_E2E_PLAN.md` (~30 min + ~$0.30)
6. ⏳ Bank result in `banked_items.md`

Until 4-6 cross, Phase 3 design v0.2 is on hold. v0.1 substrate (this doc) is preparatory and doesn't violate the gate.

---

## Banked Phase-3 estimating signals (apply to draft estimate below)

Per Phase 2 design-notes maintenance log v0.2-v0.6:

1. **spec-estimate-undercut** (Phase 1 retrospective): first-phase estimate undershoots by ~50% because discipline-inventing overhead is invisible at spec time.
2. **spec-mechanism-undercut** (Phase 2 Day 1 finding): even with realistic estimate, the design-assumed mechanism can be wrong. Inspect actual data on Day 1 of each phase before committing to mechanism.
3. **spec-role-overspecification** (Phase 2 Day 2 finding): design notes can mis-assign editorial work to Claude. Distinguish mechanical vs decision work explicitly via "is this mechanical or editorial?" check before scoping a phase day.
4. **spec-overestimate-when-substrate-is-mature** (Phase 2 close): when prior phase substrate is well-tested + well-documented, next phase compresses 5-10× via substrate-on-substrate work. Caveat: code-shipped ≠ acceptance-validated; velocity factor applies to substrate-on-substrate, NOT to novel external integration.
5. **user-blocking work** (Phase 2 v0.6): when design creates a "ships without X but acceptance requires X" gap, the gap is functionally a blocker for acceptance even when the design says otherwise. Phase 3 design notes should name user-prerequisites as e2e-acceptance blockers upfront.

**Phase 3 draft estimate (subject to v0.2 sharpening):**

- Spec said: ~2-3 weeks for Phase 3 (per v1_spec_proposal.md Phase 3 paragraph).
- Apply signals 1+4: substrate-on-substrate work compresses; novel-external-integration (F8 OpenMontage serialization) doesn't.
- Estimate: **~1-2 weeks** for the substrate-on-substrate parts (F5 hero promotion, F6 NOTES.md authorship, F7 cross-AI capture); **+~3-5 days** for F8 OpenMontage serialization (novel external integration with OpenMontage's `edit_decisions` + `asset_manifest` schemas).
- Total: ~2-3 weeks if Joseph-time-blocking work (NOTES.md template versioning content, cross-AI captures of real exchanges, rubric extensions for new concept types) doesn't accumulate.
- Apply signal 5: **NOTES.md authorship is user-blocking** (Joseph writes NOTES.md content; F6 acceptance requires real NOTES.md to exist) → e2e acceptance bridges similar to Phase 2's rubric-authoring bridge.

---

## Phase 3 features overview

### F5 — Hero promotion atomic action (carryover from Phase 2 per Q1 v0.2 call)

Spec deferred F5 from Phase 2 because its atomic action depends on F6 (NOTES.md authorship) + Phase 3 doc-set data model. Phase 3 ships F5 alongside F6 — atomic action is genuinely atomic, not split-shipped.

**Substrate-on-substrate work** (compresses): the `hero_promotions` schema already exists from Phase 1 Migration 0001; the audit viewer's verdict-marking surface (Wave A) already gets Joseph 80% of the way to "this render is hero." F5 adds the remaining 20% — file-move to `winners/`, NOTES.md update prompt (depends on F6), enumerated doc-update coordination (depends on doc-set data model).

### F6 — NOTES.md authorship via Claude API

Substantial new feature. Spec elements:
- Status view per section (NOTES.md presence/absence/staleness per canonical EP1 section)
- Template menu (per F10 — not enforcement)
- Templates versioned independently of overall discipline_version (per Q2 v0.2 confirmation)
- Hero-promotion-triggers-NOTES-prompt event (depends on F5 atomic action wiring to F6 surface)
- Authorship via Claude API: prompt construction includes `(concept, hero_renders, prior_notes_md, current_template_version, project_context, tool_grammar_config)`

**Substrate-on-substrate** (compresses): existing llm.py wraps Anthropic API call with cost-tracking; existing template-menu pattern from MJ tool-grammar config; existing api_calls table.

**User-blocking** (signal 5 applies): Joseph writes the NOTES.md template versioning content — the templates themselves are project-vocabulary-specific, not Claude work. Phase 3 acceptance bridge mirrors Phase 2's: scaffold templates in `tool_build/seeds/`, Joseph copies to canonical, fills in template body, then Phase 3 e2e plan exercises the path.

### F7 — Cross-AI / cross-Claude capture surface

Net-new high-risk feature per spec (UX shape uncertain). Capture surface for Joseph's cross-AI exchanges (Perplexity / ChatGPT / Grok / Gemini / parallel Claude instance) into structured filesystem artifacts.

**Substrate-on-substrate** (compresses): existing `cross_ai_captures` table (created empty in Migration 0001 for forward-compat); existing form-handling pattern in app.py; existing YAML write-before-SQL discipline.

**Per Q4 v0.2 default**: last-touched finding/decision as default relevance binding, editable before save. v0.1 of Phase 3 ships this default; v0.2+ refines based on actual capture friction.

**Compressed-input + AI-expansion pattern** (per M3): primary input flow. Joseph pastes compressed answer → Claude API expands using project context → captured pair preserves verbatim Joseph input alongside Claude expansion. Substrate-on-substrate (uses existing llm.py); novel because the prompt structure is new (M3 hasn't been built before).

### F8 — Serialization to OpenMontage

**Novel external integration** (signal 4 caveat applies — does NOT compress). Phase 3 builds the bridge from tool_build's structured data to OpenMontage-compatible JSON: `edit_decisions` (one per section) + `asset_manifest` (heroes + alternates).

**Per Q6 v0.2 confirmation**: per-section trigger; NOTES.md-completion event surfaces "section X is NOTES.md-complete; ready to serialize." Joseph reviews serialized JSON before handing off to OpenMontage's compose stage.

**v0.2 prerequisite**: read OpenMontage's `schemas/artifacts/edit_decisions.schema.json` + `asset_manifest.schema.json` to align tool_build serialization output. v0.1 SCAFFOLD doesn't commit to specific JSON shape — that's v0.2 work informed by reading those schemas.

### Phase 2 carryovers

Per banked_items.md Phase 3 territory section:

- **Tool-grammar config expansion to GPT Image 2 + Kling + ElevenLabs** — depends on Phase 1 + Phase 2 successful_examples accumulation. Trigger: when verdict-confirmed-strong outputs seed enough data per Q3.
- **3a hardening review** — largely landed Phase 1 Day 12; Phase 3 audit confirms no remaining gaps after real Wave B usage.
- **Render-group compare-and-rank view (F5+ extension)** — grid view of generations grouped by prompt or concept; ranking via filesystem rank-slot subdirs. Surfaced 2026-05-05 by Joseph after Phase 1.5 e2e run. Open design questions banked in `banked_items.md`.
- **Filepath-heuristics recovery + `unknown_image_terminal` status** — per Phase 2 review banking. The 367 truly-opaque renders need either filepath-heuristics recovery (~50% expected) OR explicit terminal-unknown status to stop indefinite recovery work.

---

## Migration 0004 schema sketch (v0.1)

Detailed SQL deferred to v0.2. v0.1 names the new tables + columns:

**`notes_md_state`** (new): per-section NOTES.md presence + template_version + authored_against discipline_version + staleness flag. Supports F6 status view + discipline-drift query expansion.

**`doc_set`** (new): doc-set data model per spec data model. References-as-data primitives — when NOTES.md cites "channel staple #11," that's a structured reference (doc_set entry pointing at canonical channel architecture doc), not free-text. Supports F12 inheritance audit + reference resolution.

**`cross_ai_captures`** (existing, expand): table created empty in Phase 1; v0.1 of Phase 3 lights it up with the F7 capture surface. Already has columns for source / discipline_version / yaml_path / captured. Likely needs `relevance_binding` (which finding/decision was last-touched) + `original_prompt_hash` (compressed-input + AI-expansion pair-tracking per M3).

**`lineage_edges`** layer-3 extension: layer-3 = channel-arch → ep-arch → NOTES.md inheritance. Existing schema already has `layer INTEGER NOT NULL` so no migration needed for the column itself; just usage. F12 inheritance audit queries against layer-3 edges.

**Migration 0004 candidate inclusions** (deferred decision to v0.2):
- Partial index `idx_verdicts_flagged` on `flags_needs_second_look = 1` (deferred from Phase 2 per Q2 review).
- `unknown_image_terminal` status pattern in renders.tool taxonomy (per Phase 2 review banking).
- `notes_md_state` + `doc_set` tables.

---

## High-level failure-mode outline (v0.1; detail deferred to v0.2)

Per Phase 2 §1 pattern, each feature gets numbered failure modes. v0.1 lists the categories; v0.2 fills in behavior detail.

**F5 hero promotion failure modes:**
- 5.1 Render file missing at promotion time
- 5.2 Hero `winners/` directory doesn't exist for that section
- 5.3 NOTES.md update prompt fires but F6 isn't ready
- 5.4 Doc-update coordination fails mid-loop (some docs updated; others not)
- 5.5 Un-hero (reverse promotion) per channel staple #12 — `_DEPRECATED_<reason>` directory + reason-required validation

**F6 NOTES.md authorship failure modes:**
- 6.1 Claude API rate limit (mirrors 3a.1)
- 6.2 Claude API auth error (mirrors 3a.2)
- 6.3 Claude API timeout (mirrors 3a.4)
- 6.4 Hallucinated NOTES.md content (Joseph review catches; never auto-commits)
- 6.5 Template version mismatch with discipline_version

**F7 cross-AI capture failure modes:**
- 7.1 Compressed-input + AI-expansion: Claude API down → manual capture fallback
- 7.2 Source attribution missing (which AI / which chat?)
- 7.3 Relevance binding ambiguous

**F8 serialization failure modes:**
- 8.1 OpenMontage `edit_decisions` schema doesn't accept the shape we generate
- 8.2 Per-section trigger fires before NOTES.md is actually complete
- 8.3 OpenMontage compose stage rejects asset_manifest references

---

## Build sequence sketch (waves; v0.2 sharpens)

**Wave 1 (substrate-on-substrate, ~3-5 days):**
- Migration 0004 (notes_md_state + doc_set + carryovers).
- F5 hero promotion atomic action endpoint (depends on F6 prompt being scaffold-ready).
- F6 NOTES.md authorship Claude API integration (uses existing llm.py).
- Audit viewer extension: hero-promotion button in serial view sidebar (composes with existing verdict-marking).

**Wave 2 (NOTES.md template authoring + F6 e2e, ~3-5 days):**
- NOTES.md template seeds in `tool_build/seeds/notes_md_template_v1_0_seed.md` (analog to Phase 2 rubric seed).
- Joseph fills in template content (e2e bridge analog to Phase 2 rubric authoring).
- F6 e2e plan documented + run once.

**Wave 3 (F7 cross-AI capture, ~3-4 days):**
- `/capture` endpoint + UI form.
- Compressed-input + AI-expansion flow via existing llm.py.
- M3 prompt structure new — design + iterate.

**Wave 4 (F8 OpenMontage serialization, ~3-5 days):**
- Read OpenMontage schemas; align tool_build output.
- Per-section trigger via NOTES.md-complete event.
- Serialization JSON output + Joseph review surface.

**Wave 5 (Phase 3 close + acceptance bridge, ~1-2 days):**
- F5/F6/F7/F8 e2e plans documented.
- One real run per plan.
- Bank results.

**Total Phase 3:** 13-21 days substrate-on-substrate; F8 + e2e bridges add 4-7 days. Range 17-28 days. Median estimate: ~3 weeks. Spec said 2-3 weeks; signal 4 says compress; signal 5 says e2e bridges add real time. Net: roughly aligned with spec on first authoring (per the v0.5 prediction that Phase 3 spec should land in realistic ballpark).

---

## Phase 3 prerequisites (must land before Wave 1 code)

| Prereq | Status |
|---|---|
| Phase 2 acceptance bridge crossed (rubric authored + one real Wave B firing + result banked) | ⏳ |
| Cross-Claude review wave on this v0.1 | ⏳ |
| Phase 3 v0.2 design notes settled (failure modes detailed; Migration 0004 SQL spec; F6 template versioning concrete; F8 schema-alignment with OpenMontage) | ⏳ |
| F6 user-prerequisite identified upfront (signal 5): NOTES.md template content authoring is Joseph editorial work; e2e bridge analogous to Phase 2 rubric bridge | ✅ named |
| F8 user-prerequisite identified upfront (signal 5): OpenMontage compose-stage testing requires real video assets; e2e bridge requires Joseph driving compose run | ✅ named |
| OpenMontage `schemas/artifacts/edit_decisions.schema.json` + `asset_manifest.schema.json` read + understood | ⏳ — required for v0.2 |

---

## Open questions (v0.1; v0.2 may resolve some)

1. **Hero promotion + audit viewer composition.** F5 atomic action belongs in audit viewer (verdict → hero), or in a separate hero-promotion endpoint? Audit viewer already has verdict marking; "promote to hero" is a one-button extension.
2. **NOTES.md template scope per section.** Does each canonical section (h1_hook, h5_slot_machine, etc.) get its own template, OR shared per concept-type? Q5-style Q to settle in v0.2.
3. **Cross-AI capture relevance binding default.** Per Q4 v0.2: "last-touched finding/decision." But "last-touched" needs definition — last verdict marked? Last concept opened? Last consultation run? v0.2 settles.
4. **F8 trigger granularity.** Per-section (Q6 v0.2 confirmation) — but does "NOTES.md complete" mean Joseph clicks done, or NOTES.md state is durable (`authored_against_discipline_version` matches current)?
5. **`unknown_image_terminal` status placement.** Add to renders.tool taxonomy vs renders.status (currently no status column on renders)? v0.2 schema work decides.
6. **Multi-AI batch consultation (deferred per Phase 2 4.12).** Phase 3 trigger to ship: when 3+ providers exist and bulk consultation is requested. v0.1 names the trigger; v0.2 doesn't add it unless trigger fires.

---

## Document maintenance

- **v0.1 (2026-05-07):** SCAFFOLD authored at Phase 2 close. Five banked Phase-3-estimating signals applied to draft estimate (~3 weeks median; range 17-28 days). Phase 2 acceptance bridge gate explicitly named. Migration 0004 schema sketch. High-level failure-mode outline. 5-wave build sequence sketch. Detailed schema + failure-mode + JSON-shape work deferred to v0.2 after Phase 2 acceptance bridges + cross-Claude review folds in. F6 + F8 user-prerequisite blockers (signal 5) named upfront. SCAFFOLD lets review-Claude pressure-test Phase 3 entry assumptions before substantial code or schema work begins.
