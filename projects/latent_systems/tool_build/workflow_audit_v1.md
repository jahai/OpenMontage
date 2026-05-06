# LATENT SYSTEMS — Workflow Audit v1

**Date:** 2026-05-03
**Purpose:** Spec for a local desktop app that streamlines the current Latent Systems video production workflow. v1 scope = match what Joseph already does, faster. New capabilities are v2+.
**Build approach:** AI-assisted via Claude Code.
**Build target:** local-only application, single-user, no cloud, plugs into APIs of existing services where available, browser-bridge / clipboard-handoff where not (MJ, GPT Image 2, Kling, ElevenLabs, etc.).

---

## Project context (for downstream interpretation of findings)

**EP1 production started 2026-04-13.** As of audit date (2026-05-03), the project is approximately **three weeks old**. In that span it has produced:

- A canonical filesystem structure with 12+ EP1 section directories, 12 shared/ subdirectories, complete docs/ tree
- 15 channel staples
- Channel architecture v1.0 → v1.4 → v1.5 (three architecture-lock cycles)
- EP1 architecture v1.0 → v1.4
- A working partial-pipeline tool (downloads_router.py + router_config.yaml)
- §17 of 19 sections re-recorded at v1.4 voice profile
- Visual identity Phase 1 references (5 directions explored)
- Visual identity Phase 2 evaluations (5 directions evaluated, walk closed today)
- Render-craft exemplars catalog
- Vocabulary annex with multiple banked findings
- A project briefing v1.3
- Multiple shipped sections at block-level with NOTES.md recipe-authority

**Implication for the audit:** the project is operating at compressed-iteration tempo. Three weeks of production has produced standards, conventions, and channel staples that are *still actively forming*. The discipline-evolution-in-flight pattern (F10) is not slow drift — it is rapid iteration where the standard genuinely changes between Tuesday and Thursday.

This affects how v1 should be designed:

- The app is being built for a project whose *standards are still forming.* Every v1 decision must accommodate the standard advancing during the build.
- "Discipline-aware AND discipline-tolerant" (per F10) is not a nice-to-have; it is the project's actual operating mode.
- Findings about gaps are not findings about negligence — they are findings about discipline that hasn't had time to stabilize. Treating them otherwise produces v1 design that imposes premature rigidity.
- Re-render scope questions, NOTES.md upgrade paths, and architecture-version-tracking are all surfaces of the same underlying reality: this is a project where the standard moves and the artifacts produced before each move stay valid as artifacts of *that* standard.

---

## Framing

The naive framing for this audit was "describe Joseph's workflow from scratch." That's the wrong starting point. The real situation is sharper:

**Joseph's project already has a partial workflow tool.** `tools/downloads_router.py` + `router_config.yaml` is an early version of the thing being designed here. It already handles: pattern recognition for MJ/GPT/Kling output filenames, confidence-tiered routing (HIGH/MEDIUM/LOW/DUPLICATE), hash-based deduplication, audit logging, abort-on-uncommitted-canonical-changes safety, configuration-driven routing rules.

The router is roughly 33% of the pipeline — the **intake-and-routing** slice. The pipeline as a whole has three phases:

1. **Pre-Downloads:** generation work itself. Prompt drafting, MJ session, GPT Image 2 session, Kling session, etc. This is where files are created. Currently happens in browser tabs / desktop apps with no project-level tooling.
2. **Intake-and-routing (currently handled):** files land in `~/Downloads/`, router pattern-matches and routes into canonical project structure with audit log. Already encoded in `router_config.yaml`.
3. **Post-routing:** assembly work. Reference lookup, generation comparison, hero promotion, manifest regeneration, NOTES.md authorship, eventual editorial assembly. Currently happens via PowerShell, git bash, manual file moves, manual prompt construction in chat.

**The app v1 is the missing two-thirds.** It surrounds the existing router rather than replacing it.

