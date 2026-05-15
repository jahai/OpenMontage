# Episode 1 Visual Production Bible

## Executive Summary

Episode 1 should be built with a hybrid production system: Perplexity for research, factual guardrails, prompt packs, and continuity QA; Claude and the unified app for orchestration; ComfyUI as the consistency and exact-control layer; and Higgsfield as the fast cinematic image/video model router. The main correction to the working assumption is favorable: Claude can integrate with ComfyUI, but the cleanest production path depends on whether the project uses Comfy Cloud MCP, a local ComfyUI MCP bridge, or direct ComfyUI API submission from the unified app. Comfy’s official MCP server connects Claude Desktop, Claude Code, and Cursor to Comfy Cloud, allowing agents to submit ComfyUI API-format workflows, upload inputs, check status, retrieve outputs, and reuse previous outputs on cloud GPUs ([ComfyUI MCP Server](https://docs.comfy.org/development/cloud/mcp-server)). Community local MCP servers also exist for Claude Desktop controlling a local ComfyUI instance, but those require local ComfyUI, Node/Python setup, path configuration, and more maintenance than the official cloud route ([ComfyUI MCP Server by Nikolaibibo](https://glama.ai/mcp/servers/@Nikolaibibo/claude-comfyui-mcp)).

The strategic answer is yes: build the app while creating episode 1, because the episode will reveal the actual product requirements better than abstract planning. The trap to avoid is building a “unified app” that tries to replace ComfyUI or Higgsfield too early. The app should begin as a production operating system: script, research cards, asset registry, shot board, prompt/version tracking, model routing, review states, and final asset approval. ComfyUI should remain the deterministic visual engine for repeatable looks, characters, and workflows, while Higgsfield should remain the fast exploration and cinematic motion layer.

## Creative North Star

The target is a “Black Mirror meets documentary” visual language: primary-source-grounded, moody, restrained, morally charged, and intentionally anti-generic. The Skinner sequence should feel like analog science becoming a modern behavioral machine, not like a literal claim that Skinner invented infinite scroll. The strongest phrase for the thesis remains:

> “This is not where infinite scroll began. But it is where a pattern became visible.”

The benchmark is “Gossip Goblin-level control,” meaning the system must produce repeatable characters, exact shot grammar, precise props, consistent palette, controlled camera language, and a style that does not drift every time a new prompt is run. That requires more than text prompting. It requires a visual bible, reference management, seed/workflow tracking, reusable ComfyUI graphs, and a shot-level QA loop.

## Integration Reality Check

| Question | Answer | Production implication |
| --- | --- | --- |
| Can Claude integrate with ComfyUI? | Yes. Comfy’s official MCP server connects AI assistants including Claude Desktop, Claude Code, and Cursor to Comfy Cloud via MCP ([ComfyUI MCP Server](https://docs.comfy.org/development/cloud/mcp-server)). | Claude can orchestrate Comfy workflows without you manually clicking through every run. |
| Can Claude Code work with Comfy workflows? | Yes. Comfy’s MCP documentation includes a Claude Code setup command using the hosted MCP endpoint and an API key ([ComfyUI MCP Server](https://docs.comfy.org/development/cloud/mcp-server)). | Claude Code can become the implementation/orchestration assistant for the unified app and Comfy workflow calls. |
| Can Claude run local ComfyUI? | Yes, but generally through community MCP bridges or custom API wrappers, not the same low-friction official cloud route. Community projects describe Claude Desktop controlling a local ComfyUI installation, including model listing, workflow submission, upload/retrieval, and queue management ([ComfyUI MCP Server by Nikolaibibo](https://glama.ai/mcp/servers/@Nikolaibibo/claude-comfyui-mcp)). | Local control is possible but should be treated as a second-phase setup unless local GPU, privacy, or model ownership is essential. |
| Can Claude be inside ComfyUI workflows? | Yes. Comfy’s Anthropic Claude API node supports text and multimodal inputs inside Comfy workflows, including up to 20 images per request according to Comfy’s partner-node documentation ([Anthropic Claude API Node ComfyUI Official Example](https://docs.comfy.org/tutorials/partner-nodes/anthropic/claude)). | Claude can analyze references or generate prompt text inside a graph, but this is different from Claude orchestrating Comfy from outside. |
| Where does Higgsfield fit? | Higgsfield says its MCP connector gives Claude access to 30+ video and image models, with Claude routing prompts, choosing models, generating from text/images/sketches/pose/audio/reference footage, and returning outputs in chat ([Higgsfield MCP blog](https://higgsfield.ai/blog/Generate-AI-Videos-From-Claude-with-Higgsfield-MCP)). | Use Higgsfield for rapid model comparison, cinematic clips, camera tests, and shots where speed beats deterministic repeatability. |

## Recommended System Architecture

### Layered Workflow

| Layer | Primary tool | Job | Why it matters |
| --- | --- | --- | --- |
| Research and truth | Perplexity | Primary-source research, factual constraints, quote verification, anachronism checks, shot brief writing | Prevents the visuals from becoming impressive but false. |
| Creative orchestration | Claude / Claude Code / Cowork | Turns briefs into workflows, writes app code, calls MCP tools, manages iteration | Keeps the workflow conversational while still structured. |
| Control and consistency | ComfyUI | Reusable image/video workflows, character references, ControlNet/IP-adapter-style guidance, LoRAs, seed management, exact graph reuse | This is the layer that gets you closer to exact repeatable outputs. |
| Cinematic exploration | Higgsfield MCP | Fast model routing, motion shots, short cinematic clips, reference-driven video tests | Gives fast high-end options without spending all day tuning nodes. |
| Production OS | Unified app | Script, research cards, shot board, prompt history, asset registry, model/workflow metadata, approvals | This is the product you are discovering while making episode 1. |
| Editing and finishing | NLE / editor | Assembly, sound, typography, pacing, final grade | AI generation should not be expected to solve final editorial judgment. |

### Core Principle

The unified app should not try to be “ComfyUI but simpler” at first. It should be the connective tissue between research, script, shots, prompts, workflows, renders, and approvals. ComfyUI should remain the specialized graph engine, while the app stores and reuses the exact workflow JSON, seed, model, LoRA, reference inputs, prompt text, negative constraints, output, status, and editorial notes.

## Episode 1 Visual Rules

### Skinner Character Rules

- Skinner should appear young, slim, clean-shaven, and formal.
- Default wardrobe should be dark suit, white shirt, and tie.
- Avoid lab coat unless a specific scene is intentionally symbolic rather than historical.
- Avoid older, balding, late-career Skinner for the 1928-1936 sequence.
- Avoid glasses unless a verified reference for the specific period supports them.
- Use the April 1933 Bettmann/Getty portrait and the January 1931 B.F. Skinner Foundation lead as the strongest facial/wardrobe reference anchors.

### Apparatus Rules

- The apparatus should feel hand-built, tactile, electromechanical, and improvised.
- Use wood, brass, wire, relays, solenoids, levers, food magazine details, paper rolls, and recorder mechanisms.
- The recorder should be treated as kymograph-derived / rate-recorder lineage, not an Esterline-Angus paper-tape recorder.
- Avoid clean modern lab equipment, digital screens, modern plastic housings, modern LED displays, or sci-fi lab props.

### Environment Rules

- Use Harvard psychology / Boylston Hall / Emerson Hall institutional context rather than Memorial Hall basement for this era.
- Keep lighting conservative and period-plausible.
- Avoid fluorescent-modern lighting, overly dramatic fake window shafts, and obvious modern lab surfaces.
- The lab should feel like a workshop-science space, not a glossy biotechnology set.

### Modern Continuity Rules

- Modern splice-ins should show behavioral continuity: phone taps, infinite scroll, notification loops, reward anticipation, micro-friction, and repetitive thumb motion.
- Do not imply Skinner invented apps, infinite scroll, social media, or smartphone addiction.
- The visual bridge is pattern, not direct causation.

## Shot System for the Skinner Sequence

| Shot family | Purpose | Best tool route | Consistency method |
| --- | --- | --- | --- |
| Phone-glow micro-tease | First 0-12 second YouTube hook | Higgsfield for fast motion tests; ComfyUI for final repeatable frame style | Store approved phone/reflection look as reference image and reuse in app. |
| Young Skinner portrait shots | Establish human subject and period | ComfyUI first; Higgsfield only for cinematic variants | Use fixed character reference set, seed bands, face reference, wardrobe prompt, and negative constraints. |
| Apparatus close-ups | Establish behavioral machine | ComfyUI | Reusable prop workflow, macro lens style, material palette, exact prop constraints. |
| Lever / food magazine / rat loop | Show reinforcement loop without over-explaining | ComfyUI for stills; Higgsfield or Comfy video workflow for motion | Fixed apparatus layout, repeated camera angles, storyboarded timing. |
| Paper trace / rate recorder | Visualize behavior becoming data | ComfyUI or programmatic graphic if text/line accuracy matters | If exact trace matters, generate programmatically and composite, not pure image AI. |
| Modern thumb-scroll inserts | Bridge past to present | Higgsfield for motion, ComfyUI for exact stills | Same color grade and lens language as lab shots, but colder phone glow. |
| Mirror motif | Tie analog lab to modern device loop | ComfyUI for exact composition | Reference composition image, locked aspect ratio, fixed negative constraints. |
| Held-black moments | Prestige pacing and tension | Editing layer | Treat as editorial punctuation, not a generated asset. |

## Prompt and Workflow Routing

### Use ComfyUI When

- The same character must appear across multiple shots.
- The same room, apparatus, or prop must recur.
- The output must be tuned through a reusable workflow.
- You need exact seeds, model choices, LoRAs, ControlNet-style guidance, or reference-image conditioning.
- You need to save a graph and re-run it later with small changes.
- You need production consistency more than instant cinematic surprise.

### Use Higgsfield When

- You need quick cinematic video options.
- You want to compare several models without wiring each one manually.
- The shot is atmospheric, transitional, or motion-first.
- You are still discovering the look.
- The asset can tolerate some variation or will be used as inspiration for a ComfyUI final.

### Use Perplexity When

- A scene includes historical detail, factual claim, quote, period wardrobe, location, apparatus, or causality.
- A prompt needs anti-hallucination constraints.
- A visual should be checked for anachronisms.
- A shot needs a research card attached before generation.

### Use Claude / Claude Code When

- You need to convert a shot brief into Comfy workflow parameters.
- You need to automate uploads, job submissions, polling, and retrieval.
- You need to build or modify the unified app.
- You need to connect ComfyUI, Higgsfield, local files, and the asset database.

## The App You Should Build While Making Episode 1

### Minimum Useful Version

The first version should have six objects:

| Object | Fields it should store |
| --- | --- |
| Research card | Claim, source URL, quote/excerpt, confidence, related script beat, visual implications, forbidden implications |
| Script beat | Timestamp range, narration text, emotional function, required visuals, factual constraints |
| Shot card | Shot family, composition, prompt, avoid list, references, aspect ratio, tool route, status |
| Asset | File, thumbnail, generation tool, model, seed, workflow ID, prompt version, references used, approval status |
| Workflow | Tool, workflow JSON, node dependencies, model files, parameters, notes, output examples |
| Review note | Issue type, factual risk, visual drift, continuity issue, edit decision, next action |

### Status Pipeline

Use a production status flow that matches real creative work:

1. Research needed
2. Research cleared
3. Prompt drafted
4. Test generated
5. Candidate selected
6. Consistency pass
7. Factual QA
8. Editorial approved
9. Locked for edit

### App Features Episode 1 Will Immediately Need

- Shot board with thumbnails and status.
- Prompt version history.
- Reference image library.
- Comfy workflow JSON storage.
- Higgsfield output import.
- Seed and model metadata.
- “Approved look” tagging.
- Factual risk flags.
- Character consistency tracker.
- Apparatus consistency tracker.
- Exportable shot list for editor.
- One-click “regenerate with same workflow but new prompt detail.”

### Later Features Not Needed on Day One

- Full timeline editor.
- Multi-user permissions.
- Automated voiceover-to-shot synchronization.
- Full Comfy graph editor inside the app.
- Automated YouTube upload.
- Full DAM replacement.

Those can wait. Episode 1 should drive the feature list through friction, not speculative architecture.

## Consistency System

### Character Consistency Pack

Create one approved “Young Skinner Pack”:

- 3-5 approved face/wardrobe reference stills.
- One neutral front three-quarter portrait.
- One side/profile reference.
- One seated-at-apparatus composition.
- One negative reference sheet showing what not to do: old Skinner, lab coat, bald head, glasses, modern professor look.
- One locked descriptive prompt.
- One avoid list.
- One preferred aspect ratio per use case.

### Apparatus Consistency Pack

Create one approved “Operant Apparatus Pack”:

- Main apparatus hero still.
- Lever close-up.
- Food magazine close-up.
- Relay/wire detail shot.
- Paper trace / recorder shot.
- Diagram or simplified production-design note.
- Anti-pattern sheet: plastic, LED, modern lab, incorrect recorder, sci-fi enclosure.

### Style Consistency Pack

Create one approved “Latent Systems Episode 1 Look Pack”:

- Color palette: deep blacks, warm tungsten/wood/brass, cold phone blue, restrained highlights.
- Camera language: macro inserts, slow push-ins, static symmetrical frames, shallow but not fake depth of field.
- Texture: grain, tactile materials, archival softness without fake damage.
- Motion: controlled, quiet, pressure-building, minimal gimmick transitions.
- Typography: sober, documentary-grade, used sparingly.

## Generation Playbook

### Phase 1: Look Discovery

Use Higgsfield and quick Comfy runs to create 20-40 rough candidates across the main shot families. The goal is not final assets. The goal is to find the strongest visual language fast.

### Phase 2: Lock the Style

Choose 5-8 keyframes:

- Phone-glow opening frame.
- Young Skinner portrait.
- Apparatus hero shot.
- Lever close-up.
- Paper trace / recorder shot.
- Modern infinite-scroll insert.
- Mirror motif frame.
- Closing image for the sequence.

These become the reference spine for every later run.

### Phase 3: Build ComfyUI Workflows

Convert the selected look into reusable ComfyUI workflows:

- Character still workflow.
- Apparatus macro workflow.
- Modern phone insert workflow.
- Image-to-video workflow for subtle motion.
- Upscale/final polish workflow.
- Optional style-transfer workflow for bringing Higgsfield concepts into the locked look.

### Phase 4: Generate Shot Candidates

Generate 3-6 candidates per shot. Do not chase perfection one prompt at a time. Batch variants, compare visually, then tighten.

### Phase 5: QA and Lock

Every approved asset needs:

- Factual pass.
- Character consistency pass.
- Apparatus consistency pass.
- Style pass.
- Editorial function pass.
- Metadata saved in the app.

## Example Prompt Templates

### Young Skinner Establishing Still

Create a restrained 1930s Harvard psychology laboratory documentary still of a young, slim, clean-shaven B.F. Skinner-like behavioral scientist seated beside a hand-built operant apparatus. He wears a dark period suit, white shirt, and tie, no lab coat, no glasses. The room feels institutional and modest, with wood, brass, paper, wires, relays, and a workshop-science atmosphere. Composition is quiet and tense, like a prestige historical documentary: three-quarter view, controlled shadows, conservative period lighting, shallow but natural depth of field, tactile analog textures, restrained grain. The apparatus includes a lever, food magazine, wiring, solenoid/relay details, and a paper recording mechanism inspired by kymograph/rate-recorder lineage. Avoid modern laboratory equipment, LED displays, plastic enclosures, fluorescent light, old/bald Skinner, sci-fi styling, and exaggerated cinematic smoke.

### Apparatus Macro Still

Create a macro documentary close-up of a hand-built 1930s behavioral experiment apparatus: a small lever, food magazine opening, brass screws, dark wood, exposed wire, relay/solenoid detail, and paper recording mechanism nearby. The image should feel tactile, improvised, and historically grounded, as if analog behavior is being translated into data. Use warm tungsten highlights, deep shadows, restrained grain, and a quiet ominous composition. Avoid modern electronics, LEDs, acrylic, digital screens, sleek lab equipment, science-fiction panels, and generic steampunk ornamentation.

### Modern Behavioral Continuity Insert

Create a dark, restrained close-up of a hand holding a smartphone in bed or in a dim room, thumb repeating a vertical scrolling motion. The screen glow reflects faintly on the fingers and face edge, but the interface is abstract and non-branded. The mood is quiet, compulsive, and observational, not sensational. Composition should visually echo a lab lever: small repeated motion, reward anticipation, controlled darkness, cold blue light, shallow depth of field. Avoid readable app names, real logos, fake social media UI, melodrama, horror clichés, and exaggerated addiction imagery.

### Mirror Motif Frame

Create a composed split-motif documentary image where a 1930s apparatus lever and a modern smartphone scroll gesture visually rhyme through shape and motion. The image should not imply direct invention or causation; it should suggest a behavioral pattern becoming visible across time. Keep the frame minimal, elegant, dark, and analog-to-digital: warm brass/wood on one side, cold phone glow on the other, with a quiet central negative space. Avoid literal arrows, infographics, labels, brand interfaces, or obvious “then vs now” stock imagery.

## Episode 1 Production Schedule

### Day 1: Research-to-Visual Lock

- Finalize Skinner sequence beats.
- Attach research cards to each visual beat.
- Build shot list.
- Create first prompt pack.
- Generate initial visual exploration.

### Day 2: Style Frame Selection

- Pick 5-8 keyframes.
- Build Young Skinner Pack.
- Build Apparatus Pack.
- Build Style Pack.
- Decide which shots are Comfy-first versus Higgsfield-first.

### Day 3: ComfyUI Workflow Build

- Build and test reusable workflows.
- Save exact workflow JSON and metadata.
- Run consistency tests.
- Reject workflows that cannot reproduce the chosen look.

### Day 4: Motion Tests

- Use Higgsfield for cinematic motion candidates.
- Use Comfy image-to-video workflows for controlled subtle motion.
- Compare motion drift, face drift, prop drift, and artifact rate.

### Day 5: Production Batch

- Generate all required Skinner sequence assets.
- Run factual and continuity QA.
- Approve, revise, or reject each asset in the app.

### Day 6: Assembly

- Drop approved assets into the edit.
- Test pacing with voiceover.
- Identify missing inserts.
- Generate only what the edit proves is missing.

### Day 7: Polish and Lock

- Upscale, grade, and finalize.
- Export final shot list, prompt log, and asset metadata.
- Convert lessons learned into app feature requirements.

## Immediate Build Instructions for the Unified App

The app should start as a thin layer over the actual production workflow. Build the database around the artifacts you are already creating, not around hypothetical future users.

### Data Model

```txt
Project
  Episode
    ScriptBeat
      ResearchCard
      ShotCard
        PromptVersion
        GenerationJob
          Asset
        ReviewNote
    Workflow
    ReferencePack
```

### Critical Metadata

Every generated asset should store:

- Prompt text.
- Negative/avoid text.
- Tool used.
- Model used.
- Workflow JSON or job link.
- Seed, if available.
- Reference images used.
- Source shot card.
- Version number.
- Review status.
- Why it was approved or rejected.

### First Automations

1. “Create shot cards from script beat.”
2. “Generate prompt variants from shot card.”
3. “Send to Comfy workflow.”
4. “Send to Higgsfield.”
5. “Import output and metadata.”
6. “Compare candidates side by side.”
7. “Mark approved and lock reference.”
8. “Export approved assets for edit.”

## Recommendation

The strongest path is to build episode 1 and the app together, but keep the architecture honest:

- Perplexity defines the truth layer.
- Claude builds and orchestrates.
- ComfyUI controls consistency.
- Higgsfield accelerates cinematic discovery.
- The app remembers everything.

ComfyUI should not be optional for this project if the goal is exact, repeatable, high-control imagery. Higgsfield can produce impressive shots quickly, but ComfyUI is where the project gets a durable production system. Episode 1 should become the proving ground for the app because every annoying manual step becomes a real feature requirement.
