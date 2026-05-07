# F6 — NOTES.md authorship Claude API prompt structure (DRAFT)

**Date:** 2026-05-07
**Status:** v1.0 DRAFT — preparatory spec for Wave 2 Day 2-3 implementation. NOT the actual `dispatcher.author_notes_md` function (lands when Phase 2 acceptance bridges cross + Wave 1 Day 2-3 unblocks). Surfaces prompt structure decisions now so implementation is mechanical transcription.
**Source:** `phase3_design_notes.md` v0.2 §"F6 — NOTES.md authorship via Claude API" + spec Q9 (authorship via Claude API) + F3 sharpening (per spec) + existing `llm.py` substrate + `seeds/notes_md_*_seed.md` 7 scaffolds for body context.

---

## Scope

F6 NOTES.md authorship surfaces a Claude API call that takes
`(concept, hero_renders, prior_notes_md, current_template_version,
project_context, tool_grammar_config)` per spec § "Authorship via
Claude API" and produces a NOTES.md draft Joseph reviews + edits
before save (per spec — never auto-commits).

This doc spec the prompt structure for that Claude API call: system
prompt content, user message structure, cache_control boundaries,
cost expectations, iteration patterns, project-content guards
(per AUDIT_PATTERNS Pattern #8).

---

## Prompt structure overview

```
┌─ SYSTEM PROMPT (cached via ephemeral cache_control) ─────────────┐
│ - Channel architecture context (channel staples, render-craft     │
│   conventions)                                                    │
│ - EP1 architecture context (section-level structure)              │
│ - Template scaffold for the requested section                     │
│ - Existing-NOTES.md gold-standard examples (h3_skinner, h4_match  │
│   _cut for SHIPPED + LOCKED patterns)                             │
│ - Format rules (Status header convention, Block deliverable, etc.)│
│ - Discipline rules (channel staple #11, do-not-re-iterate-casually)│
└────────────────────────────────────────────────────────────────────┘

┌─ USER MESSAGE (per-section, NOT cached) ─────────────────────────┐
│ - Section name + concept (e.g., h5_slot_machine + variable ratio) │
│ - Current state: existing NOTES.md if any, OR empty               │
│ - Hero renders (paths + verdict + verdict_reasoning)              │
│ - Recent ai_consultations on those renders (verdict_inference,    │
│   key_observations)                                               │
│ - Lineage edges connecting these renders to prior section work    │
│ - Joseph's authoring intent (free-text optional: "I want this     │
│   NOTES.md to emphasize the apparatus-fidelity story")            │
│ - Output instruction: structured Markdown matching the template,  │
│   NOT preamble/commentary                                         │
└────────────────────────────────────────────────────────────────────┘
```

System prompt is **cache-stable** within an audit session — the
channel architecture + EP1 architecture + template scaffold +
gold-standard examples don't change between consecutive section
authorings. Repeat F6 calls within a session hit cache (10× cost
reduction on input side per Phase 2 v0.2 §3 cache boundary
discipline).

User message is **per-section + per-state** — varies on each call
because the hero renders + verdicts + consultations + Joseph's
intent are section-specific.

---

## System prompt content (detailed)

```
You are authoring a NOTES.md file for a section of EP1 of the
Latent Systems channel — an AI-native, calm-observational
documentary channel about behavioral conditioning architecture
(Skinner box, slot machine, variable-ratio reinforcement, opioid
crisis pattern, etc.).

NOTES.md is recipe-authority per channel staple #11. Section is
"ready to serialize" for OpenMontage when this file captures the
recipe.

# Channel architecture context

[Channel staples relevant to NOTES.md authoring — pulled from
docs/CHANNEL_STRUCTURAL_ARCHITECTURE_v1_5.md. Cache-stable.]

- Channel staple #9: Daniel narration register (calm, authoritative,
  slightly-ominous; NOT performative-ominous; NOT movie-trailer drift)
- Channel staple #10b: render-craft exemplars (12 canonical
  reference renders at shared/render_craft_exemplars/)
- Channel staple #11: NOTES.md as recipe-authority
- Channel staple #12: hero promotion + un-promotion via _DEPRECATED_
  <reason>/ subdirs with reason required
- Channel staple #13: compressed-form four-step pattern recognition
- Channel staple #15: AI-native channel identity positioning
- Render-craft conventions: schematic_apparatus / cinematic_atmospheric
  / composite_subject / latent_space / surreal_subject directions

# EP1 architecture context

[Section-level structure pulled from
docs/EP1_STRUCTURAL_ARCHITECTURE_v1_4.md. Cache-stable.]

EP1 is structured as Cold Open + sections §1-§18 mapping to
filesystem directories cold_open + h1_hook through h9_ep2_tease +
card_*/k_* sub-features. Five-act structure per architecture §5:
Setup (cold open through §6) / Progressive Complications (§7-§12) /
Ordeal (§13) / Reward (§13A) / Crisis-Climax (§15-§16) / Resolution
+ Meta-Move (§17-§18).

Archetypal mapping per architecture §7 [section-by-section
descriptions inline].

# Template scaffold for this section

[Per-section template from tool_build/seeds/notes_md_<section>_v1_0_seed.md
OR Joseph's authored version from ep1/<section>/NOTES.md if exists.
This is the structural skeleton the draft fills in.]

# Existing NOTES.md gold-standard examples

[h3_skinner SHIPPED-with-qualifiers pattern; h4_match_cut LOCKED-
with-technical-detail pattern; h2_face_glow PENDING-DECISION
pattern. Pulled verbatim from canonical files.]

# Format rules

- Status header at top: "**Status:** <state>" where state is one of
  NOT STARTED / IN ITERATION / LOCKED / SHIPPED / PENDING DECISION,
  with optional sub-state qualifiers in parentheses.
- "Timecode in EP1:" if known (format: M:SS-M:SS).
- "Load-bearing line:" if applicable.
- Section headings match the template: ## Status / ## Block deliverable
  / ## Sources / ## Trimmed / ## Reference / ## Pending / ##
  Architecture deviations / ## Do not re-iterate casually.
- File paths within tool_build's canonical structure (relative to
  ep1/<section>/).
- Technical specs (resolution, codec, frame rate, duration) stated
  precisely when applicable.

# Discipline rules

- NEVER speculate beyond evidence in the user message. If a section
  is at NOT STARTED, write the structural skeleton with TODO markers,
  not invented production state.
- NEVER use performative-ominous language. Channel staple #9 register.
- NEVER use movie-trailer phrasing ("haunting", "shocking",
  "mysterious"). Calm-observational only.
- ALWAYS preserve existing prior NOTES.md content patterns where
  Joseph established them. New content layers on top, doesn't
  overwrite.
- ALWAYS reference canonical filepaths precisely (relative to
  projects/latent_systems/ep1/<section>/).
- DO NOT re-iterate casually (channel staple). Once a section reaches
  SHIPPED, only re-open for specific identified problems.

# Output format

Respond ONLY with the NOTES.md content as Markdown. No preamble.
No closing remarks. No "Here is your NOTES.md draft:" wrapper.
The first character of your response should be the Markdown header.
```

**Length estimate (system prompt):** ~3000-5000 tokens. Cache hit
makes repeat calls within session ~10× cheaper on input side.

---

## User message structure (per-section, per-call)

```
Section: <section_name>  (e.g., h5_slot_machine)
EP1 section identifier: <§N from architecture>

# Current NOTES.md state

[If ep1/<section>/NOTES.md exists: paste verbatim.
If not: "(no existing NOTES.md; this is initial authoring)"]

# Hero renders for this section

[For each render with verdict='hero_zone' OR verdict='strong' in
this section's renders, include:]
- render_id: <id>
  filepath: <relative path>
  verdict: <verdict>
  verdict_reasoning: <reasoning if any>
  tool: <tool>
  variant: <variant if MJ>
  audited_at: <iso>

# Recent AI consultations on these renders

[For each ai_consultation linked to verdicts above, include:]
- consultation_id: <id>
  verdict_id: <linked verdict>
  provider: <provider>
  status: <status>
  parsed:
    verdict_inference: <inference>
    criteria_match: <criteria match per criterion>
    key_observations: <list of brief observations>

# Lineage edges connecting this section

[For renders with lineage_edges, include incoming + outgoing edges
limited to most-relevant 10. Cap at 10 to keep prompt manageable
per F6 6.6 context-window check.]

# Joseph's authoring intent (optional)

[If Joseph specified intent at endpoint call time, include here:
"I want this NOTES.md to emphasize ___" or "Update production state
to reflect ___" or empty.]

# Author-against template version

current_template_version: <version>
authored_against_discipline_version: <version>

# Output: write the full NOTES.md content per system prompt rules.
```

**Length estimate (user message):** ~2000-5000 tokens depending on
section's render count + lineage depth. Plus images NOT included
(F6 is text-only per cost scope; image context comes via verdict
+ consultation data).

---

## Cost expectations

Per Phase 2 v0.5 cost estimates ($0.05 per text-only Claude API
call placeholder; F6 is text-only):

- First-section authoring: ~$0.05-0.10 (full system prompt loaded;
  cache miss).
- Subsequent sections in same audit session: ~$0.01-0.02 (cache hit
  on system prompt; user message dominates input cost).
- Per-Joseph authoring run (10 sections): ~$0.50-2.00 cumulative
  if all in single session.
- Multi-day authoring (cache TTL 5 minutes): cache won't persist
  across sessions; each new session starts with cache miss.

Cumulative F6 acceptance bridge cost estimate: $1-5 across all
NOTES.md authoring + iteration cycles.

---

## Iteration patterns

F6 endpoint produces draft → Joseph reviews → 3 likely outcomes:

**Outcome A: Joseph saves as-is.** Draft was good. Notes_md_state
row updated; YAML written; F6 endpoint logs `audited_by =
"claude_assisted"`.

**Outcome B: Joseph edits before save.** Draft was directionally
right but needed polish. Joseph's edits saved; `audited_by` flagged
with edit-count or marked `human_with_assist`.

**Outcome C: Joseph rejects + re-prompts.** Draft was wrong
(captured wrong production state, used wrong register, missed
canonical references). Joseph adjusts authoring intent + re-fires
F6 endpoint. Iteration count tracked per section.

**Iteration cycle estimate (per signal 5 banking + v0.1 review
item 5):** 2-3 iteration cycles per section before structure
stabilizes. First section likely needs more cycles (3-4) as Joseph
calibrates F6's prompt understanding against actual project
discipline; subsequent sections compress (1-2 cycles).

---

## Project-content guards (per AUDIT_PATTERNS Pattern #8)

F6's draft generation must respect project-specific discipline that
generic NOTES.md drafts wouldn't anticipate:

**Guard 1: Channel staple #9 register.** Daniel narration is
calm-authoritative-slightly-ominous. NEVER use performative-ominous
language ("haunting", "shocking", "mysterious"). Test fixture: prompt
with H#3 Skinner box + addiction theme; verify draft doesn't drift
to movie-trailer register.

**Guard 2: Canonical filepath precision.** Drafts MUST reference
filepaths relative to `ep1/<section>/`. Test fixture: prompt with
h5_slot_machine; verify draft uses `sources/`, `trimmed/`,
`assembled/` correctly (not invented paths).

**Guard 3: Production-state honesty.** NEVER speculate beyond the
hero renders + consultations provided. If section is at NOT STARTED,
draft writes structural skeleton + TODO markers, NOT invented
production state. Test fixture: prompt with no hero renders; verify
draft stays at structural-skeleton level.

**Guard 4: Channel staple #11 recipe-authority discipline.** Draft
must capture enough recipe detail that F8 serialization can extract
asset_manifest entries. NOT marketing prose. Test fixture: prompt
with h3_skinner SHIPPED state; verify draft captures all 4 sources
+ all 4 trimmed versions + assembled output specs.

**Guard 5: H#3 Skinner box + addiction-themed content.** Per Pattern
#8: draft generation against project content (rats, slot machines,
addiction architecture) should NOT trigger AI safety self-censorship
in draft body. Test fixture: prompt with h3_skinner v3 reenactment
context (rat-collapsed-prone state); verify draft doesn't refuse
or hedge.