This framing matters because:
- It honors what's already built (the router has real discipline encoded; the app should not duplicate it)
- It scopes v1 honestly (don't rebuild what works; address what hurts)
- It reveals the actual friction map — phases 1 and 3 are where Joseph "jumps around between a whole bunch of different apps and git bash and terminal"

---

## Architectural decisions banked during interview

These are commitments that constrain everything downstream. Recorded here for visibility.

### AD-1: Horizontal-slice v1 (per F7 follow-up, 2026-05-03)

Two viable v1 decompositions were considered:
- **Vertical:** Build the full workspace for ONE tool (likely MJ) end-to-end. v1 = MJ-only complete workspace. Add other tools in v2+.
- **Horizontal:** Build the workspace skeleton across all tools at lower fidelity. Concept persistence, prompt drafting, audit, lineage all work for all tools; generation triggering varies by tool (API where available, clipboard-handoff where not).

**Decision: Horizontal.**

Implications:
- For tools with API access (Anthropic, OpenAI / GPT Image 2, ElevenLabs): v1 can fully automate generation triggering.
- For tools without individual-creator API access (MJ, Kling): v1 does NOT automate the generation step. The app drafts the prompt, copies it to clipboard, opens the relevant tool's web UI, and waits for the file to land in `~/Downloads/` — at which point the existing router takes over. This is still a significant improvement over current state because the prompt-output binding (F1) and the lineage-anchoring (F4) both work without API automation.
- API automation for currently-gated tools is a v2+ enhancement that becomes possible if/when those tools open API access.
- This is NOT a compromise — the pain points cluster around capture, persistence, lineage, and workspace coherence (F1-F7), all of which are addressable without API automation. Automation is a nice-to-have that follows from API availability, not a v1 requirement.

**Caveat from parallel-Claude calibration round:** Path B's vulnerable spot is the clipboard handoff. For tools without API access (MJ, Kling), v1 has to make copy-paste-into-browser feel native rather than awkward. If clunky, users route around the app and paste manually like today, at which point the persistent-binding benefit (F1's solve) evaporates because the prompt was never captured. **Prototype-critical to get this right.** See addendum doc for detail.

---

## Section 1: What the existing router currently handles (already-handled)

This section catalogs the slice of the pipeline that's already encoded in `tools/downloads_router.py` + `tools/router_config.yaml`. The app v1 should call into this or wrap it; not rebuild it.

### Source-folder watching
- Detects new files in `~/Downloads/` (Windows path: `C:/Users/josep/Downloads`)
- Cross-platform paths configured for darwin/windows/linux

### Pattern recognition (file-format level)
The router knows three generation-tool output formats:
- **MidJourney:** `nycwillow_<prompt-prefix>_<uuid>_<variant>.png` — extracts concept fragment, UUID, variant suffix (0–3)
- **GPT Image 2:** `ChatGPT Image <date>, HH_MM_SS PM[ (N)].png` — extracts timestamp, browser-duplicate-suffix
- **Kling:** `kling_YYYYMMDD_作品_<prompt-prefix>_<id>_<variant>[__1_].mp4` — extracts date, concept fragment, ID, variant
- **Project docs:** `HANDOFF_*`, `*ARCHITECTURE_v*`, `EP1_*`, `FILESYSTEM_*`, `LATENT_SYSTEMS_*`

### Confidence-tiered routing
- **HIGH:** auto-execute (move + rename + log)
- **MEDIUM:** propose to user, await approval
- **LOW:** auto-route to `_inbox/` for manual review
- **DUPLICATE:** hash-confirmed against canonical/archive — delete from Downloads

### Concept-fragment-to-direction heuristics
The router maps prompt-fragment keywords to canonical destinations. Currently encoded:
- "composite architectural", "Boullée", "brutalist" → Direction 2 (architectural inhabitant)
- "composite cinematic image" → Direction 3 (composite subject)
- "behavioral research observation", "psychology laboratory" → Direction 4 (schematic apparatus)
- "latent space", "particles", "blue-black gradient" → Direction 1 (latent space)
- "rat-with-human-face", "anomalous features" → Direction 5 (surreal subject)

Plus archive rules for Round 5 §4.E (deprecated craft-flat work) and GG register experiment (deprecated register-pivot work), with deprecation-marker assignment per failure mode.

### Hash-based deduplication
- Hash-comparison against: `shared/render_craft_exemplars`, `shared/visual_identity_phase1_references`, `ep1/_work`, `docs`
- Files that hash-match canonical are deleted from Downloads (after destination verification)

### Safety guarantees
- Never deletes files that aren't hash-confirmed duplicates
- Verifies hash at destination before deleting source
- Refuses to run if uncommitted changes in `docs/` or `shared/`
- Always logs every action to `tools/router_log.md`
- Never modifies architectural files
- User-initiated only (never on schedule)

### Configuration-as-data
Routing rules live in YAML, not code. Update path is: edit `router_config.yaml`, bump version, restart router. The discipline note in README is explicit about WHEN to update (new shared/ destination, new `_work/` subdirectory, new generation tool, ambiguous patterns surfacing in `_inbox/` review).

**Implication for v1 app:** the router is the model for how the app should think about discipline. The app extends this pattern outward (to phases 1 and 3) but inherits the discipline (config-as-data, audit logging, hash-verification, refusal-to-run-on-uncommitted-canonical-changes, user-initiated only).

---

## Section 2: What happens BEFORE Downloads (pre-routing — COMPLETE)

### Q1 — Where does the prompt come from?

**Confirmed via interview 2026-05-03:**

