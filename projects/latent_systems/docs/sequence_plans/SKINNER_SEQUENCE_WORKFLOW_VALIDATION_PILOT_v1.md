# Skinner Sequence Workflow Validation Pilot

## Pilot Thesis

Treat the Skinner sequence as a self-contained short film inside Episode 1. If this sequence can achieve the intended tone, visual consistency, factual discipline, app workflow, and generation control, then the production system is validated for the rest of Episode 1 and future Latent Systems episodes.

The Skinner sequence is the right test case because it compresses every hard problem into one controlled unit: historical research, character consistency, apparatus accuracy, analog-to-digital visual metaphor, modern splice-ins, cinematic pacing, and sensitive causal framing. It is small enough to build and revise quickly, but difficult enough that success actually means something.

## Definition of Success

The pilot succeeds if the Skinner sequence proves four things at once:

| Validation area | What must be proven | Pass condition |
| --- | --- | --- |
| Creative control | The sequence feels like a premium short film, not a collection of AI clips. | A viewer can describe the visual language after one watch: restrained, dark, analog, psychological, modern-device mirror motif. |
| Consistency | Characters, props, lighting, color, and visual grammar remain stable across shots. | Young Skinner, apparatus, lab atmosphere, and modern phone inserts feel like one designed sequence. |
| Factual discipline | The sequence is dramatic without making false claims. | No shot or narration implies that Skinner invented apps, infinite scroll, or smartphone addiction. |
| Workflow validation | The app, Perplexity, Claude, ComfyUI, and Higgsfield each play a clear role. | Every approved shot has linked research, prompt constraints, generation metadata, review status, and final asset approval. |

## Pilot Scope

### Runtime Target

The Skinner short-film sequence should be designed as a 90-180 second internal film. It does not need to include the full Episode 1 arc. Its purpose is to establish the behavioral loop, make the analogy to modern addiction visible, and prove the production workflow.

### Core Story

The short film is not “Skinner created the modern internet.” It is:

> A pattern becomes visible in a controlled room: action, reward, repetition, measurement. Decades later, the same behavioral logic appears in the cold glow of a phone.

### Required Emotional Arc

1. **Curiosity**: A quiet, almost mundane laboratory action begins.
2. **Pattern**: Repetition becomes visible through apparatus, paper trace, and timing.
3. **Pressure**: The human observer and the machine start to feel morally charged.
4. **Mirror**: The lab gesture rhymes with the modern scroll gesture.
5. **Implication**: The viewer understands the bridge without the sequence overstating causality.

## Short-Film Structure

### Act One: The Hook

| Beat | Visual | Tool route | App requirement |
| --- | --- | --- | --- |
| Phone glow in darkness | Thumb scroll, abstract non-branded feed, face edge lit by blue light | Higgsfield for motion tests, ComfyUI for locked still style | ShotCard with modern-behavior risk note |
| Held black | Sound and narration carry the gap | Editor | Beat marked as editorial-only |
| Thesis line | “This is not where infinite scroll began. But it is where a pattern became visible.” | Script / editor | ClaimCheck required |

### Act Two: The Room

| Beat | Visual | Tool route | App requirement |
| --- | --- | --- | --- |
| Young Skinner established | Young, slim, clean-shaven, dark suit, white shirt, tie, no lab coat | ComfyUI-first | Character consistency pack required |
| Apparatus hero | Hand-built electromechanical box, lever, food magazine, wood, brass, wire | ComfyUI-first | Apparatus research card required |
| Rate trace / paper data | Behavior becoming line, rhythm, measurement | Programmatic or ComfyUI composite | Exactness check required if trace is readable |

### Act Three: The Loop

| Beat | Visual | Tool route | App requirement |
| --- | --- | --- | --- |
| Lever action | Small movement, repeatable reward gesture | ComfyUI image-to-video or Higgsfield test | Motion drift review |
| Food / reward insert | Mechanical delivery detail | ComfyUI macro workflow | Prop continuity review |
| Observer watches | Skinner-like figure as witness, not villain | ComfyUI | Tone check: avoid caricature |

### Act Four: The Mirror

| Beat | Visual | Tool route | App requirement |
| --- | --- | --- | --- |
| Thumb scroll | Repeated small gesture echoes lever | Higgsfield for video, ComfyUI for hero still | Modern UI must be abstract and non-branded |
| Apparatus / phone visual rhyme | Split motif or match cut | ComfyUI composition | VisualConstraintSet required |
| Held black | Let implication land | Editor | No generation needed |

### Act Five: The Hand-Off

| Beat | Visual | Tool route | App requirement |
| --- | --- | --- | --- |
| Paper trace becomes modern feed rhythm | Abstract transformation, not literal infographic | Higgsfield or compositing | Causality risk check |
| Final unresolved image | Lab darkness or phone glow | ComfyUI / editor | Approved final frame |
| Transition to larger episode | Sequence exits back into Episode 1 thesis | Editor | Linked to next script beat |

## Workflow Roles

### Perplexity

