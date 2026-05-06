# Section 3 Closure — OpenMontage finding + M5 + scope pivot

**Date:** 2026-05-03
**Purpose:** Close Section 3 of the workflow audit with the Q13 OpenMontage finding, M5 (the architectural-boundary meta-finding), and the decision to pivot to v1 spec proposal rather than continue surfacing more findings.

This doc is the third file in the audit series:
1. `workflow_audit_v1.md` — main doc, Sections 1, 2, 4, 5 + findings register
2. `workflow_audit_v1_section3_addendum.md` — Section 3 Q7-Q12, F8-F12, M1-M4, parallel-Claude calibration round
3. `workflow_audit_v1_section3_closure.md` — this doc

---

## Q13 — OpenMontage assembly capability check

**Source:** Joseph asked the audit Claude to verify OpenMontage's editorial assembly capability against his original assumption that it could put together a rough cut. Audit Claude read `README.md`, `PROJECT_CONTEXT.md`, `AGENTS.md`, `config.yaml`, and three relevant pipeline manifests (`cinematic.yaml`, `hybrid.yaml`, `documentary-montage.yaml`) directly from filesystem. Parallel Claude weighed in on the resulting framing with three sharpenings; this doc banks the final framing.

### What OpenMontage actually does

OpenMontage is a real, production-grade AI video assembly system. The README's demo videos (Signal From Tomorrow, Last Banana, VOID, Ghibli-style shorts) are real outputs produced by real pipelines. The capability Joseph originally relied on is genuine.

**What works for assembly:**

- 12 production pipelines covering explainers, cinematic, hybrid, documentary montage, talking head, screen demo, podcast repurpose, animation, etc.
- Each pipeline runs `idea/research → proposal → script → scene_plan → assets → edit → compose → publish` with stage director skills, schema-validated artifacts, and quality gates.
- The `compose` stage is where Remotion + FFmpeg + audio_mixer + color_grade + video_stitch + video_trimmer + audio_enhance run.
- Quality gates include pre-compose validation (delivery promise, slideshow risk, renderer governance) and post-render self-review (ffprobe validation, frame extraction, audio level analysis, subtitle checks).
- Scored provider selection ranks every tool across 7 dimensions with auditable decision logs.
- Budget governance with estimate-reserve-reconcile flow.

**The architectural mismatch with Latent Systems:**

OpenMontage's pipelines are designed around **agent-driven productions where the agent makes most creative decisions.** The agent reads the pipeline manifest, generates the script, drafts prompts, picks providers, decides cuts, presents for approval at creative decision points. Human is in the loop for approval but not for orchestration.

Latent Systems works inversely. **Joseph makes the decisions; AI executes against his specifications.** Three weeks of compressed iteration has produced 15 channel staples, channel architecture v1.5, EP1 architecture v1.4, voice profile parameter map, vocabulary annex with banked findings, render-craft exemplars, NOTES.md as recipe-authority for shipped sections. The discipline density is several orders of magnitude higher than what OpenMontage's pipelines assume.

### The 95% / 5% framing (parallel Claude calibration)

**Important correction:** OpenMontage isn't misaligned with AI-native video production *generally*. It fits 95% of such work. Latent Systems is in the 5% that operates at unusual discipline density. Joseph didn't pick the wrong tool for AI-native video — he picked a tool that fits the broader pattern and built a project in the unusual tier.

OpenMontage handles assembly. The tool-build provides the layer upstream of assembly that didn't exist yet because most AI-native projects don't reach this discipline tier.

This framing matters because it preserves OpenMontage's value-claim while correctly scoping the tool-build's contribution. The tool-build isn't fixing OpenMontage; it's adding an upstream layer for projects that have outgrown the agent-driven assumption.

### Two options for Latent Systems' use of OpenMontage

**Option A: OpenMontage's compose stage as runtime.**

Bypass OpenMontage's upstream stages (idea, proposal, script, scene_plan, assets, edit). Hand-author schema-valid `edit_decisions` and `asset_manifest` JSON from tool-build's structured data. Invoke just the compose stage. Remotion + FFmpeg + audio_mixer + color_grade execute against the hand-curated inputs and produce a final render with quality gates intact.

**Option B: Custom Latent-Systems pipeline.**

Add a 13th pipeline to `pipeline_defs/` matching Latent Systems' actual workflow. Stage director skills teach the agent to read locked architecture, locked script, hero promotions, validated voice profile, and assemble within those constraints.

### Per parallel Claude calibration: A → B is sequenced commitment, not a choice

**v1 ships with Option A explicitly.** Hand-authored OpenMontage-compatible JSON from tool-build's structured data, invoked against the compose stage as runtime.

**v2 considers Option B** AFTER multiple episodes have shipped and patterns of what stage-director skills should encode become extractable from real production data.

Building Option B in v1 is premature optimization. The patterns that would justify a custom pipeline don't exist yet — they emerge from doing the work, not from theorizing about it. Option A produces the work; the patterns surface; v2 codifies them.

**v1 spec commits to Option A.** This resolves the ambiguity and gives v1 a concrete handoff target.

### Friction finding F13: Editorial assembly is a solved problem at the OpenMontage layer; the gap is the upstream-of-compose hand-off

**Severity: HIGH (architectural; resolves rather than creates friction).**

This finding is unusual in the register because it does NOT identify new friction to address in v1. It identifies that **the perceived editorial-assembly gap is a perceived gap, not an actual one.** OpenMontage's compose stage is real, validated, and capable of producing finished video from hand-authored inputs.

The actual gap that v1 addresses is **producing the structurally-disciplined inputs that match OpenMontage's existing artifact schemas.** That's what F1-F12 and M1-M4 are all naming at different layers.

**v1 implication:**

