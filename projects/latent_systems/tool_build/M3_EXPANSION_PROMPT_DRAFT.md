# M3 — Compressed-input + AI-expansion prompt structure (DRAFT)

**Date:** 2026-05-07
**Status:** v1.0 DRAFT — preparatory spec for Wave 3 Day 2-6 implementation. NOT the actual `audit_consult.expand_compressed_input` (or wherever the M3 endpoint lives) function. Surfaces prompt structure decisions for the explicitly-novel pattern v1 spec § F7 names ("compressed-input + AI-expansion as primary input pattern (per M3) ... hasn't been built before").
**Source:** `phase3_design_notes.md` v0.2 §F7 + spec M3 framing + existing `llm.py` substrate + Phase 2's prompt-engineering precedents (F6_DRAFT_PROMPT_DRAFT.md system/user split).

---

## Scope

F7 cross-AI capture has two flows:
- **5a. Manual capture** (verbatim paste of Perplexity/ChatGPT/Grok/Gemini exchange). Form-based; no AI involved.
- **5b. Compressed-input + AI-expansion** (M3 pattern). Joseph types a compressed thought; Claude API expands using project context; pair (compressed + expansion) saved as paired records.

This doc specs the prompt structure for flow 5b. It's the **novel pattern element** v1 spec explicitly flags as not-yet-built.

The M3 pattern is essentially **decompression**: Joseph speaks tersely (high context-density per token); Claude expands using channel architecture + EP1 state + recent banked decisions + relevance-binding context to articulate what Joseph compressed. Output preserves both forms so a reader-Claude / reviewer-Claude can verify the expansion matches Joseph's intent.

---

## Why M3 is novel (vs F6 NOTES.md authorship)

F6 produces a structured artifact (NOTES.md) against a template. The output shape is canonical; the intelligence is in filling it correctly.

M3 produces a **decompression annotation**: Joseph's compressed input + Claude's expansion as paired record. The intelligence is in:
1. Inferring what Joseph compressed (decompressing context Joseph elided)
2. Binding to the right project-state anchor (relevance_binding_id)
3. Articulating the expansion in a form that's reviewable + correctable

There's no canonical output shape. Each compressed input can decompress into different forms (technical decision, creative direction, banking-worthy insight, side observation). The expansion picks the form.

This makes M3 prompt design materially different from F6: F6 has a template the prompt fills; M3 has a context Joseph elided that the prompt reconstructs.

---

## Prompt structure overview

```
┌─ SYSTEM PROMPT (cached via ephemeral cache_control) ──────────────┐
│ - Project context: channel architecture + EP1 state               │
│ - Banked items + design notes maintenance log (recent banking      │
│   gives Claude what's been decided + open questions)              │
│ - Joseph's communication patterns (compression conventions,       │
│   register, recurring themes)                                     │
│ - Decompression discipline rules (preserve verbatim; infer don't  │
│   invent; surface ambiguity not gloss it)                         │
│ - Output JSON schema (paired record format)                       │
└────────────────────────────────────────────────────────────────────┘

┌─ USER MESSAGE (per-call, NOT cached) ─────────────────────────────┐
│ - Joseph's compressed input verbatim (potentially typo'd, terse)  │
│ - Relevance binding context (current finding/decision/concept that│
│   was last-touched per Q4 v0.2 default)                           │
│ - Recent context (last N audit-session events, last verdict        │
│   marked, last consultation run, last F6 NOTES.md authored)       │
│ - Joseph's binding override if specified (vs default)              │
└────────────────────────────────────────────────────────────────────┘
```

System prompt is **cache-stable** within an audit session — channel
architecture + recent banked items + Joseph's patterns don't change
between consecutive M3 calls. Repeat M3 calls hit cache (10× cost
reduction on input side per Phase 2 v0.2 §3 cache boundary).

User message is **per-call** — varies on each call because the
compressed input + relevance binding + recent-state context are
session-specific.

---

## System prompt content (detailed)