---

## Test fixtures (Pattern #8 mandatory third bucket)

**Positive cases (Joseph should accept the draft as-is or with
minor edits):**
- F6 prompt for h3_skinner (SHIPPED state) → draft matches the
  existing canonical NOTES.md within ~80% structural similarity.
- F6 prompt for h5_slot_machine (NOT STARTED state) → draft is
  structural skeleton with TODO markers; no invented production state.

**Project-specific looks-like-target-but-isn't (must NOT regress):**
- F6 prompt for h3_skinner with H#3 v3 reenactment context → draft
  captures rat-collapsed-prone production state without safety
  self-censorship.
- F6 prompt asking for "compelling narrative arc" framing → draft
  refuses to use movie-trailer language; stays in calm-observational
  register per channel staple #9.
- F6 prompt with no hero renders → draft is honest about NOT STARTED
  state; doesn't invent file paths.

**Negative cases (must reject):**
- F6 endpoint with empty section name → 400 validation error.
- F6 endpoint with non-existent section → 404 not found.
- F6 endpoint with no API key configured → 502 with retryable hint.

---

## Failure modes (carryover + extension from Phase 2 §1)

Per phase3_design_notes.md v0.2 §"F6 NOTES.md authorship failure
modes":

- 6.1 Claude API rate limit (mirrors 3a.1 — uses retry queue)
- 6.2 Claude API auth error (mirrors 3a.2 — surface modal)
- 6.3 Claude API timeout (mirrors 3a.4 v0.4 amendment — single
  60s auto-retry then manual)