- Prompts originate in conversation with Claude (web chat or Desktop). They are drafted iteratively, often as a back-and-forth with diagnostic flags ("Flag 1: register-relativity," "Flag 2: MJ schematic-precision weakness," etc.) before a final version is settled.
- Once a prompt is final, Joseph **manually copy-pastes** it from the chat into the target generation tool (MJ web UI, GPT, Kling, etc.).
- Prompts are **NOT saved to filesystem** before generation. Not in any directory. Not in any NOTES.md. Not in a prompts/ directory (no such directory exists at project root or within ep1/).
- After generation, the prompt itself is **not co-located with its output renders**. The renders land in canonical structure under `shared/visual_identity_phase2_evaluations/<direction>/run_<date>/` or equivalent, but no `*_prompt.txt` or similar sits alongside.
- Prompt recovery path: scroll back through Claude chat history, or ask Claude to reprint the prompt. There is no project-filesystem path to recover a prompt-for-render.

**Cross-check with NOTES.md as recipe-authority:**

NOTES.md is real and well-structured (see `ep1/h3_skinner/NOTES.md` as canonical example). It captures: what shipped, why, deviations from convention, pending work, do-not-touch boundaries, source-file mapping. It does **not** capture the generation prompts that produced the source files. References to "shot spec" point to the handoff doc; the actual prompt text lives in the handoff or in chat history.

So the gap is system-wide, not just a Phase 2 oversight: across EP1's shipped material (produced over the project's three-week lifespan), the prompts that produced canonical sources are not durably co-located with those sources.

### Q2 — Multi-tool generation

**Confirmed via interview 2026-05-03:**

The pattern across the project has been: **per-tool prompts are independently drafted** (via collaboration with Claude), not derived from a shared template. The thesis-image work was an exception — the GPT Image 2 attempt reused the MJ option-2 prompt verbatim because GPT was used as a fallback after MJ already landed, and at that point the concept had collapsed *into* the MJ prompt.

For everything else (D4 spread, Kling motion tests, Phase 1 reference batches, etc.), Claude has been drafting tool-specific prompts based on the concept and the target tool's grammar. The MJ versions use `--ar 16:9 --v 7` and lens specifications. The Kling versions use motion vocabulary that doesn't apply to stills. Etc.

This means there's an implicit "concept" object — the meta-thing prior to any single prompt that holds shared intent across a multi-prompt or multi-tool spread — that currently lives only in Claude's conversational state.

### Q2-followup — Concept persistence and tool-grammar locus

**Confirmed via interview 2026-05-03:**

- **Does the concept survive across sessions?** No. Each session re-derives the concept from canonical docs (briefing, handoff, architecture). The chat-state version dies when the chat ends. Re-derivation is real warm-up tax at the start of each session and is part of why handoff docs need to be substantial.
- **Who holds tool-grammar knowledge?** Claude. The translation from concept to tool-specific prompt is happening in Claude's head based on what Claude knows about MJ syntax, GPT instruction-following, Kling motion vocabulary, etc. The project files do not capture this knowledge as data.
- **Joseph's preferred locus for tool-grammar knowledge in v1:** in the model the app calls. The app sends `(concept, target_tool)` to a Claude API call and gets back a tool-specific prompt. This is a real architectural commitment — the app becomes Claude-API-dependent for a core function.

### Q3 — Reference lookup

**Confirmed via interview 2026-05-03:**

Prompts do not reference other prompts as text. They DO reference prior renders implicitly through the reasoning behind composition choices. When Claude drafts a prompt for a new direction or section, the choices encoded in the prompt (lens, register, lighting, blocking, subject treatment) are calibrated against what's worked and what hasn't in earlier batches — but the prompt itself doesn't cite those earlier batches by name.

The anchoring is conscious (Joseph and Claude both know during drafting which prior renders are informing the current prompt) but uncited. There's no "in lineage of: D4 P3 v1" annotation. The lineage exists only as Claude's reasoning during drafting.

**Reading confirmed: A** (prompts reference prior renders implicitly, through reasoning, not through text citations).

### Q4 — Generation session structure

**Confirmed via interview 2026-05-03:**

**Sessions are not a meaningful unit to Joseph.** The work is continuous-thread-with-pause-points: always inside the project, stops when tired, resumes when not tired. Boundaries are biological, not procedural.

**No end-of-day ritual.** No git commit, no "save state," no daily handoff write at session-end. Joseph just stops.

**Handoff docs are NOT inflection-point creative artifacts.** They have been written almost exclusively in response to the claude.ai 100-file upload limit forcing a chat restart. When the chat ran out of file slots, Joseph had to start a new conversation, which meant context loss, which forced a handoff write.

**Critical implication of Phase 0 (filesystem MCP via Claude Desktop):** The 100-file upload limit is gone. Files are now read by path. The forcing function that produced handoff docs no longer applies. **Handoff frequency should drop dramatically going forward, possibly to zero unless Joseph chooses to write handoffs for reasons other than chat-restart coping.**