1. **Section 5 (out-of-scope) gets sharpened.** Editorial assembly stays out of v1 scope, but for a sharper reason than the original draft. Not "Remotion already does this" — the sharper reason is *"OpenMontage's compose stage handles assembly; v1's job is producing structurally-disciplined inputs that match OpenMontage's existing artifact schemas."* That's a structural reason, not a punt.

2. **F12's doc-set data model has an active design constraint** (parallel Claude sharpening). The doc-set structure should align with OpenMontage's `edit_decisions` and `asset_manifest` schemas where possible, so serialization at handoff time is mechanical rather than translation-heavy. This isn't a "downstream consumer exists somewhere" framing — it's an active constraint that shapes how v1's data model gets designed.

3. **Routing handoff sharpens to per-stage event** (parallel Claude sharpening). Originally vague "routing handoff" in the v1 spine. Sharpened: NOTES.md-completion event (per channel staple #11) triggers serialization. App surfaces "section X is NOTES.md-complete; ready to serialize" as an action. The handoff happens section-by-section at the natural completion boundary, not at some monolithic "ship the episode" moment.

4. **Tool-build doesn't need editorial-tool-agnosticism.** Latent Systems lives inside OpenMontage's parent directory. OpenMontage IS the editorial layer by construction. v1 doesn't think about Premiere/Resolve/Final Cut Pro/etc. compatibility. That simplifies the spec considerably — one downstream consumer with a known schema, not N downstream consumers requiring an abstract export format.

### Friction finding M5: OpenMontage / tool-build boundary defines v1 scope cleanly

**Severity: HIGH (structural scope insight).**

The tool-build owns everything **upstream of compose.** OpenMontage owns **compose and render.** Integration is JSON: tool-build's structured data serializes into OpenMontage-compatible `edit_decisions` and `asset_manifest`.

This boundary provides a **concrete scope-test for v1:** any proposed feature that duplicates compose-stage capability is out-of-scope. Any proposed feature that produces or maintains structural discipline upstream of compose is in-scope. Any proposed feature that captures relationships between artifacts (per M4) is in-scope. The test is structural rather than judgment-call.

**Why M5 deserves status as a separate finding from F13:**

F13 is about the OpenMontage capability and the integration. M5 is about what that capability/integration implies for v1's scope discipline going forward. F13 names the architecture; M5 names the discipline that derives from the architecture.

Examples of how M5 resolves scope ambiguity:

- "Should v1 have its own video preview?" — No. Preview is compose-stage capability. v1 hands off and OpenMontage previews/renders.
- "Should v1 have its own audio mixing?" — No. Audio mixing is compose-stage capability.
- "Should v1 have its own asset retrieval?" — Maybe. If tool-build's role is upstream curation, asset retrieval might be in-scope (the tool-build needs to know about candidate renders to curate). But the *retrieval* lives upstream; the *use* of retrieved assets lives in OpenMontage.
- "Should v1 have its own NOTES.md template authoring?" — Yes. NOTES.md is upstream-of-compose; it's a relationship-layer artifact (per M4 and F12) that informs but doesn't execute editorial decisions.
- "Should v1 have its own Claude API call for prompt drafting?" — Yes. Per F3 sharpening; this is upstream-of-generation, well upstream of compose.
- "Should v1 do its own rendering?" — No. Rendering is compose-stage capability.

This structural scope discipline travels — when v2 surfaces new feature candidates, M5 provides the test.

**v1 implication:**

The v1 spec should explicitly declare the OpenMontage / tool-build boundary as architectural commitment alongside AD-1 (horizontal-slice). Banking as **AD-2: OpenMontage is the editorial layer; tool-build is the structural-discipline layer upstream of compose.**

---

## Decision: pivot to v1 spec proposal

Per parallel Claude's recommendation: synthesis is overdue.

**What's in the audit register so far:**

- 13 friction findings (F1-F13)
- 5 meta-findings (M1-M5)
- 2 architectural decisions (AD-1: horizontal-slice; AD-2: OpenMontage boundary)
- 1 design principle (discipline-aware AND discipline-tolerant, from F10)
- 1 explicit non-finding (Q10: manifest regen trigger)
- 1 v1 spine shape (concept browser → prompt drafting → batch tracking → audit viewer with rubric + AI-assist → verdict capture → routing handoff → OpenMontage)

**What's NOT yet in the register:**

- Q14+ (cross-document synthesis was Q12; editorial assembly was Q13; remaining post-routing questions like memory/handoff are partially covered by F5)
- All of Section 4 (cross-cutting concerns)

**Why pivot now:**

Q14+ findings would be M4 instances at additional scales (relationships at additional layers). The architectural shape is in. F1-F13 + M1-M5 + AD-1 + AD-2 + the design principle + the v1 spine produce enough material to draft a coherent v1 spec.

If completeness is preferred over speed-to-buildable, the audit can resume after the v1 spec draft to verify the spec covers the work. The findings register holds the work either way.

**Decision: pivot to v1 spec proposal.**

Section 3 closes here. Section 4 deferred. v1 spec proposal becomes the next deliverable.

---

## Status update

- Section 1 (already-handled): COMPLETE
- Section 2 (pre-Downloads): COMPLETE — F1-F7 + AD-1
- Section 3 (post-routing): CLOSED via this doc — F8-F13 + M1-M5 + Q10 non-finding + AD-2
- Section 4 (cross-cutting): DEFERRED — to be resumed if v1 spec proposal surfaces gaps
- Section 5 (out-of-scope): DRAFT pending v1 spec proposal validation
- Friction Findings Register: 13 findings + 5 meta-findings (18 total entries)
- Architectural Decisions Register: 2 decisions (AD-1, AD-2)

**Next:** v1 spec proposal at `tool_build/v1_spec_proposal.md`.