- 6.4 Hallucinated NOTES.md content (Joseph review catches; never
  auto-commits to canonical)
- 6.5 Template version mismatch with discipline_version (refuse
  to draft against stale template; surface "template needs revisit"
  status)
- 6.6 Template body too long (Anthropic context window check;
  truncate prior_notes_md if needed; mirrors 4.11 vision context-
  exceeded handling)
- **6.7 (NEW per this draft):** Project-content safety self-
  censorship — draft refuses to engage with H#3 reenactment imagery
  or addiction-architecture content per Anthropic safety filter.
  Mitigation: detect refusal in draft body (similar to vision
  adapter's _SAFETY_REFUSAL_RE per AUDIT_PATTERNS Pattern #8);
  fall back to "no AI draft available; author manually" UI state.

---

## Implementation hooks (Wave 2 Day 2-3)

```python
# dispatcher.py — Wave 2 Day 2-3 extension

def author_notes_md(
    *,
    section: str,
    template_version: str = "1.0",
    authoring_intent: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> dict:
    """Phase 3 Wave 2 NOTES.md authorship via Claude API.

    Per phase3_design_notes.md v0.2 §F6 + F6_DRAFT_PROMPT_DRAFT.md:
      1. Load section's notes_md_state row + existing NOTES.md if any.
      2. Query hero renders + verdicts + ai_consultations for the section.
      3. Query lineage_edges for those renders.
      4. Build system prompt (cached via ephemeral cache_control).
      5. Build user message per F6_DRAFT_PROMPT_DRAFT.md structure.
      6. Call llm.call_claude with purpose='notes_md_authorship'.
      7. Detect failure mode 6.7 (safety refusal in draft body).
      8. Return draft for Joseph review (does NOT auto-commit).
    """
    pass


def save_notes_md(
    *,
    section: str,
    content: str,
    template_version: str,
    audited_by: str = "claude_assisted",  # or 'human' or 'human_with_assist'
) -> dict:
    """Joseph's save action commits draft to canonical NOTES.md +
    updates notes_md_state row. Separate from author_notes_md so
    Joseph review-and-edit flow is explicit."""
    pass
```

Endpoint pair:
- `POST /audit/notes-md/<section>/draft` → returns draft (no commit)
- `POST /audit/notes-md/<section>/save` → commits draft (or edited
  version) to canonical NOTES.md path; updates notes_md_state row

---

## Open questions for Wave 2 Day 2-3 implementation

1. **System prompt cacheability boundary.** Channel architecture +
   EP1 architecture + render-craft conventions are stable across
   sessions; template scaffold + gold-standard examples are also
   stable. All four belong in cache_control system block. But
   does the system prompt change per-section? **Recommendation:**
   single system prompt covers all sections; section-specific
   info goes in user message. Cache hits across all section
   authorings within a session.

2. **Hero renders selection cap.** A section may have 5+ renders
   verdicted at hero_zone. Include all in user message? Cap at 3?
   **Recommendation:** include all hero_zone + strong verdicts
   (typically 1-5 per section); cap user message at 8000 tokens
   (per 6.6 mitigation). If section exceeds, drop oldest hero_zone
   first (newest carry more recent context).

3. **prior_notes_md inclusion vs replacement.** When Joseph re-fires
   F6 against a section that already has NOTES.md, does the draft
   replace or augment? **Recommendation:** prompt instructs draft
   to layer on top of prior content (preserve Joseph's voice +
   conventions); NEVER replace wholesale. Save action shows diff
   for Joseph review.

4. **Iteration count tracking.** Track per-section F6 call count
   for cost-attribution + bridge-time analytics? **Recommendation:**
   add `f6_iteration_count` column to notes_md_state in Migration
   0004 follow-up (Phase 3.5+ if friction surfaces; not blocking
   Wave 2). Until then, infer from `api_calls` table queries by
   purpose='notes_md_authorship' + section grouping.

5. **Multi-section draft batching.** Joseph may want to draft multiple
   sections in one workflow. Should F6 endpoint support batch?
   **Recommendation:** ship single-section v1; batch is Phase 3.5+
   if friction surfaces. Mirrors Phase 2 §F8 4.12 batch-deferred
   pattern.

---

## Document maintenance

- **v1.0 DRAFT (2026-05-07):** Phase 3 Wave 2 Day 2-3 preparatory
  spec for the F6 NOTES.md authorship Claude API prompt. System
  prompt structure (cache-stable: channel architecture + EP1
  architecture + template scaffold + gold-standard examples +
  format rules + discipline rules + output format). User message
  structure (per-section: section context + current state + hero
  renders + ai_consultations + lineage + Joseph's authoring intent).
  Cost expectations (~$0.05-0.10 first call, ~$0.01-0.02 subsequent
  per cache hit). Iteration patterns (3 outcomes per Joseph review;
  2-3 cycles per section). 5 project-content guards per
  AUDIT_PATTERNS Pattern #8. Test fixtures specified including
  H#3 reenactment + addiction-architecture content guards.
  Failure mode 6.7 added (safety self-censorship; mirrors vision
  4.10). 5 open questions for Wave 2 Day 2-3 implementation.
  Lives at `tool_build/F6_DRAFT_PROMPT_DRAFT.md` (sibling to
  Migration 0004 + filepath heuristics drafts + adapter mapping
  + e2e plans). Implementation transcribes from this when Wave 2
  Day 2-3 unblocks.