```
You are an AI assistant that decompresses compressed natural-language
inputs from Joseph (the project owner of Latent Systems, an AI-native
documentary YouTube channel about behavioral conditioning architecture).

Joseph speaks tersely. His compressed inputs assume context he has
elided. Your job is to decompress those inputs into fuller
articulations using the project context provided below, while
preserving Joseph's verbatim compressed text alongside the
expansion so a reviewer can verify the decompression matches his
intent.

# Project context

[Cache-stable. Pulled from PROJECT_ARCHITECTURE.md + LATENT_SYSTEMS_PROJECT_BRIEFING_v*.md
+ CHANNEL_STRUCTURAL_ARCHITECTURE_v1_5.md + EP1_STRUCTURAL_ARCHITECTURE_v1_4.md.]

[Channel staples relevant to compression interpretation:]
- #9 Daniel narration register (calm-authoritative-slightly-ominous)
- #11 NOTES.md as recipe-authority
- #13 compressed-form four-step pattern recognition
- #15 AI-native channel identity positioning

[EP1 architecture context:]
- 5-act structure (Setup / Progressive Complications / Ordeal / Reward /
  Crisis-Climax / Resolution-Meta)
- 18 §-numbered sections + cold open + sub-features
- Visual-identity 5 directions (latent_space / architectural_inhabitant /
  composite_subject / schematic_apparatus / surreal_subject)

# Recent banked items + open questions

[Pulled from banked_items.md + recent design notes maintenance log
entries (Phase 2 v0.6, Phase 3 v0.2). These are what's been decided
+ what's still open + what compressed inputs likely refer to.]

[Examples:]
- Phase 2 v0.6 settled: create_verdict_if_missing default = True (Joseph
  bulk-seed workflow)
- Phase 3 v0.2 open: F6 NOTES.md template scope per section
- Phase 3 v0.2 banked: 5 Phase-3-estimating signals (1-5)
- Phase 3 Wave 1 Day 1: F8 adapter mapping landed

# Joseph's communication patterns

- Compressed: "push", "do X", "ai ranks initially then i will review",
  "(a)", "yes" — high context-density per token; assumes interpretation
  via what was just discussed.
- Decisions often referenced via numbered options ("a", "b", "c") or
  by terse confirmation ("yes", "go").
- Theme-jumps are common: a compressed input may shift from
  "execution velocity" to "design wisdom" to "visual aesthetic" within
  the same session. Don't lock to one frame; surface multiple.
- Register: technical + analytical. Avoid performative-ominous; avoid
  movie-trailer language; calm-observational only (channel staple #9
  applies even to non-rendered Joseph text).

# Decompression discipline rules

- ALWAYS preserve `compressed_input_verbatim` exactly as Joseph typed.
  Including typos, ambiguities, partial sentences. Don't normalize.
- INFER what Joseph meant from project context + recent state. NEVER
  invent new context Joseph didn't reference.
- When ambiguity is real, surface it in `inferred_intent` rather than
  collapsing to one reading. Joseph reviews; Joseph picks.
- Bind to the relevance binding provided. If Joseph's compression
  fits a different binding, surface that as `binding_alternative`.
- NEVER use performative-ominous language; NEVER drift to movie-trailer
  register. Channel staple #9 applies.
- NEVER pad expansion with filler. Compression-to-expansion ratio
  should be ~3-5×. If you're going further, you're inventing.

# Output JSON schema

Respond ONLY with a JSON object matching this schema:

{
  "compressed_input_verbatim": "<Joseph's input, exact verbatim>",
  "expansion": "<your decompressed articulation, 3-5× the compressed length>",
  "inferred_intent": "<what you understood Joseph to mean — surface ambiguity if present>",
  "relevance_binding_evidence": "<why this binding fits — reference recent
                                 state or banked item that anchors it>",
  "binding_alternative": "<null OR a different binding if ambiguity is real>",
  "confidence": "high | medium | low",
  "follow_up_questions": ["<list of clarifying questions for Joseph if confidence is low or ambiguity surfaces>"]
}

No preamble. No closing remarks. JSON object only.
```

**Length estimate (system prompt):** ~3500-5500 tokens. Cache hit makes
repeat calls within session ~10× cheaper.

---

## User message structure (per-call)

```
Joseph's compressed input:
<verbatim text — potentially terse, typo'd, or fragmentary>

Relevance binding (default — last-touched per Q4 v0.2):
type: <concept | verdict | decision_log_entry | finding | open_question | other>
id: <id of the bound entity>
why default fits: <one sentence drawn from session timeline>

Recent state context (last ~5 audit-session events):
- <event 1>
- <event 2>
- ...
- <event N — most recent>

[If Joseph specified binding override: include here as "Joseph
override:" line.]

[If Joseph specified intent hint: include as "Joseph hint:" line.]
```

