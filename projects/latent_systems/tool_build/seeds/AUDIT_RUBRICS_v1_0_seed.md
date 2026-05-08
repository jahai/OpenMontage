---
version: "1.0"
discipline_version: "1.0"
applies_to_concept_types:
  - latent_space
  - architectural_inhabitant
  - composite_subject
  - schematic_apparatus
  - surreal_subject
---

# Audit Rubric v1.0 — SEED

This is a SEED scaffold. To use:

  1. Copy this file to `projects/latent_systems/docs/AUDIT_RUBRICS_v1_0.md`
     (per AD-5, only Joseph commits to `docs/`; this seed lives in
     `tool_build/seeds/` and is the editable bootstrap).
  2. Fill in the `pass:` / `partial:` / `fail:` bullets per criterion
     below. The criterion *definitions* are scaffolded here from
     `docs/HANDOFF_2026-05-02.md` Phase 2 evaluation criteria + the
     5-direction descriptions in `shared/visual_identity_phase1_references/README.md`;
     the *grading scale language* is yours to author.
  3. Verify the file parses cleanly, every criterion has all three
     bullets filled, AND no trailing content got folded into a
     criterion definition (the "footer pollution" failure mode — see
     "Authoring safety notes" below):
     ```bash
     cd projects/latent_systems/tool_build && python -c "
     from rubric import load_active_rubric
     r = load_active_rubric('/c/Users/josep/Desktop/desktop1/OpenMontage')
     assert r is not None, 'no rubric found in docs/'
     print('criteria:', list(r['criteria'].keys()))
     print('all bullets filled:', all(c['pass'] and c['partial'] and c['fail'] for c in r['criteria'].values()))
     print('footer-pollution check (any definition > 1000 chars):',
           any(len(c['definition']) > 1000 for c in r['criteria'].values()))
     "
     ```
     Expected: 6 criteria listed, `all bullets filled: True`,
     `footer-pollution check: False`.
  4. Once parsing passes, `POST /audit/render/{id}/consult` will fire
     against the rubric. Phase 2 acceptance bridge per PHASE_2_E2E_PLAN.md
     unblocks.

**Scope note:** v1.0 ships flat criterion list applying to all 5
concept types listed in front-matter (per `phase2_design_notes.md` §4
"Per-concept-type criteria scope deferred"). If a criterion needs to
scope to a single concept type later, add `concept_types_filter: [...]`
to that criterion's body — handled by Phase 2.5+ rubric parser
extension.

# Authoring safety notes (preamble — invisible to AI consultation)

These sections sit ABOVE the first H3 (`### Documentary integrity`)
deliberately. The parser ignores everything before the first H3
anchor; everything from the first H3 to EOF is folded into the
nearest H3's definition body.

**Critical authoring rule:** do NOT add any content (notes, tables,
horizontal rules, additional H1/H2 headings) AFTER the last H3
(`### Sonic-being preservation`). It will get appended to the last
criterion's definition and shipped to the AI verbatim. The footer-
pollution check in the verification command above catches this.

## Per-direction notes

The 5 concept types in `applies_to_concept_types` correspond to the
5 visual-identity directions documented in
`shared/visual_identity_phase1_references/README.md`:

| Concept type | Description |
|---|---|
| `latent_space` | typography within latent-space depth, blue-black gradients, particles |
| `architectural_inhabitant` | physical interior architecture, institutional palette, geometric composition |
| `composite_subject` | figures/faces assembled from multiple sources, monochromatic palette |
| `schematic_apparatus` | technical/schematic visualizations, scientific-document register |
| `surreal_subject` | animal subjects with anomalous human features (rat-with-human-face territory) |

For Phase 2.5+ when per-direction criteria become valuable: add
`### Per direction: <type>` H3 sections within the criteria block
below. The criterion list is order-independent for the AI, so insert
them anywhere in the H3 sequence — never after the last H3.

## Authoring tips

- Use existing canonical examples to anchor pass/partial/fail
  language. "K1 typography" pass. "H#3 Skinner box hero shot" pass.
  Recent _DEPRECATED renders (per `_work/<context>/_DEPRECATED_<reason>/`)
  are partial or fail examples. Note: the AI doesn't have the named
  references — your trailing observable adjectives are the actual
  signal ("sepia/warm-cast monochrome, single-source incandescent
  lighting" parses; "H#3 register" alone doesn't).
- Keep `pass:` / `partial:` / `fail:` bullets to 1-2 sentences each.
  Anthropic vision API gets the full text per criterion; longer than
  ~3 sentences risks dilution.
- Make `partial:` describe a specific recoverable mid-state, not just
  "between pass and fail." Each level should be diagnostic — what
  exactly distinguishes this level from the next.
- The parser is permissive on bullet casing (PASS:, Pass:, pass: all
  match) and bullet markers (- or *), but strict on H3 anchors (`### `
  with at least one space). H4+ subheadings get folded into the
  criterion's definition body.
- Test parse after each criterion is filled in (verification command
  in "How to use" section above).

## After authoring

1. Run the verification command from "How to use" above. `pytest
   tests/test_rubric.py` is NOT a useful check on the authored
   content — it tests the parser against inline fixtures, not your
   rubric file.
2. Optionally point the e2e plan at this rubric: PHASE_2_E2E_PLAN.md
   step 6 fires consultation against whatever rubric the loader finds.
3. Bank result in `banked_items.md` per "Phase 2 e2e run YYYY-MM-DD"
   heading once one consultation completes.

## Common criteria (apply across all 5 concept types)

These are the 6 evaluation criteria already named in
`docs/HANDOFF_2026-05-02.md` §"Specific next-session opening directive."

### Documentary integrity
The render's coherence with the channel's documentary register —
calm-observational, not movie-trailer drift, not performative-ominous.
References hold against existing canonical content (K1 typography,
H#3 Skinner box hero shot, L1 multi-beat composite).
- pass: TODO — what does pass on documentary integrity look like?
- partial: TODO
- fail: TODO

### Shorts effectiveness
The render reads at-a-glance in 9:16 framing for short-form
distribution (YouTube Shorts, TikTok). Subject + apparatus relationships
clear without context; works at thumbnail scale.
- pass: TODO
- partial: TODO
- fail: TODO

### Channel recognition
The render is identifiable as channel-content — visual-identity
holds against existing canonical exemplars (`shared/render_craft_exemplars/`
12-image set per channel staple #10b). Aesthetic is consistent enough
that a viewer encountering this independently recognizes it as
this channel.
- pass: TODO
- partial: TODO
- fail: TODO

### Series continuity
The render reads as part of the same series across episodes —
visual-identity decisions hold against future EP1-EP10 work without
pinning the channel to a single episode's needs. Reusable across
episodes if visual-identity decision lands at channel level (per
`shared/visual_identity_phase1_references/README.md`).
- pass: TODO
- partial: TODO
- fail: TODO

### Production feasibility
The render's vocabulary is reproducible — MJ tool-grammar (or future
GPT Image 2 / Kling expansions) can hit this register reliably with
documented prompts. Not a one-shot lucky generation.
- pass: TODO
- partial: TODO
- fail: TODO

### Sonic-being preservation
The render preserves the channel's sonic-being convention (per channel
staple — held-black-on-editorial-judgment + anchor-without-bed §17).
Visual content doesn't fight or pre-empt the audio-driven editorial
shape. Render is silent-by-default-friendly.
- pass: TODO
- partial: TODO
- fail: TODO
