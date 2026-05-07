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
  3. Verify the file parses cleanly:
     ```python
     from rubric import parse_rubric_file
     parse_rubric_file('projects/latent_systems/docs/AUDIT_RUBRICS_v1_0.md')
     ```
     Should return the parsed dict without raising RubricParseError.
  4. Once parsing passes, `POST /audit/render/{id}/consult` will fire
     against the rubric. Phase 2 acceptance bridge per PHASE_2_E2E_PLAN.md
     unblocks.

**Scope note:** v1.0 ships flat criterion list applying to all 5
concept types listed in front-matter (per `phase2_design_notes.md` §4
"Per-concept-type criteria scope deferred"). If a criterion needs to
scope to a single concept type later, add `concept_types_filter: [...]`
to that criterion's body — handled by Phase 2.5+ rubric parser
extension.

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

---

# Per-direction notes (NOT part of parsed criteria)

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
`### Per direction: <type>` H3 sections below this comment line; the
parser ignores text outside front-matter + H3 headings, so the table
above is invisible to AI consultation. Once added, drop the "(NOT
part of parsed criteria)" caveat above this section.

# Authoring tips

- Use the existing canonical examples to anchor pass/partial/fail
  language. "K1 typography" pass. "H#3 Skinner box hero shot" pass.
  Recent _DEPRECATED renders (per `_work/<context>/_DEPRECATED_<reason>/`)
  are partial or fail examples.
- Keep `pass:` / `partial:` / `fail:` bullets to 1-2 sentences each.
  Anthropic vision API gets the full text per criterion; longer than
  ~3 sentences risks dilution.
- The parser is permissive on bullet casing (PASS:, Pass:, pass:
  all match) but strict on H3 anchors (`### Criterion name`).
  H4+ subheadings get folded into the criterion's definition body.
- Test parse early. Run `python -c "from rubric import parse_rubric_file; print(parse_rubric_file('docs/AUDIT_RUBRICS_v1_0.md'))"` after each criterion authoring pass.

# After authoring

1. Run `python tool_build/tests/test_rubric.py` to confirm structure.
2. Optionally point the e2e plan at this rubric: PHASE_2_E2E_PLAN.md
   step 6 fires consultation against whatever rubric the loader finds.
3. Bank result in `banked_items.md` per "Phase 2 e2e run YYYY-MM-DD"
   heading once one consultation completes.