**Length estimate (user message):** ~500-2000 tokens. Compressed
input itself is ~10-50 tokens; bulk is recent-state context.

---

## Cost expectations

Per Phase 2 v0.5 cost estimates ($0.05 per text-only Claude API call):

- First M3 call in session: ~$0.05-0.10 (cache miss; full system prompt loaded).
- Subsequent M3 calls: ~$0.01-0.02 (cache hit; user message dominates).
- Per-Joseph M3 run (10 compressed inputs): ~$0.50-2.00 cumulative.
- Cumulative Phase 3 F7 cost: $1-5 across all M3 expansions; lower than
  F6 because M3 outputs are smaller (decompression annotation, not full
  NOTES.md draft).

---

## Iteration patterns

M3 endpoint produces JSON expansion → Joseph reviews → 4 likely
outcomes:

**Outcome A: Joseph saves as-is.** Expansion was good. Captures the
compressed input + expansion as paired records (cross_ai_captures
with paired_capture_id self-FK per Migration 0004 Step 2).

**Outcome B: Joseph edits expansion before save.** Expansion was
directionally right but needed adjustment. Joseph's edits saved;
audited_by tagged `human_with_assist`.

**Outcome C: Joseph rejects + adjusts binding.** Expansion was bound
to wrong concept/verdict/finding. Joseph picks the correct binding
and re-fires. Iteration count tracked.

**Outcome D: Joseph rejects + adjusts intent.** Expansion misread
Joseph's intent. Joseph adds intent hint and re-fires. Useful for
ambiguous compressed inputs.

**Iteration cycle estimate:** 1-2 cycles per compressed input on
average. Higher-confidence compressed inputs (Joseph's more familiar
patterns) hit Outcome A on first try; novel or ambiguous compressed
inputs more likely Outcome C/D.

---

## Project-content guards (per AUDIT_PATTERNS Pattern #8)

M3 expansion must respect project-specific discipline that generic
decompression wouldn't anticipate:

**Guard 1: Channel staple #9 register applies to Joseph's text too.**
M3 expansion drifts to performative or movie-trailer language is a
real risk because expansion is creative-text-generation. Test
fixture: compressed input "the apparatus reads me back" → expansion
must stay calm-observational; not "Skinner box becomes the haunting
mirror revealing your conditioning."

**Guard 2: Compression-to-expansion ratio bounded.** Joseph's
compressions are high-density. 3-5× expansion captures elided
context; >5× starts inventing. Test fixture: compressed input
"streak mechanic loss aversion" should expand to ~30-50 tokens
(loss-aversion psychology of streak mechanics in apps like Duolingo
applied to §10 DUOLINGO architecture per EP1 §6 PULL-TO-REFRESH
threshold-crossing → ordeal-of-recognition pattern), not 200+ tokens
of speculation.

**Guard 3: Verbatim preservation.** Joseph's typos / fragments are
information. NEVER normalize "i" to "I" or expand "tho" to "though"
in `compressed_input_verbatim`. Test fixture: input "ai ranks
initially then i will review" → verbatim preserved exactly; expansion
articulates the bulk-seed-then-review workflow without normalizing
the input.

**Guard 4: Relevance-binding evidence transparency.** Don't gloss the
binding. The reason Q4 v0.2 picked "last-touched" as default was
that explicit-binding required too much per-input context. M3 must
SURFACE the evidence so Joseph can verify the binding fits. Test
fixture: compressed input "the regex thing was important" with binding
default last-touched=consultation_xyz; if last-touched is actually
about something else, M3 should surface `binding_alternative`.

**Guard 5: H#3 Skinner box + addiction-themed content.** Same as F6
6.7: M3 expansion against Joseph's compressed thoughts about
behavioral conditioning + addiction must not trigger AI safety
self-censorship. Test fixture: compressed input "the system metabolizes
hero attempts" (referring to §9 Tristan Harris Absorbed-Hero
archetype) → expansion engages with addiction-architecture content
without hedging.

---

## Test fixtures (Pattern #8 mandatory third bucket)