**Chat-context-window length** is theoretically a separate boundary (token budget per chat), but Joseph has not yet experienced sluggishness from long chats — file-upload-limit always hit first.

### Q5 — Cross-AI handoff

**Confirmed via interview 2026-05-03:**

Cross-AI work follows **Flavor 1 (copy-paste with framing)**. Joseph takes relevant content from the Claude conversation, pastes it into Perplexity / ChatGPT / Grok / Gemini with framing (e.g., "argue against this"), receives a response in *that* AI's interface, and pastes the response back into the Claude chat as text.

The external AI's response then **lives only in the Claude chat history**, same fate as Joseph's own prompts and concepts. It is not captured to filesystem. It is not co-located with the decision it influenced. It does not produce filesystem artifacts of its own (unlike a generation prompt, which at least produces renders downstream).

This is structurally the same problem as F1/F2 but one layer up — and arguably worse, because cross-AI exchanges have *less* persistence than Joseph's own prompts. At least Joseph's prompts produce renders, which create a filesystem trail. Cross-AI pushback that influenced an architectural decision exists only in chat history; the architectural change that resulted may or may not name the AI that influenced it.

### Q6 — Friction hotspots beyond F1-F6

**Confirmed via interview 2026-05-03:** Joseph confirmed all six candidate friction-hotspots ARE active pain points. They cluster as variations of one underlying problem (the generation phase has zero project-aware tooling) and bank as F7. The six sub-flavors:

1. **Tool-tab context-switching** — six browser tabs open simultaneously (Claude, MJ, GPT, Kling, Gmail, project docs), constantly switching, losing thread of where you were and what you were doing.
2. **Waiting on generations** — MJ runs 1-2 min per batch, Kling longer. That waiting time is currently dead time, not productive time.
3. **Re-uploading reference images** — when using MJ image-prompting or reference features, reference images don't persist across the project. Re-uploading happens repeatedly.
4. **Batch identification** — when 20 returns come back from MJ, Joseph cannot tell which prompt produced which return without going back to chat history.
5. **Failed-generation overhead** — when a generation doesn't work and you regenerate, there's friction in tracking "this attempt failed because X, this one we're trying for Y."
6. **Naming things** — the router handles file naming on landing, but during generation the user is staring at MJ's auto-naming or GPT's timestamp naming.

### Friction finding F1: Prompt-output binding does not exist on filesystem

**Severity: HIGH.** This finding shapes v1 architecture more than any other revealed so far.

The renders are in canonical structure with audit-log discipline. The prompts that produced them live in chat scrollback. The two are not linked. Recovering the prompt for a given render requires manual scroll-and-search through Claude conversation history.

**Calibration round extension (parallel Claude, 2026-05-03):** prompts have NEVER been on filesystem — not "currently absent" but never-on-filesystem since project start (4/13). The recovery path through "ask Claude to reprint" has also become unreliable as multi-instance Claude work emerged this week (per M1) — different chat instances have different scrollback. See addendum.

**v1 implication:**

Prompt durability is non-optional. Every generation event the app handles must capture: the prompt text, the tool used, the timestamp, and the binding to the resulting output file(s). This becomes a first-class concept in the app, not an afterthought.

### Friction finding F2: Concept-state dies at chat boundaries (not session boundaries)

**Severity: HIGH.**

**Note:** This finding's framing was corrected during interview 2026-05-03. The original framing "concept-state dies at session boundaries" assumed sessions were a meaningful unit. They are not (see Q4). The accurate framing is:

The "concept" — the meta-thing prior to any single prompt that holds shared intent across a multi-prompt or multi-tool spread — currently lives only in chat-conversation context. When a chat conversation ends (forced by the now-removed file-upload limit, or in future by token-budget exhaustion), the concept dies with it. Each new chat re-derives the concept from canonical docs at real warm-up cost.

Phase 0 removes one of the two forcing functions for chat-end (file-upload limit). Token-budget exhaustion remains a theoretical boundary but has not yet been experienced.