Perplexity is the truth layer. For this pilot, it must produce and store research cards for Skinner’s appearance, the apparatus, Harvard-era location context, recorder/rate-trace lineage, and the safe modern analogy. It should also run claim checks on every narration line that implies causality.

### Claude / Claude Code / Cowork

Claude is the builder and orchestrator. It should translate shot cards into app tasks, ComfyUI workflow calls, Higgsfield prompts, and review actions. Comfy’s official MCP server supports Claude Desktop, Claude Code, and Cursor connecting to Comfy Cloud via MCP for workflow submission and output retrieval, which makes Claude a viable orchestration layer for Comfy-based generation ([ComfyUI MCP Server](https://docs.comfy.org/development/cloud/mcp-server)).

### ComfyUI

ComfyUI is the consistency engine. It should be responsible for locked character frames, apparatus shots, macro inserts, style transfer, image-to-video consistency tests, and final reusable workflows. The Skinner pilot fails if the final visual identity cannot be reproduced through saved ComfyUI workflows.

### Higgsfield

Higgsfield is the cinematic exploration layer. Higgsfield describes its MCP connector as giving Claude access to many image and video models, routing prompts, handling text/image/sketch/pose/audio/reference inputs, and returning outputs inside the chat workflow ([Higgsfield MCP blog](https://higgsfield.ai/blog/Generate-AI-Videos-From-Claude-with-Higgsfield-MCP)). For the pilot, use Higgsfield to discover camera movement, motion atmosphere, and cinematic variants, then either approve those outputs directly or translate the winning look into ComfyUI for repeatability.

### Unified App

The app is the production memory. It must remember every decision that would otherwise disappear across Perplexity, Claude, ComfyUI, Higgsfield, and the editor: research, prompt, references, workflow JSON, model, seed, asset version, review notes, rejection reasons, approval state, and final export status.

## Required Pilot Deliverables

| Deliverable | Purpose | Required before scale-up? |
| --- | --- | --- |
| Skinner short-film script beat map | Defines sequence structure and timing | Yes |
| Research card set | Grounds all factual and visual choices | Yes |
| Claim-check report | Protects against causality overreach | Yes |
| Young Skinner reference pack | Tests character consistency | Yes |
| Apparatus reference pack | Tests prop consistency | Yes |
| Style frame set | Locks the visual language | Yes |
| ComfyUI workflow set | Proves repeatability | Yes |
| Higgsfield motion test set | Proves cinematic exploration route | Yes |
| Approved shot board | Shows final sequence candidate assets | Yes |
| Rejection log | Shows what failed and how the app learned from it | Yes |
| Edited pilot cut | Final validation artifact | Yes |

## App Requirements Proven by the Pilot

### P0 App Requirements

- Create and store ScriptBeats.
- Create and store ShotCards.
- Attach ResearchCards to ScriptBeats and ShotCards.
- Run ClaimCheck on narration or visual implications.
- Generate VisualConstraintSets from ResearchCards.
- Store PromptVersions.
- Store reference images and reference roles.
- Store ComfyUI workflow metadata.
- Store Higgsfield output metadata.
- Store generated assets with review state.
- Mark assets approved, rejected, or needs revision.
- Export approved assets for edit.

### P1 App Requirements

- Compare candidates side by side.
- Regenerate from the same workflow with altered constraints.
- Track character consistency across shots.
- Track apparatus consistency across shots.
- Convert QA flags into prompt revisions.
- Display a shot-level readiness gate.

### Not Required for Pilot

- Full timeline editor.
- Automated publishing.
- Multi-user collaboration.
- Full Comfy graph editing inside the app.
- Full DAM replacement.
- Automated voiceover sync.

## Validation Gates

### Gate One: Research Lock

Pass if:

- Skinner appearance card is approved.
- Apparatus card is approved.
- Location/environment card is approved.
- Modern analogy card is approved.
- Causality guardrail is approved.

Fail if:

- Any core visual is based only on vibes.
- Any narration line implies direct invention of modern apps.
- Any major visual detail cannot be categorized as verified, safe inference, or creative metaphor.

### Gate Two: Style Frame Lock

Pass if:

- There are 5-8 approved keyframes.
- The keyframes look like one sequence.
- The Young Skinner frame is period-plausible.
- The apparatus frame is tactile and historically grounded.
- The modern phone frame visually rhymes with the lab loop without showing real app brands.

Fail if:

- Outputs look like separate AI generations.
- Skinner changes age, wardrobe, or facial structure across frames.
- Apparatus becomes generic sci-fi, steampunk, or modern lab equipment.

### Gate Three: Workflow Repeatability

Pass if:

- At least three shot families can be regenerated through saved workflows.
- New candidates preserve the approved style pack.
- Prompt changes produce controlled variation rather than total drift.
- Workflow metadata is stored in the app.

Fail if:

- The best outputs are lucky one-offs.
- Re-running the workflow loses the character or apparatus.
- The app cannot tell which prompt/workflow produced which output.

### Gate Four: Motion Viability

Pass if:

- Higgsfield produces usable cinematic motion tests.
- ComfyUI or Comfy-style workflows can preserve core still-frame identity for controlled shots.
- Motion clips do not break the established character, prop, or tone.

Fail if:

- Motion causes face drift, prop drift, or style collapse.
- Camera movement feels generic or too flashy.
- Clips cannot be cut together into one coherent sequence.

### Gate Five: Edited Pilot Cut

Pass if:

- The sequence works as a standalone short film.
- The analogy is clear without being over-explained.
- A viewer understands the behavioral loop.
- The final cut has no obvious AI slop, period-breaking artifacts, or unsupported claims.
- The app contains the full audit trail for every approved visual.

Fail if:

- The sequence only works when explained outside the cut.
- The visuals are impressive but inconsistent.
- The app did not reduce chaos or improve repeatability.
- The pipeline feels slower than manual prompting without producing better control.

## Pilot Metrics

### Creative Metrics

| Metric | Target |
| --- | --- |
| Approved style frames | 5-8 |
| Shot families tested | At least 5 |
| Viewer comprehension | 80% of test viewers can explain the behavioral loop without extra explanation |
| Visual identity recall | 80% of test viewers describe the look with similar language |

### Consistency Metrics

| Metric | Target |
| --- | --- |
| Character consistency pass rate | 80%+ after workflow lock |
| Apparatus consistency pass rate | 80%+ after workflow lock |
| Prompt-to-output controllability | 70%+ of revisions move in the intended direction |
| Lucky one-off dependency | No approved shot should be impossible to trace back to prompt/workflow metadata |

### Research and QA Metrics

| Metric | Target |
| --- | --- |
| Research coverage | 100% of factual visual beats have linked ResearchCards |
| Claim check coverage | 100% of causality-sensitive narration lines checked |
| Unsupported claims in final cut | 0 |
| Visual anachronism issues in final review | 0 unresolved P0 issues |

### App Workflow Metrics

| Metric | Target |
| --- | --- |
| Approved assets with metadata | 100% |
| Rejected assets with rejection reason | 75%+ |
| Shots passing readiness gate before generation | 90%+ |
| Manual searching across chat/tool history | Should decrease after app workflow is used |

## Pilot Production Plan

### Day One: Short-Film Beat Map

- Define the 90-180 second Skinner short-film structure.
- Lock narration beats.
- Identify all factual claims.
- Create initial ShotCards.
- Create initial ResearchCards.

### Day Two: Research and Constraint Lock

- Approve or revise ResearchCards.
- Run ClaimChecks.
- Generate VisualConstraintSets.
- Build Young Skinner, Apparatus, and Style reference packs.

### Day Three: Look Discovery

- Use Higgsfield for fast cinematic exploration.
- Use ComfyUI for controlled still-frame exploration.
- Select 5-8 keyframes.
- Reject anything visually impressive but historically wrong.

### Day Four: Workflow Build

- Build ComfyUI workflows for character, apparatus, macro inserts, modern phone inserts, and final polish.
- Store workflow JSON and metadata.
- Run repeatability tests.

### Day Five: Motion Tests

- Test Higgsfield motion for phone, lab atmosphere, and match-cut moments.
- Test ComfyUI image-to-video or equivalent controlled motion for high-consistency shots.
- Reject motion that breaks face, prop, or tone.

### Day Six: Assembly Cut

- Assemble the Skinner short-film pilot.
- Add VO, sound, held-black moments, and temporary grade.
- Identify missing shots only after watching the cut.

### Day Seven: Validation Review

- Run viewer test with 5-10 people.
- Track comprehension, visual identity recall, and perceived quality.
- Review the app audit trail.
- Decide whether to scale the workflow to the rest of Episode 1.

## Scale-Up Decision

### Green Light

Scale the workflow if:

- The edited Skinner pilot feels like a coherent short film.
- ComfyUI produces repeatable style and character control.
- Higgsfield meaningfully accelerates motion exploration.
- Perplexity prevents factual and visual drift.
- The app reduces chaos and preserves decisions.

### Yellow Light

Continue iterating before scaling if:

- The concept works but consistency is still unstable.
- The app captures metadata but the workflow is too slow.
- Higgsfield outputs look good but are hard to integrate with ComfyUI.
- Research cards exist but are not influencing prompts strongly enough.

### Red Light

Do not scale yet if:

- The best shots are disconnected lucky outputs.
- The app becomes overhead instead of leverage.
- Skinner or apparatus consistency cannot be controlled.
- The sequence implies false causality.
- The final cut looks like generic AI documentary B-roll.

## Final Recommendation

Use the Skinner sequence as the validation pilot before committing the full episode to the new production stack. The goal is not just to make one good sequence. The goal is to prove that the system can repeatedly convert research into precise, consistent, cinematic assets while preserving the audit trail inside the app.

If the Skinner short film works, the rest of Episode 1 becomes an expansion problem. If it does not work, the failure will reveal exactly which layer is weak: research grounding, app structure, ComfyUI consistency, Higgsfield motion, Claude orchestration, or editorial assembly.