**Positive cases (expansion should be useful):**
- Compressed input: `"do the notes_md scaffolds"` (recent session
  example) → expansion: "Joseph requests Phase 3 Wave 2 prep work —
  scaffold per-section NOTES.md template seeds in tool_build/seeds/
  per AD-5 (canonical paths read-only)..." Bind to Phase 3 prep work
  context.
- Compressed input: `"a"` after a 3-option question → expansion:
  surfaces the option(a) text + Joseph's pick; binds to most recent
  question's decision. Cite the question explicitly.

**Project-specific looks-like-target-but-isn't (must NOT regress):**
- Compressed input: `"haunting"` (could be drift signal!) → expansion
  must NOT use "haunting" reflexively in its own articulation. Channel
  staple #9 register applies even when discussing Joseph's word
  choice. Surface the word as Joseph's actual compressed input;
  articulate why it might not be the right register.
- Compressed input: `"the rat saw itself"` → expansion must engage
  H#3 Skinner box + Mirror archetype context without softening to
  "the test subject experienced recognition." Honor the verbatim
  while expanding context.

**Negative cases (must surface low confidence + follow-ups):**
- Compressed input: `"yeah"` with no recent context → confidence: low;
  follow_up_questions: ["What does this 'yeah' confirm? Recent
  decisions in session: <list>"]
- Compressed input: ambiguous between two recent open questions →
  binding_alternative populated; follow_up_questions surfaces both
  options.

**Decompression-ratio guard tests:**
- Compressed input: ~10 tokens → expansion should be ~30-50 tokens.
  Reject expansions >100 tokens as "padded" (would surface during
  review).
- Compressed input: 50 tokens (already verbose) → expansion ~150-250
  tokens. Joseph rarely compresses heavily here; expansion is more
  about articulating connections than decompressing density.

---

## Failure modes

Per phase3_design_notes v0.2 §F7 + extension:

- 7.1 Compressed-input + AI-expansion: Claude API down → manual capture
  fallback (form lets Joseph paste both compressed input + manually-
  written expansion if API unavailable).
- 7.2 Source attribution missing — required field; form refuses
  submit without explicit source.
- 7.3 Relevance binding ambiguous — default to last-touched; editable;
  M3 surfaces in `binding_alternative` when ambiguity real.
- 7.4 Paired-capture orphan (Joseph-input row exists; AI-expansion row
  never created or reverse) — UI surfaces orphan list; cleanup
  catches via `_sweep_orphans`-style walks.
- **7.5 (NEW per this draft):** M3 expansion confidence too-low to
  capture. M3 returns `confidence: low` + populated `follow_up_questions`.
  UI surfaces the follow-ups instead of saving the expansion;
  Joseph either answers the follow-ups (M3 re-fires with hint) or
  switches to manual-capture flow (5a).
- **7.6 (NEW per this draft):** M3 expansion produced output that
  fails JSON schema (parse_failed). Mirrors vision adapter 4.5
  parse_failed handling. Recovery: surface raw response to Joseph;
  let Joseph manually extract pair.
- **7.7 (NEW per this draft):** M3 expansion safety self-censorship
  on H#3 / addiction content (mirrors F6 6.7). Detect refusal;
  fall back to manual-capture flow.

---

## Implementation hooks (Wave 3 Day 2-6)

```python
# audit_consult.py — Wave 3 Day 2-6 extension (or new module
# tool_build/cross_ai_capture.py if scope justifies separation)

def expand_compressed_input(
    *,
    compressed_input: str,
    relevance_binding_type: Optional[str] = None,
    relevance_binding_id: Optional[str] = None,
    intent_hint: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> dict:
    """Phase 3 Wave 3 M3 compressed-input + AI-expansion.

    Per phase3_design_notes.md v0.2 §F7 + M3_EXPANSION_PROMPT_DRAFT.md:
      1. Resolve relevance_binding (default to last-touched per Q4
         v0.2 if not specified).
      2. Build user message per M3 prompt structure (compressed input
         + binding context + recent state).
      3. Call llm.call_claude with purpose='m3_expansion'.
      4. Parse JSON response (parse_failed → 7.6 fallback).
      5. Detect failure mode 7.7 (safety refusal in raw_response).
      6. Detect failure mode 7.5 (low confidence + follow-up
         questions surfaces).
      7. Return paired-record draft for Joseph review (does NOT
         auto-commit cross_ai_captures rows).
    """
    pass


def save_paired_capture(
    *,
    compressed_input_verbatim: str,
    expansion_text: str,
    relevance_binding_type: str,
    relevance_binding_id: str,
    confidence: str,
    audited_by: str = "claude_assisted",
) -> dict:
    """Joseph's save action commits the paired records (compressed +
    expansion) to cross_ai_captures with paired_capture_id self-FK
    per Migration 0004 Step 2. Two rows inserted; first is
    Joseph's input (expansion_text NULL); second is expansion
    (paired_capture_id linking back).
    """
    pass
```

Endpoint pair (mirrors F6's structure):
- `POST /audit/cross-ai-capture/expand` — body: `{compressed_input, relevance_binding_*?, intent_hint?}`
- `POST /audit/cross-ai-capture/save` — body: paired-record contents from review surface

---

## Open questions for Wave 3 Day 2-6 implementation

1. **Last-touched binding resolution.** What "last-touched" means
   needs concrete definition. Candidates: last verdict marked, last
   ai_consultation run, last F6 NOTES.md authored, last concept
   opened, last cross_ai_capture saved. **Recommendation:** maintain
   a session-scoped "last-touched" pointer that updates on any
   structurally-significant action; pointer tuple is (type, id,
   timestamp). M3's resolve_default_binding() reads the pointer.

2. **Recent state context window.** How many recent events to
   include in user message? **Recommendation:** last 5 events from
   the audit session (verdicts, consultations, NOTES.md authorings,
   prior captures). Cap at ~1500 tokens; older events summarized
   if window exceeds.

3. **Joseph's communication patterns updates.** System prompt has a
   section on Joseph's compression patterns. Does that section
   evolve as Joseph's patterns evolve, or stay static? **Recommendation:**
   stay static for v0.1 of M3; Phase 3.5+ may add learning loop if
   M3 expansion confidence drops over time (signal that Joseph's
   patterns shifted).

4. **Multiple-compressed-inputs in single message.** Joseph might
   paste multiple compressed thoughts in one input. Should M3
   expand each separately or treat as one? **Recommendation:**
   single input per call; M3 endpoint refuses inputs containing
   blank-line separators (basic heuristic). Joseph splits manually
   if intent is multiple.

5. **Cache invalidation on banked items update.** System prompt
   includes recent banked items. When `banked_items.md` updates,
   cache invalidates → next call pays cache miss. **Recommendation:**
   acceptable; banked items don't update mid-session typically.
   If they do (which Phase 2/3 has shown they can), the cost hit
   is small (~$0.05) per cache rebuild.

6. **`compressed_input_verbatim` vs `original_input_text`.** Migration
   0004 Step 2 added `original_input_text` column to cross_ai_captures.
   M3 prompt outputs `compressed_input_verbatim`. Same field?
   **Recommendation:** yes, same field. `original_input_text` in
   schema = `compressed_input_verbatim` in prompt JSON. Map at
   save_paired_capture() time.

---

## Document maintenance

- **v1.0 DRAFT (2026-05-07):** Phase 3 Wave 3 Day 2-6 preparatory spec
  for the M3 compressed-input + AI-expansion novel pattern. System
  prompt structure (cache-stable: project context + banked items +
  Joseph's communication patterns + decompression discipline rules
  + output JSON schema). User message structure (per-call:
  compressed input + binding context + recent state). Cost
  expectations ($0.05-0.10 first call; $0.01-0.02 subsequent). 4
  iteration outcomes patterns; 1-2 cycles average. 5 project-content
  guards per AUDIT_PATTERNS Pattern #8 (channel staple #9 register;
  compression ratio 3-5×; verbatim preservation; binding evidence
  transparency; H#3 / addiction-themed content engagement). Test
  fixtures including project-specific positive + looks-like-target-
  but-isn't + negative + decompression-ratio guards. Failure modes
  7.5/7.6/7.7 NEW per this draft (low confidence + parse_failed +
  safety refusal). 6 open questions for Wave 3 implementation. Lives
  at `tool_build/M3_EXPANSION_PROMPT_DRAFT.md` (sibling to
  F6_DRAFT_PROMPT_DRAFT.md + other Phase 3 design-spec docs).
  Implementation transcribes from this when Wave 3 Day 2-6 unblocks.