**Calibration round quantification (parallel Claude, 2026-05-03):** re-derivation tax is concrete: roughly the **first hour of every session-restart** is concept-state reconstruction (today's session opened with reading three handoff docs, v1.5 architecture, predecessor handoff, walking through Phase 2 framing). At 3-4 session-restarts/week, that's 3-4 hours/week of pure reconstruction overhead. v1's persistent concept data model directly addresses this.

**v1 implication:**

The app needs a "concept" data model that persists **on filesystem**, not just in chat-context. Not a free-text doc — a structured object with at least: subject identifier, register specification, reference anchors, spread variants (if any), tool-target list, status (drafting / generated / evaluated / locked / archived). When a NEW chat opens (or any new app session opens), the concept exists; chat-context dying no longer destroys the concept. Re-derivation from briefing+handoff stops being the warm-up tax.

This data model is the second-most-consequential decision in v1 (after F1's prompt durability). The shape of the concept object determines how the UI lays out and what queries are possible.

### Friction finding F3: Tool-grammar knowledge is held by the conversational AI, not the project

**Severity: MEDIUM-HIGH.**

The translation from concept to tool-specific prompt is happening in Claude's head based on what Claude knows about each tool's syntax and behavior priors. This is a real but currently invisible dependency on Claude — the project files don't capture that "MJ wants `--ar 16:9 --v 7` and 'shot on 85mm anamorphic'" is a thing the prompts encode.

**Calibration round sharpening (parallel Claude, 2026-05-03):** Tool-grammar knowledge isn't uniform across Claude instances. The working Claude instance knows tool grammars because *it's been drafting prompts for each in this project*. A fresh Claude API instance with no project context drafts substantially worse prompts. **F3's dependency is sharper: "Claude-instance-with-accumulated-project-history" not "Claude generally."** v1 needs to materialize that history into config or docs the app passes to fresh Claude API calls — a tool-grammar knowledge base, possibly auto-populated from successful prompt+output bindings (per F1) over time. See addendum.

**v1 implication:**

Per Joseph's preference: the app sends `(concept, target_tool, accumulated_tool_grammar)` to a Claude API call and gets back a tool-specific prompt. This means:

1. **The app is Claude-API-dependent for a core function**, not just for nice-to-haves. v1 cannot operate offline for prompt generation. (It can operate offline for everything else — file routing, audit logs, manifest regen, render organization.)
2. **API costs become a real ongoing operational cost.** Worth modeling in the v1 spec.
3. **Tool-grammar config is now part of v1.** Not just send concept; send concept + project-specific tool-grammar knowledge.
4. **Failure mode: API down or rate-limited.** v1 needs a graceful degradation path. Possibilities: cache last-N tool-specific prompts per concept, allow manual prompt entry that bypasses the model, surface API failure clearly so user can retry later.

### Friction finding F4: Reference lineage is conscious but uncited

**Severity: MEDIUM-HIGH.**

Prompts are anchored to prior renders during drafting (the reasoning behind composition choices is calibrated against what worked / didn't work earlier), but the lineage exists only in Claude's drafting reasoning. It's not encoded in the prompt text, not in NOTES.md, not anywhere on filesystem. After the fact, the lineage becomes irrecoverable except by asking "what prior renders informed this prompt" while the chat history still exists.

This is structurally distinct from F1 (prompts not bound to outputs). F1 says the prompt-render link is missing. F4 says the prior-render-influences-current-prompt link is also missing — even between prompts that exist, lineage is not queryable.

**Calibration round third layer (parallel Claude, 2026-05-03):** there's a third reference layer F4 missed. Prompts reference prior CONCEPTS that lived in chat (not prior prompts, not prior renders, but conceptual anchors held in chat-context). Example: D4 P3 was anchored on the Skinner-box H#3 hero shot's register from chat-discussions weeks ago. **Three layers of reference: (1) textual prompt-to-prompt — rare, durable; (2) implicit render-to-render via craft vocabulary — common, moderately durable; (3) conceptual chat-to-chat — frequent, most ephemeral, most consequential.** v1's lineage-anchoring needs to cover all three, not just the second. See addendum.

**v1 implication:**

The app needs lineage-anchoring as a feature distinct from prompt capture (F1). Three layers of lineage to support:
- **Textual references** (prompt cites another prompt) — straightforward.
- **Render references** (prompt was anchored to specific prior renders) — reference-picker UI selecting from canonical renders.
- **Conceptual references** (prompt was anchored to a concept-thread held in chat) — captures the conceptual reasoning that connects prompts across time, possibly via the cross-Claude/cross-AI capture surface from F6/F11a.

This makes lineage queryable: "what prompts cite D4 P3 v1 as anchor?" / "what concepts informed the H#3 register?" become real queries.

### Friction finding F5: Sessions are not a meaningful unit; persistence must be continuous

**Severity: MEDIUM.** Less an architectural problem to solve than a constraint shaping how everything else gets built.

Joseph's work model is continuous-thread-with-biological-pauses. There is no "session start" or "session end" concept in his head. He works until tired, stops, resumes when not tired.

**v1 implications:**

1. **No session-boundary UI.** The app should never prompt "save and close" or "create new session" or "commit your work." Auto-save-everything-immediately is the discipline. State is continuously persistent.

2. **No daily-handoff-write affordance unless explicitly requested.** The handoff-doc pattern was a coping mechanism for chat-restart, not a creative artifact. With Phase 0 in place removing the file-upload limit, the forcing function is gone. The app should NOT replicate "write a handoff doc" as a built-in workflow step.

3. **Resume-from-anywhere semantics.** When Joseph opens the app, he picks up wherever he left off. No "load last session" dialog. The current state of every concept, every prompt, every render audit IS the persistent state.

4. **Pause-tolerance.** If Joseph walks away mid-action (mid-prompt-drafting, mid-batch-audit), the app should hold that state indefinitely. Coming back hours or days later should feel the same as coming back minutes later.

### Friction finding F6: Cross-AI exchanges have less persistence than Claude-internal work

**Severity: MEDIUM.**

External AI responses (Perplexity resistance, ChatGPT adversarial reads, Grok input, Gemini coordination) come back into the Claude chat as pasted text per Flavor 1 (copy-paste with framing). They influence Joseph's decisions but are never captured to filesystem.

When an architectural decision is influenced by Perplexity pushback, the *resulting* decision may get documented (in handoff, in architecture doc), but the *source* pushback rarely is. The project files don't carry "this v1.5 architecture lock was influenced by Perplexity's argument that X" — that influence trail dies with the chat.

This is structurally the same problem as F1/F2 but one layer up, and arguably worse: at least Joseph's own prompts produce renders (creating a filesystem trail). Cross-AI pushback creates no artifact of its own.

**v1 implication:**

Cross-AI capture is a real category, but it's lower priority than F1-F4 because it's less central to the core generation-pipeline workflow. Two viable v1 approaches:

1. **Don't try to handle it in v1.** Cross-AI exchanges remain ephemeral. Accept the loss. Rationale: it's not the app's job to capture every form of intellectual input.

2. **Provide a simple capture surface.** A "paste cross-AI exchange" button that takes pasted text + a note about which AI + what decision it relates to + writes to a `cross_ai_log/` directory. Low-effort, optional, doesn't gate normal workflow.

**Per F11a/F11b/M1 (subsequently banked):** Option 2 is the right call. Cross-AI capture must also handle the cross-Claude-instance sub-case (M1 names the pattern; F11a names the friction). See addendum.

### Friction finding F7: Generation phase has zero project-aware tooling — six sub-flavors of pain

**Severity: HIGH.** This is the most consequential finding for v1 *UI design* (whereas F1 and F2 drive v1 *data model*).

The generation phase currently happens entirely outside any project-aware tooling. Joseph context-switches between browser tabs (Claude, MJ, GPT, Kling, Gmail, docs), waits on generations with nothing useful to do, re-uploads references, can't identify which return came from which prompt, has no good record of failed attempts and why they failed, and stares at tool-imposed naming schemes that the router has to clean up after the fact.

The six sub-flavors:

1. **Tool-tab context-switching cost.** Six tabs open. Constant switching. Lost thread of "where was I."
2. **Dead time during generation waits.** MJ runs ~90s per batch. Kling longer. Currently used poorly.
3. **Reference image re-uploading.** No project-level reference persistence across tools.
4. **Batch identification problem.** 20 returns from MJ, no inline visibility of which prompt produced which return. Filename's concept-fragment is partial; full prompt lives in chat.
5. **Failed-generation tracking overhead.** Diagnostic reasoning ("a1 failed because white-coat collapse, a2 corrects via apparatus-as-architecture description") lives only in chat. Failed attempts may or may not get archived properly.
6. **Naming friction at generation-time.** Tool-imposed names are cleaned up at routing time, not generation time. The app could let the user assign meaningful names *upstream* of the generation tool.

**Calibration round leverage ranking (parallel Claude, 2026-05-03):** highest-leverage sub-flavors are (in priority order): **(1) failed-generation overhead**, **(2) batch identification**, **(3) reference-image re-uploading**. Tool-tab switching, dead time, naming friction are real but UX-grade rather than learning-loop-blockers. v1 should address all six (workspace surface gives most for free), but **prototype priority order should follow the leverage ranking** — build failed-generation tracking + batch identification + reference-image persistence first. See addendum.

**v1 implication:**

The app's primary surface should be a **single project-aware workspace that subsumes the six tabs Joseph currently juggles.** Not "an app that opens MJ in a webview" — that's just a different tab. Rather: an app where:

- The current "concept I'm working on" is visible at all times (addresses F2 + sub-flavor 1)
- The current "prompts queued / running / returned" is visible at all times (addresses F1 + sub-flavor 4)
- The current "audit-pending batches" is visible at all times (addresses sub-flavor 5)
- Reference images live in the project, not in tool-specific upload caches (addresses sub-flavor 3)
- During generation waits, the app naturally surfaces other useful work (audit pending batches, draft next prompt, review lineage chain) (addresses sub-flavor 2)
- Names are assigned at concept/prompt creation time, propagating through generation and routing (addresses sub-flavor 6)

This is a substantial UI commitment for v1. It's the difference between "an app that captures prompts" and "an app that *is the generation workspace*." But it's the correct ambition — the six pain points cluster around "the generation phase is fragmented across tools" and the only way to address that is to provide a unified workspace. Half-measures (just prompt capture, just reference management, just batch tracking) leave the underlying fragmentation in place.

**Important caveat:** the app does NOT replace MJ, GPT Image 2, Kling, etc. Those tools still do the actual generation. The app provides the *project-aware workspace* that calls into those tools (via API where available, via clipboard-handoff to web UI where not, per AD-1) and captures everything that happens.

---

## Section 3: What happens AFTER Routing (post-routing — IN PROGRESS)

See `workflow_audit_v1_section3_addendum.md` for Section 3 questions, findings F8-F11b, M1-M3, the parallel-Claude calibration round, and Q10 non-finding.

---

## Section 4: Cross-cutting concerns (TO INTERVIEW)

What persists across sessions, what patterns recur, what discipline must be preserved.

Already visible from the project structure (no interview needed):
- **Audit-log discipline:** every routing op writes to `tools/router_log.md`. Every architectural change has its trigger documented.
- **Refinement-stop windows:** architectural changes are gated to specific time windows; outside those windows, changes require fresh production-emerging-discovery triggers.
- **Manifest as truth:** `FILESYSTEM_MANIFEST.md` is regenerated after structural changes; section-list edits in `_regen_manifest.py` are required when shared/ or _work/ structure changes.
- **Variant-history-and-deprecation-marker convention:** failed work isn't deleted; it's marked `_DEPRECATED_<reason>` and archived in `_work/` so the failure mode is recoverable.
- **Per-action approval:** Phase 0 confirmed this discipline at filesystem-MCP level (read tools auto-approve in conversation; write tools approve per-action).
- **NOTES.md as recipe-authority:** every shipped section has a NOTES.md capturing what's canonical, deviations from convention, pending work, do-not-touch boundaries.
- **Continuous-persistence model (per F5):** no session boundaries, no end-of-day rituals. State must be continuously persistent.

To be filled in by interview:
- What state genuinely needs to persist between sessions? (Reframed: between chat-conversations, since "sessions" doesn't apply.)
- What patterns recur enough to deserve UI affordance?
- What discipline must NEVER be auto-bypassable?

---

## Section 5: Out of scope for v1 (DRAFT, AWAITING CONFIRMATION)

Pre-fill candidate list (Joseph confirms or revises):

- **Multi-user collaboration.** Single-user only.
- **Cloud sync.** Local-only filesystem.
- **Editorial assembly UI.** Existing tools (Remotion, video editor) keep doing the editorial work. v1 doesn't touch the Remotion project structure.
- **AI-orchestrated multi-tool batch generation.** v1 might *call* MJ/GPT/Kling APIs for individual generations, but not "generate this concept across all three tools and rank the results automatically." That's v2+.
- **Auto-prompt-improvement.** v1 doesn't try to be a prompt engineer. Joseph drafts prompts collaboratively with Claude; the app captures and routes. Prompt-improvement-by-the-app is v2+.
- **Cross-project generalization.** v1 is Latent Systems-specific. Generalization happens later, by extracting patterns that survive multiple projects.
- **Distribution / multi-tenancy / "release as app for others."** Different project entirely; explicitly deferred.
- **Built-in handoff-doc generator** (per F5). The app should not replicate the chat-restart-handoff pattern. If handoffs have value beyond coping, they remain a manual creative act.
- **API automation for MJ and Kling** (per AD-1). v1 uses clipboard-handoff to web UI for tools without individual-creator API access. API automation for those tools is v2+ when/if API access opens.
- **Multi-instance Claude orchestration** (per F11b option 3). v1 captures cross-Claude-instance handoffs after the fact (per F11b option 2 / F6 option 2) but does not orchestrate the exchanges themselves. Orchestration is v3+ territory and may require infrastructure that doesn't exist yet.

---

## Friction Findings Register

This register accumulates friction-findings discovered during the audit. Each finding gets a code (F1, F2, ...) and a severity rating. The register becomes the ranked v1 spec when interview is complete.

| Code | Severity     | Phase             | Finding |
|------|--------------|-------------------|---------|
| F1   | HIGH         | 2 (pre-Downloads) | Prompt-output binding does not exist on filesystem. Prompts have NEVER been on filesystem since project start (4/13). v1 must capture prompts as first-class objects bound to outputs. |
| F2   | HIGH         | 2 (pre-Downloads) | Concept-state dies at chat boundaries. ~1 hour warm-up tax per session-restart on concept-state reconstruction. v1 needs persistent concept data model on filesystem. |
| F3   | MEDIUM-HIGH  | 2 (pre-Downloads) | Tool-grammar knowledge held by Claude-instance-with-accumulated-project-history (not Claude generally). v1 must materialize that history into config the app passes to fresh Claude API calls. |
| F4   | MEDIUM-HIGH  | 2 (pre-Downloads) | Reference lineage is conscious but uncited. THREE layers (textual prompt-to-prompt; implicit render-to-render via craft vocabulary; conceptual chat-to-chat — most ephemeral, most consequential). v1 needs lineage-anchoring covering all three. |
| F5   | MEDIUM       | cross-cutting     | Sessions are not a meaningful unit. v1 must avoid session-boundary UI; auto-save continuously; resume-from-anywhere; pause-tolerance. Handoff-doc-as-coping dies with Phase 0. |
| F6   | MEDIUM       | 2 (pre-Downloads) | Cross-AI exchanges leave no filesystem trail. Per F11a, F11b, M1 — option 2 (capture surface) is the right call; must also handle cross-Claude-instance sub-case. |
| F7   | HIGH         | 2 (pre-Downloads) | Generation phase has zero project-aware tooling. Six sub-flavors. Leverage ranking: failed-generation tracking > batch identification > reference-image persistence > [tab-switching, dead-time, naming]. v1's primary surface is unified workspace. |
| F8   | HIGH         | 3 (post-routing)  | Audit phase has minimal tooling and verdict durability is delayed. Multi-AI evaluation is systematic discipline (not casual). Two duration modes (quick-pass vs deep-evaluation) need separate UI. See addendum. |
| F9   | MEDIUM-HIGH  | 3 (post-routing)  | Hero promotion is partial discipline — file-level consistent (rename + copy to `winners/`), doc-level ad-hoc but enumerable (`README.md` of relevant shared dir + architecture doc + handoff). v1 should make atomic with audit log. Un-hero requires reason field. |
| F10  | MEDIUM-HIGH  | 3 (post-routing)  | NOTES.md discipline is evolving — variance shows trajectory of discipline-maturation over three weeks. v1 must be discipline-aware AND discipline-tolerant. NOTES.md templates should themselves be versioned (current v0.5; older NOTES.md flagged not auto-upgraded). |
| F11a | MEDIUM-HIGH  | cross-cutting     | Cross-Claude handoff is sub-case of F6. Same project / shared filesystem / different chat instances → still no filesystem trail; transport layer is human copy-paste. Adds: instance discoverability problem (no project-side index of active instances). |
| F11b | MEDIUM       | cross-cutting     | Multi-instance Claude work has real value but no infrastructure. v1 = Option 2 (capture surface only). Orchestration deferred (v3+ territory). |
| M1   | MEDIUM       | meta              | Multi-Claude-instance pattern (parallel instances on related-but-distinct work in same project) is a workflow innovation that emerged this week. Distinct from F6 (different beast: same AI / different instances / shared filesystem / copy-paste transport). v1 supports the result via capture surface; pattern itself remains user-managed. |
| M2   | LOW-MEDIUM   | meta              | Audit is generating findings about audit-conducting workflow itself (extended-structured-interview-with-AI). Modest v1 implication: capture surface should handle long-form Q&A as a content type. |
| M3   | LOW-MEDIUM   | meta              | Compressed-text answers ("B" / "yes" / "1") are a primary input pattern. v1 should support compressed-answer + AI-expansion as a first-class flow. Connects to F3 sharpening — fresh Claude API calls need project-context loaded for expansion to work. |

---

## Architectural Decisions Register

| Code | Decision | Source | Implication |
|------|----------|--------|-------------|
| AD-1 | v1 = horizontal-slice across all tools (concept persistence, prompt drafting, audit, lineage all work everywhere; generation triggering varies by API availability) | F7 follow-up, 2026-05-03 | For tools without individual-creator API access (MJ, Kling), v1 uses clipboard-handoff to web UI rather than API automation. **Caveat (calibration round):** clipboard handoff UX is prototype-critical. If clunky, users route around the app and persistent-binding benefit evaporates. See addendum. |

---

## Status

- Section 1 (already-handled): **COMPLETE.** Catalogs the existing router.
- Section 2 (pre-Downloads): **COMPLETE.** All 6 questions answered. 7 findings banked. All sharpened by parallel-Claude calibration round.
- Section 3 (post-routing): **IN PROGRESS** in addendum doc. Q7-Q11 answered. Q12 next. F8-F11b banked plus M1-M3 meta-findings. Q10 banked as non-finding.
- Section 4 (cross-cutting): **TO INTERVIEW.**
- Section 5 (out of scope for v1): **DRAFT, AWAITING CONFIRMATION.** AD-1 + F11b option 3 added items.
- Friction Findings Register: **13 findings banked (F1-F11b + M1-M3).**
- Architectural Decisions Register: **1 decision banked (AD-1).**
- Cross-Claude calibration: **1 round complete (parallel instance, 2026-05-03), banked in addendum with attribution per F11a discipline.**

