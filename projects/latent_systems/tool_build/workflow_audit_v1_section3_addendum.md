## Section 3: What happens AFTER Routing (post-routing — IN PROGRESS)

Files are in canonical filesystem. What happens next? Currently a mix of PowerShell, git bash, Claude Code, manual decisions.

### Q7 — Audit / evaluation

**Confirmed via interview 2026-05-03:**

When 20 returns from MJ land in canonical structure (e.g., `shared/visual_identity_phase2_evaluations/4_schematic_apparatus/run_2026-05-03/`):

1. **Viewer:** Windows Media Player / Windows Photos image viewer. Not File Explorer thumbnails (initial interview answer corrected). Means a full-screen viewer that displays images at meaningful size, but it's still a general-purpose image viewer — no prompt-alongside-render display, no tagging, no rating, no project-aware metadata. Joseph navigates between images using the viewer's prev/next controls.
2. **Cadence:** One-by-one through the viewer's navigation, not side-by-side grid. Serial evaluation rather than differential evaluation.
3. **Scoring:** Informal. Criteria exist (used tonight: register-relativity test, four-element craft test, etc.) but are not formalized as numerical rubrics. **Joseph also asks AIs for opinions using the criteria** — outsources part of the audit to Claude / Perplexity / ChatGPT as a structured second opinion, with Joseph making the final call.
4. **Verdict capture:** Conversational with Claude. Verdicts ("D4 P3 v1 is hero zone") become durable hours later when a bank doc is written. Between verdict and bank doc, the verdict lives only in chat.
5. **Duration:** Wide range. Minutes to an hour per batch depending on complexity and how clearly the spread separates.

### Friction finding F8: Audit phase has minimal tooling and verdict durability is delayed

**Severity: HIGH.**

The audit phase — the moment when generation outputs become creative decisions — currently runs through Windows Media Player / Photos viewer (a general-purpose viewer with no project awareness), serial one-by-one viewing, informal scoring against unformalized criteria, AI second-opinions via copy-paste, and conversational verdict-capture that only becomes durable when a bank doc is written hours later.

**Five sub-flavors of audit-phase friction:**

1. **Image viewer is project-unaware.** Windows Media Player / Photos shows images at full size with prev/next navigation, which is better than File Explorer thumbnails. But it has no project awareness: doesn't display the prompt that produced each render, doesn't support tagging or rating, doesn't let you mark a verdict from within the viewer, doesn't link the render to its concept or to prior renders in lineage. The audit happens in a viewer designed for general image browsing, not for creative evaluation against project-specific criteria.

2. **Serial evaluation when grid would help.** Going one-by-one through 20 returns means you can't easily compare adjacent variants in the same view. A 4×5 grid with prompt headers would let you see the spread holistically. (Note: Joseph may prefer one-by-one even when grid is available — this is a UI affordance, not a forced flow change. Both should be available.)

3. **Criteria are unformalized.** The criteria exist as discipline (register-relativity, four-element craft test, etc.) but aren't encoded as scoring rubrics. Audit happens against criteria-from-memory rather than criteria-on-screen. v1 could surface criteria as a checklist or rubric alongside each render.

4. **AI-assisted evaluation is manual copy-paste.** Joseph asks AIs (Claude, Perplexity, ChatGPT) for opinions on renders using the criteria as framework. Currently this means: paste image into chat, paste criteria, get response, paste back. The app could make AI-assisted evaluation a first-class flow: select render or batch → invoke "AI evaluation against criteria" → get structured feedback logged alongside the render.

5. **Verdict durability gap.** When you decide "this is hero zone," that verdict lives only in chat until hours-or-days later when a bank doc is written. If chat closes before bank doc is written, the verdict is recoverable only through reconstruction. Same problem as F1 (prompt durability) but applied to verdicts.

**v1 implication:**

The audit surface in v1 needs at minimum:

- **Image viewer that shows prompt alongside render** (addresses sub-flavor 1). The viewer becomes project-aware: render + prompt + concept context + lineage chain visible in one screen. Replaces Windows Media Player for project-context evaluation while WMP / Photos remains useful for general full-screen viewing if Joseph prefers.
- **Toggle between serial and grid views** (addresses sub-flavor 2 without forcing flow change).
- **Criteria visible during audit** as a configurable checklist or rubric per concept-type (addresses sub-flavor 3).
- **AI-assisted evaluation as one-click flow** that sends render + criteria to Claude API, gets structured response, logs response alongside render (addresses sub-flavor 4).
- **Verdict capture as immediate filesystem write**, not chat-only (addresses sub-flavor 5). When Joseph marks a render as "hero" or "deprecated" or "save for v2," that decision writes to filesystem instantly with timestamp.

This is a substantial UI commitment. Combined with F7's workspace surface, the app's core surface is shaping up as: **concept browser → prompt drafting → batch tracking → audit viewer with rubric + AI-assist → verdict capture → routing handoff.** That's the v1 spine.

### Q8 — Hero promotion

**Confirmed via interview 2026-05-03:**

1. **File-level mechanic:** When a render becomes a hero, it's renamed and copied to a dedicated `winners/` folder within the canonical filesystem structure. Today's session showed this pattern executed via Claude Code: `D4_P3_archival-bw-lab_v1.png`, `D5_thesis_image_MJ_v4_human_in_chamber.png`, `D5_thesis_image_GPT_explicit_action.png` all landed in `winners/` subdirectories under their parent direction folders. The original render also remains in the run-batch directory; the hero copy is additive, not destructive.

2. **Doc-level mechanic:** The verdict gets written into "system docs" — but **Joseph is not certain which doc(s) specifically.** Possible candidates from project structure: section-level NOTES.md (e.g., `ep1/h3_skinner/NOTES.md`), handoff docs, bank docs, the audit log file from the routing op. The honest answer is: it varies. The doc-update step does not have a defined discipline analogous to the router's "every action logs to `tools/router_log.md`."

3. **Reversibility:** Yes, hero status can be reversed. When un-hero'd, the file does not get deleted. It gets archived — consistent with the project's variant-history-and-deprecation-marker convention (channel staple #12). The deprecation marker presumably gets applied to the un-hero'd copy.

### Friction finding F9: Hero promotion is a partial discipline — file-level consistent, doc-level ad-hoc

**Severity: MEDIUM-HIGH.**

The file-level mechanic for hero promotion is consistent: rename + copy to `winners/`. The doc-level update is ad-hoc: the verdict gets written somewhere in the system, but not consistently into a defined location, and Joseph cannot reliably enumerate which doc(s) hold which verdicts.

**Why this matters:**

The router's discipline is exemplary: every routing action gets logged to `tools/router_log.md`. There's no ambiguity about where to look for "what got routed when." Hero promotion lacks the equivalent — the question "which renders got promoted to hero, when, by what reasoning" cannot be answered by reading a single file. It requires reconstructing from NOTES.md scattered across sections, handoff docs scattered across dates, and bank docs scattered across sessions.

This is structurally similar to F1 (prompt-output binding missing) but at a different layer. F1: the link between prompt and render isn't on filesystem. F9: the link between hero-decision and reasoning isn't durably captured.

**v1 implication:**

Hero promotion in v1 should be an **atomic action** that does several things together:
1. Copy render to canonical `winners/` location with proper naming (already established mechanic — preserved).
2. Write a verdict log entry to a defined location — proposed: `tool_build/hero_promotions_log.md` or per-direction `winners/_promotions_log.md` (to be decided in spec).
3. Optionally update relevant section NOTES.md with a hero-reference line (to be decided in spec).
4. Capture the *reasoning* — at least a short note ("hero zone — desk lamp anchor + foreground apparatus + background bokeh holds at 100%") — alongside the file copy.

The un-hero'ing path (channel staple #12 deprecation pattern) needs equivalent atomicity:
1. Move hero copy from `winners/` to deprecated archive with `_DEPRECATED_<reason>` marker.
2. Write a de-promotion log entry.
3. Update relevant NOTES.md.

This is moderate-complexity work for v1. The router model gives us the template — atomic action with audit log. Hero promotion just extends the pattern to creative-verdict territory.

### Q9 — NOTES.md authorship

**Confirmed via interview 2026-05-03 + filesystem ground-truth check:**

1. **Trigger:** When Joseph remembers to write one, or when Claude prompts him to. No defined trigger event (e.g., "at hero promotion" or "at section ship"). NOTES.md authorship is event-less rather than event-driven.

2. **Authorship:** Claude writes outright with Joseph's approval at the end. Joseph supplies direction and content judgment; Claude composes the prose. This is consistent with the channel-staple #11 NOTES.md-as-recipe-authority pattern but it means **NOTES.md authorship is API-dependent** the same way prompt-drafting is (F3) — the app cannot generate NOTES.md offline.

3. **Coverage:** Joseph "not sure" — the coverage is genuinely unknown to him. Filesystem ground-truth check across 6 sampled EP1 sections (`h1_hook`, `h2_face_glow`, `h4_match_cut`, `h5_slot_machine`, `section_1c`, `cold_open`) shows 3 have NOTES.md and 3 don't. **50% coverage in this small sample**, suggesting the gap is wider than the two known-pending items (§1.E and §1.C) in the gates list.

**Quality variation across the existing NOTES.md:**

- **§1.C NOTES.md is exemplary** (~80 lines): full recipe-authority with prompt text verbatim, tool settings, validation criteria checklist, banked alternates table, cross-references to channel staples, version history.
- **h2_face_glow NOTES.md is a status note** (~25 lines): captures pending decision, deprecation rationale, what's in `reference/rejected/`, what's blocked.
- **h4_match_cut NOTES.md is a technical-spec doc** (~80 lines): captures frame-precise alignment math, source files, transform parameters, audio-pass pending items.

**Critical clarification per interview 2026-05-03:** The variance across these three NOTES.md is NOT evidence of discipline failure. It is evidence of **discipline evolution in flight.** Joseph has been learning, implementing, and building the system *while making EP1 in parallel*. The §1.C NOTES.md represents a later, more developed state of NOTES.md discipline than the h2_face_glow NOTES.md. h4_match_cut sits somewhere between, capturing what was important to capture at the time it was written.

This is the same pattern that produced this app project: a learning-and-implementing-while-building loop. The variance is the project's history made visible. Different NOTES.md were written at different points along the discipline-evolution arc, and each one is a faithful artifact of the standard at the time it was authored.

### Friction finding F10 (REVISED): NOTES.md discipline is evolving — coverage gap + intentional variance + no completeness state

**Severity: MEDIUM-HIGH.**

NOTES.md is real, well-structured, and a load-bearing channel staple (#11 — NOTES.md-as-recipe-authority). The discipline is evolving as the project itself develops. The friction is not "NOTES.md fails to follow a defined standard" — it's that the project doesn't have a way to track what NOTES.md state currently exists, doesn't have a defined trigger for when NOTES.md should be written or revisited, and doesn't have a way to *deliberately* upgrade older NOTES.md to the current standard when the standard advances.

**Five characteristics:**

1. **Coverage is unknown to the user** — Joseph cannot enumerate which sections have NOTES.md and which don't. The known-pending items (§1.E, §1.C) surface because Joseph noticed them, not because the system tracks gaps systematically.

2. **No defined trigger** — NOTES.md gets written when remembered or when Claude prompts.

3. **Authorship is Claude-dependent** — same API-dependency as F3.

4. **Variance reflects evolving discipline, not template failure** — older NOTES.md captured what was important to capture at the time. Forcing them retroactively into a §1.C-style template would be revisionism, not discipline.

5. **No mechanism to mark "needs upgrading"** — when the discipline advances (as it has), there's no way to flag older NOTES.md for revisit when production cycles back through the relevant section. They become latent debt that's only discoverable through ad-hoc filesystem browsing.

**v1 implication (REVISED):**

The app should treat NOTES.md state as a tracked, evolving thing — not a binary present/absent state and not a uniformly-templated state.

Three concrete v1 affordances:

1. **NOTES.md status view per section.** A list of all canonical sections, with NOTES.md presence/absence/staleness marked. Plus a "last-discipline-version" marker per NOTES.md so older docs can be flagged for revisit when the discipline advances. Trivial to implement structurally (`os.path.exists` + a small metadata block at the top of each NOTES.md noting the discipline version it was written against).

2. **NOTES.md template *menu* — not enforcement.** When Joseph or Claude generates a new NOTES.md, the app offers template variants the project has used (status-pending note, technical-spec doc, full recipe-authority) so the appropriate level of completeness can be selected for what's actually being captured. The app doesn't *require* §1.C-level completeness for a section that's still in candidate-pending state. Templates are scaffolding, not enforcement.

3. **Hero-promotion-triggers-NOTES-prompt.** When Joseph promotes a render to hero (per F9 atomic action), the app prompts: "this section's NOTES.md hasn't been updated since X — update now?" Defines the event-driven trigger that's currently missing without forcing premature documentation.

**v1 design principle that emerged from this finding:**

The app is being built for a project that is *itself learning its discipline as it builds.* That changes the v1 spec in a meaningful way: the app cannot impose a fixed standard on top of a moving discipline. It must support the project's discipline-evolution, not freeze it.

Concrete implications:
- Templates are menus, not enforcement.
- Status views surface gaps without prescribing how to close them.
- Triggers prompt for action without forcing it.
- The data model captures *which version of discipline* a given artifact was authored against, so retroactive upgrading becomes a deliberate act rather than a retrofit.

This principle generalizes beyond NOTES.md. It applies to: how the app handles older renders that don't fit current vocabulary (re-render scope question, gate #14 in the bank doc); how it handles older handoff docs that follow earlier discipline versions; how it handles older audit logs that captured less metadata than current ones. **The app must be discipline-aware AND discipline-tolerant.**

### Q10 — Manifest regen trigger discipline (NON-FINDING)

**Confirmed via interview 2026-05-03:**

The trigger is "a combination" — sometimes Claude flags it, sometimes Joseph remembers, sometimes it surfaces when the manifest is needed and noticed to be stale. Critically: **the manifest regen script is a recent addition.** The discipline around when to invoke it has not had time to stabilize.

**This question does not generate a friction finding.** F1-F10 are about gaps that have had time to become friction — places where the project has been operating long enough to feel the lack of tooling. Manifest regen, by contrast, is brand-new tooling. There is no extended history of pain to surface.

The honest project-state observation: the manifest regen trigger pattern is still being figured out, in keeping with F10's revised principle (discipline evolution in flight). The app should support whatever trigger discipline emerges — not prescribe one based on assumptions about what manifest regen *should* trigger on.

**Implication for v1:**

The app's manifest-regen integration should be:
- **Available as an action** — invokable from the UI at any time.
- **Surfacing manifest-staleness state** — when filesystem changes have happened since last regen, the app indicates this without forcing regen.
- **Not pinning a trigger discipline** — letting the user (and Claude as collaborator) decide when to regen, rather than auto-regenning on every filesystem change or prescribing a workflow rule.

This is consistent with F10's discipline-aware-and-discipline-tolerant principle. New tooling enters the project; the discipline around it stabilizes through use; the app supports whatever stabilizes rather than freezing an early-stage assumption.

### Q11 — Architecture changes

**Source attribution:** This Q11 answer was sourced via cross-Claude handoff. Joseph asked the question to a parallel Claude instance working on a different chat in this project — the instance that drafted v1.5 today, has firsthand experience of the architecture-change workflow, has read access to `docs/CHANNEL_STRUCTURAL_ARCHITECTURE_v1_5.md` and the v1.4 archived predecessor, and applied the Image 17 hybrid-dad scope correction during today's v1.5 lock. Joseph copy-pasted the answer into this chat after verifying it matches his own read of the workflow. Transmission = manual copy-paste; Joseph's role = directed the question and verified the answer; my role (audit Claude) = banked with attribution after flagging the depth shift rather than attributing the answer to in-chat back-and-forth.

This sourcing is itself diagnostic — see F11a and F11b below.

**Q11.1 — What triggers an architecture change?**

Production-emerging-discovery is the current operative trigger inside refinement-stop windows, but it's not the only legitimate trigger across the project's history. Six trigger types have actually fired across v1.0 → v1.5:

1. **Initial canonical lock (v1.0).** Not a "change" — the first writing-down of structure that was previously in Joseph's head.
2. **Audit-driven refinement (v1.0 → v1.1).** Phase 2 audit caught register-variance in §6 + the staple #13 full/compressed form distinction. Discovery from re-reading the doc, not from production work.
3. **Cross-AI insight integration (v1.1 → v1.2).** Perplexity's AI-native positioning reframe. External resistance produced a structural insight that altered channel positioning. Conceptually-emerging from outside the project.
4. **Discipline addition (v1.2 → v1.3).** Refinement-stop-condition (72-hour clock + production-emerging-discovery carve-out). Meta — adding a rule about how future architecture changes get triggered. Itself triggered by Perplexity flagging that architecture work could expand infinitely.
5. **Functional testing surfacing pattern (v1.3 → v1.4).** Voice-profile testing surfaced movie-trailer drift; voice profile changed. Production-adjacent (testing was production prep, not production itself), but the trigger was empirical evidence from rigorous test, not "we tried it in a real shot and it broke."
6. **Production-emerging-discovery proper (v1.4 → v1.5).** Craft-vs-register diagnostic during actual generation work. The most recent lock and the only one that was "we did the work and discovered something."

**Pattern, plainly:** triggers are anything that produces empirical evidence durable enough to reshape future decisions. The refinement-stop discipline (channel §13 v1.3) doesn't actually restrict triggers to production-emerging — it restricts when post-lock changes are permitted *during* refinement-stop windows. The §13 carve-out is "production-emerging-discovery" because that's the trigger type most likely during active production. Outside refinement-stop windows, any of the trigger types above is legitimate.

**What's NOT a legitimate trigger:**

- "I had a thought." Architecture isn't a notebook for ideas; it's the durable structure decisions affecting canonical material.
- "AI consensus." Multiple AIs agreeing isn't evidence — most pattern-match to validation.
- "It would be cool if." Aspiration without empirical grounding doesn't earn architecture treatment.
- Edge-case-of-one. A single shot needing weird treatment doesn't elevate to architecture; it goes in the shot's NOTES.md.

The discipline test: does this finding apply across episodes, or to this specific moment? Cross-episode → architecture. Specific-moment → NOTES.md.

**Q11.2 — Write-the-doc workflow.**

The pattern that's emerged:

1. Joseph signals the trigger — "Lock v1.5 with the render-craft finding" / "We need to add §13 stop-condition" / "v1.4 voice profile change."
2. Claude reads the prior version in full from the project files (this matters — Claude does not draft from memory of prior versions, Claude views the actual file).
3. Claude drafts the new version as a complete document, not a diff. Drafting principle: minimal change, maximum clarity. Sections that don't change inherit verbatim. Sections that change get rewritten in place. New sections get appended (preserving section numbering for unchanged sections).
4. Joseph reads the draft and directs revisions. Sometimes one pass; sometimes several. Today the v1.5 draft went through one pass with the Image 17 hybrid-dad scope correction.
5. Lock the version when satisfied. "LOCKED" header gets added; supersession marker added to prior version's filename when it moves to archive.

**What's NOT the workflow:**

- Claude does NOT draft from a blank page. Always start from the prior version on disk.
- Claude does NOT propose architecture changes unprompted. The trigger comes from Joseph; Claude drafts on instruction.
- Claude does NOT diff in the conventional code-review sense. The doc is rewritten as a unified whole; the changelog at the bottom captures what changed at version-bump.

**The changelog discipline:**

v1.5 §"Document maintenance" — the refinement history list. Every version since v1.0 has a one-line entry naming what changed. That's the diff/changelog discipline, embedded in the doc itself. Not a separate `CHANGELOG.md` file; an in-doc convention that travels with the canonical doc.

This works because:
- Architecture docs are short (~200-400 lines), so per-version full rewrites are tractable.
- The refinement-history embedded in the doc = single source of truth for "what changed when."
- Archive lifecycle (`docs/archive/CHANNEL_STRUCTURAL_ARCHITECTURE_v1_4_SUPERSEDED_by_v1_5.md`) means full prior versions are recoverable; no need for a textual diff.

**When this might break down:** if architecture grew to 2000+ lines, full-rewrite-per-version would become wasteful. At that scale, true diff tracking becomes warranted. The project is not there.

**Important addition (per Joseph's verification, 2026-05-03):** the in-doc changelog convention is itself a recent addition — introduced when v1.5 was written today. Earlier architecture versions had less rigorous changelog discipline. **This is another instance of F10's revised principle: discipline-evolution-in-flight, this time inside the architecture-change workflow itself.** The workflow that produced v1.5 is not the workflow that produced v1.0 through v1.4; it has improved through use, and the improvement landed at the v1.5 boundary.

**Q11.3 — What gets versioned, what doesn't.**

**Versioned (`v1_X.md` filename suffix):**

- `CHANNEL_STRUCTURAL_ARCHITECTURE_v1_X.md` — channel-level structural commitments inherited by every episode.
- `EP1_STRUCTURAL_ARCHITECTURE_v1_X.md` — episode-level structural application of channel architecture.
- `LATENT_SYSTEMS_PROJECT_BRIEFING_v1_X.md` — project-level briefing (positioning, market frame, strategic rationale).
- `PROJECT_ARCHITECTURE_v9.md` — process architecture (filesystem, color pipelines, asset cataloging). Note: uses simple integer versioning (v9), not v1.X — different lifecycle pattern, see below.

**NOT versioned:**

- `HANDOFF_*.md` — session-bounded; date-stamped instead of versioned. Multiple in same date allowed (continued, continued_2).
- `NOTES.md` (per-shot recipe authority) — append-only working docs; no version.
- `FILESYSTEM_MANIFEST.md` — auto-regenerated; no version (the regen IS the lifecycle).
- `tools/router_log.md` — append-only log; no version.
- `tools/router_config.yaml` — has internal `version` field but no filename version.

**Edge cases worth examining:**

- `EP1_PROJECT_HANDOFF_v10.md` — versioned but called a handoff. Either the handoff convention drifted or this doc is misnamed (might actually be more like an EP1 production-state doc, not a session handoff).
- `EP1_BROLL_PLAN_v1.md` — versioned at v1, never bumped. Might just be "this is the canonical broll plan, future revisions would v2." Pre-emptive versioning.
- `LATENT_SYSTEMS_EP1_FINAL_SCRIPT_v3.md` — versioned. Scripts version with whole numbers because each version is a wholesale revision (v2 → v3 cut entire paragraphs from §17). Closer to "draft 1, draft 2, draft 3" than semver.

**The pattern, made explicit:**

A doc gets version-locked when:
1. Decisions in it are structurally consequential (changing them affects canonical material downstream).
2. The doc has a clear "lock" event (Joseph signs off on a version; the version becomes operative; later changes require justification).
3. Predecessor versions need to be recoverable (because someone — including Joseph — might need to verify "what did we agree to in v1.3 specifically?").

A doc does NOT get version-locked when:
1. It's session-bounded or working (handoffs, NOTES, logs).
2. It's auto-regenerated (manifest).
3. Its purpose is operational, not structural (router config — which uses an internal version field as needed but doesn't filename-lock).

**The integer-vs-v1.X distinction:**

Project architecture uses simple integer versions (v9) because its changes are typically additive process refinements. Less semver-y, more just "v9 supersedes v8."

Channel/EP1/Project Briefing architecture uses v1.X because those have semantic-version flavor — major.minor signals scope. v1.X (today) all minor refinements; if a structural rethink happened (e.g., changed channel positioning fundamentally) that'd be v2.0.

**Pattern summary, single sentence:** Architecture and structurally-consequential planning docs version-lock with full-document rewrites + in-doc changelog + archive lifecycle for predecessors; session/working/auto-generated docs don't version, they date-stamp or append.

### Friction finding F11a: Cross-Claude handoff is a sub-case of F6 — leaves no filesystem trail even between filesystem-aware instances

**Severity: MEDIUM-HIGH.**

Q11's answer arrived via parallel Claude instance — a different chat in the same project, with read access to the same filesystem, running the same architecture-change workflow firsthand. Both instances had filesystem access. Yet the exchange between them happened entirely through Joseph as copy-paste courier. The audit Claude could not see the source Claude's prior context; the source Claude cannot see the audit Claude's findings register.

This is structurally a sub-case of F6 (cross-AI handoff leaves no filesystem trail). F6 addressed handoff between Claude and other AIs (Perplexity, ChatGPT, Grok, Gemini). F11a addresses handoff between Claude instances. The pattern is the same: filesystem access on both ends doesn't help when the transport layer is human copy-paste.

**Why this matters:**

The cross-Claude handoff just demonstrated all three F6 sub-problems plus a new one:
1. **No filesystem trail.** The Q11 answer existed only in the source Claude's chat history until Joseph copy-pasted it. If the source chat closes, the answer's reasoning is irrecoverable except through what got copied.
2. **No automatic attribution.** The audit Claude correctly refused to bank silently and flagged the depth shift. The discipline worked. But the discipline only worked because the audit Claude noticed. A more credulous instance might have banked it as "Joseph said," replicating exactly the problem F6 names.
3. **Joseph as transport layer = bottleneck and integrity check.** Joseph judged which Claude to ask, transported the answer, and verified accuracy. That's three jobs for one human in one round-trip. Scales poorly.
4. **NEW — instance discoverability.** Joseph knew which parallel instance to ask because he was tracking it himself. There's no project-side index of "active Claude instances and what context they hold." If Joseph forgets which instance has v1.5 context, the institutional knowledge is irretrievable until that chat surfaces in his memory.

**v1 implication:**

If the app supports cross-AI capture (per F6 option 2), it should support cross-Claude-instance capture as a sub-case. Specifically:
- A "paste cross-Claude answer" action that captures: the source chat URL/identifier (when known), the question asked, the answer received, the verification note from Joseph ("verified matches my read"), and the relevance binding (which decision/finding/architectural change does this answer inform).
- Output goes to `cross_ai_log/` (per F6) or a more specific `cross_claude_log/` if the volume warrants the split.
- Captured answers become first-class durable artifacts that future audit / synthesis work can reference by path, not by chat-history search.

This is still v1+v2 boundary territory. F6 deferred the decision; F11a sharpens the case for option 2 (provide a simple capture surface) because cross-Claude handoffs are likely to be more frequent than cross-AI-to-other-vendor handoffs.

### Friction finding F11b: Multi-instance Claude work has real value but no infrastructure

**Severity: MEDIUM.**

The parallel Claude instance had context and answer-quality the audit Claude couldn't replicate from inside their session. The audit instance has been deep in audit framing for ~6 hours; the source instance has been deep in v1.5 architecture work today including firsthand drafting. Both perspectives are valuable for the audit, but the source instance's perspective on Q11 was substantially more grounded.

**Asking the right Claude the right question is itself a workflow pattern.** It currently runs entirely on Joseph's judgment about which instance to ask, and entirely via copy-paste transport. The pattern is unsupported by tooling.

**v1 question worth flagging for the spec:**

Is "ask another Claude instance with different project context" a first-class action the app should support, or is it a cross-AI handoff (Flavor 1) that lives outside the app?

Three honest options:

1. **Out-of-scope for v1.** Cross-Claude-instance work remains ad-hoc. Joseph manages instance-routing manually; copy-paste is the transport. The app captures the *result* (per F11a above) but doesn't orchestrate the *exchange*.

2. **Capture surface only (per F11a).** App provides a structured way to record the exchange after the fact. No orchestration, but the work becomes durable.

3. **Multi-instance orchestration as v1 feature.** App tracks active Claude instances per project (likely impossible without Anthropic-side support), routes questions to the appropriate instance based on context, and captures the answer automatically. This is probably v3+ territory and may require infrastructure that doesn't exist yet.

**Recommendation: Option 2 for v1.** Capture is high-value and low-cost. Orchestration is high-value but requires capability that may not exist.

---

## Parallel-Claude calibration round (banked 2026-05-03)

**Source:** Same parallel Claude instance that supplied Q11. Joseph went back and asked the parallel instance to weigh in on each prior finding, then transmitted the calibration via copy-paste. Transmission = manual copy-paste; Joseph's role = directed the calibration pass and verified each input matched his read; audit Claude's role = banked with attribution per F11a discipline.

This is itself the second cross-Claude handoff of the session, demonstrating that the pattern named in F11a/F11b is a recurring workflow input, not a one-off.

The calibrations below extend or sharpen prior findings. Original framings remain in place above; the calibrations append rather than replace, preserving the audit trail of how findings evolved under cross-Claude review. (This is itself a worked example of F10's discipline-evolution-tolerant principle applied to the audit doc.)

### F1 extension — prompts have NEVER been on filesystem

The original F1 framing said prompts "live in chat scrollback." The sharper framing: prompts have never been on filesystem across the project's entire three-week lifespan. Every MJ / GPT / Kling prompt that produced canonical output exists only in chat scrollback. The recovery path through "ask Claude to reprint" has also become unreliable as the multi-chat / multi-instance pattern (per M1 below) emerged this week — different chat instances have different scrollback and may not have the relevant prompt.

F1's HIGH severity stands. The extension reinforces it: this isn't a recent oversight, it's the project's operating pattern from day one.

### F2 quantification — re-derivation tax is ~1 hour per session-restart

The original F2 framing said re-derivation is "real warm-up tax." The parallel Claude provided concrete quantification: today's session opened with substantial concept reconstruction. Claude had to read three handoff docs, the v1.5 architecture, the predecessor handoff, and walk through Phase 2 framing before working could start. **Roughly the first hour of every session-restart is spent on concept-state reconstruction.**

That's a meaningful number. At even 3-4 session-restarts per week of compressed-iteration tempo, that's 3-4 hours/week of pure reconstruction overhead. v1's persistent concept data model (per F2's v1 implication) directly addresses this — the warm-up tax becomes "open the app" rather than "re-read seven docs."

### F3 sharpening — translation layer isn't "Claude" generally, it's "Claude-instance-with-project-history"

Original F3 said tool-grammar knowledge lives in Claude. Sharper: tool-grammar knowledge isn't uniform across Claude instances. The working Claude instance knows MJ v7 syntax + GPT Image 2 strengths + Kling motion vocabulary because **it's been drafting prompts for each in this project**. A fresh Claude instance with no project context drafts substantially worse prompts.

**v1 implication, sharpened:** The app needs to materialize that accumulated history into config or docs that any fresh Claude API call can use. Not just "send concept + target tool to Claude API" — send concept + target tool + accumulated tool-grammar config that captures what's been learned about MJ/GPT/Kling/etc. through use. This is the difference between "API call to a generic Claude" and "API call to a Claude prepared with project-specific tool-grammar knowledge."

This is more substantial work than F3's original framing implied. It's a tool-grammar knowledge base that v1 needs to maintain — possibly auto-populated from successful prompt+output bindings (per F1) over time.

### F4 third layer — conceptual chat-to-chat references

Original F4 named two reference layers: textual prompt-to-prompt (rare), implicit render-to-render via craft vocabulary (common). Parallel Claude added a **third layer F4 missed**: prompts reference prior CONCEPTS that lived in chat.

Concrete example: when the parallel Claude drafted D4 P3 with "1940s archival" they were anchoring on the Skinner-box H#3 hero shot's register, which Joseph and Claude discussed weeks ago in chat. That conceptual reference isn't in any doc, isn't in the prompt text, isn't in any image — it lives entirely in held context.

**Three layers of reference, ranked by ephemerality and consequence:**

1. **Textual prompt-to-prompt.** Rare. Most durable when present (the text is the reference).
2. **Implicit render-to-render via craft vocabulary.** Common. Moderately durable via the renders themselves.
3. **Conceptual chat-to-chat.** Frequent. Most ephemeral. Most consequential — these references shape the prompt's structural choices in ways downstream renders can't recover.

**v1 implication for F4 (sharpened):** lineage-anchoring isn't just about pointing to prior renders. It's about capturing the conceptual reasoning that connects prompts across time — including conceptual references to prior chat-conversations. This pushes lineage-anchoring closer to "concept thread" than "render-pointer."

### F7 leverage ranking — three highest-leverage sub-flavors

Original F7 confirmed all six sub-flavors as active pain points but treated them as equal. Parallel Claude's leverage ranking:

1. **Failed-generation overhead (sub-flavor 5).** Highest leverage. Directly blocks learning loops — can't tell what worked vs didn't without manual comparison work.
2. **Batch identification (sub-flavor 4).** Second highest. Directly blocks accurate audit — 20 returns with no prompt-link is the audit problem made visible.
3. **Reference-image re-uploading (sub-flavor 3).** Third highest. Directly blocks iteration speed.

Lower-leverage (real friction but UX-grade rather than learning-loop-blocker):
- Tool-tab switching (sub-flavor 1)
- Dead time during generation waits (sub-flavor 2)
- Naming friction at generation-time (sub-flavor 6)

**v1 implication:** v1 should address all six (the workspace surface gives most of them for free), but **prototype priority order should follow the leverage ranking.** Build failed-generation tracking + batch identification + reference image persistence first; tab-management and dead-time-utilization can land in later v1 iterations.

### AD-1 caveat — Path B's vulnerable spot is the clipboard handoff

AD-1 banked horizontal-slice as the v1 architecture. Parallel Claude flagged the architecturally vulnerable point: **for tools without API access (MJ, Kling), v1 has to make copy-paste-into-browser feel native rather than awkward.** The clipboard-and-watch-Downloads pattern is the most fragile part of Path B. If clunky, users route around the app and paste manually like today — at which point the persistent-binding benefit (F1's solve) evaporates because the prompt was never captured by the app.

**v1 implication:** the clipboard handoff UX is prototype-priority. If it's clunky, the entire horizontal-slice value proposition collapses for half the toolchain. Specific design considerations:
- The app should make "copy this prompt and open MJ" a one-button action that updates app-side state (prompt captured, expecting return) at the moment of copy.
- The watch-Downloads logic (already encoded in the existing router) needs to feel instant — when MJ generates, the file should appear in the app's batch view within seconds of landing in `~/Downloads/`.
- If the user pastes manually outside the app, the app should detect the orphan return and offer to bind it to the most recent uncaptured prompt.

This sharpens AD-1 without changing the decision. Horizontal-slice still right; the clipboard handoff just earned a "prototype-critical" flag.

### F8 sharpening — multi-AI evaluation is already systematic discipline, plus dual audit modes

Two extensions to F8:

**(1) Multi-AI evaluation is deliberate methodology, not casual asking.** The original F8 framing said Joseph "asks AIs for opinions." Sharper: the cross-AI calibration framework is deliberate per the project's role calibration (Perplexity for resistance, ChatGPT for adversarial structural read, etc.). The audit phase already has multi-AI evaluation as systematic discipline — it's just unsupported by tooling. v1's AI-assisted evaluation flow should support this systematic discipline, not invent a casual one.

**(2) Audit duration variance tracks something specific.** Original F8 framing said duration ranges minutes-to-an-hour. Sharper:
- **Quick batches** resolve fast when v1.5 craft vocabulary holds — the vocabulary is itself a fast-pass filter.
- **Long batches** take an hour when vocabulary doesn't hold or when the question is "is this register working at all" rather than "is this craft working."

**v1 implication:** the audit interface should support both modes:
- **Quick-pass-against-known-criteria** for batches where vocabulary is the verdict ("does this hold the four-element craft test? Y/N").
- **Deep-evaluation-against-emerging-criteria** for batches where the question is structural ("is this register the right register at all").

These modes have different UI needs. Quick-pass needs minimal friction (advance, mark, advance, mark). Deep-evaluation needs full context (concept text, lineage, AI consultation).

### F9 sharpening — "system docs" enumerated + un-hero'ing convention specified

**Doc-level update enumerated:** Today's hero promotions for the 8 craft renders + 2 GPT density exemplars + 2 standalone exemplars wrote into three concrete places:
1. `shared/render_craft_exemplars/README.md` (recipe authority for the exemplar set)
2. `docs/CHANNEL_STRUCTURAL_ARCHITECTURE_v1_5.md` (citing exemplars as sub-staple #10b reference)
3. `docs/HANDOFF_2026-05-03.md` (banked at session end)

All three updated by Claude at hero promotion time, with Joseph's approval. **F9's "ad-hoc" finding is correct, but the ad-hocness is partly because Claude figures out which docs to update each time, not following a defined rule.** The decision logic isn't captured anywhere — it's reasoning that happens fresh in chat each time.

**Un-hero'ing convention specified:** Per channel staple #12: `_DEPRECATED_<reason>.png` rename + move to `_work/<context>/_DEPRECATED_<category>/` directory. **Reason field is required, not optional.** v1 should enforce this when the un-hero action runs — refuse to proceed without a reason note.

**v1 implication for F9:** the atomic hero-promotion action should encode the doc-update-locations as part of its config (not Claude-decides-each-time). The set of locations may evolve (per F10), but each invocation should write to the currently-defined-set deterministically.

### F10 sharpening — variance shows trajectory; templates should version too

Original F10 said NOTES.md variance reflects discipline-evolution-in-flight. Parallel Claude sharpened: **§1.C NOTES.md is exemplary because it was written most recently, representing current discipline. Earlier NOTES.md (h2_face_glow as status-pending, h4_match_cut as technical-spec-heavy) represent earlier discipline versions. The variance shows the trajectory of how NOTES.md authorship has matured over three weeks.**

**v1 implication, sharpened:** the app's NOTES.md TEMPLATES should themselves be versioned (like architecture docs). When discipline evolves, you bump template version. Existing NOTES.md files get flagged as "written against template v0.3, current is v0.5" — not auto-upgraded, just marked for revisit. Discipline-evolution-tolerant per F10's design principle, with versioning as the mechanism.

This is a meaningful concrete-spec addition. Template-as-versioned-artifact rather than template-as-static-form.

### Q10 extension — manifest regen pattern is the most extreme discipline-evolution case

Original Q10 banked manifest regen as a non-finding because the discipline hadn't stabilized. Parallel Claude added: the manifest regen pattern was created **today, less than 12 hours ago.** Discipline around it has had less than a working day to develop. This is the most extreme case of discipline-evolution-in-flight in the entire project — critical infrastructure AND brand-new.

**Implication:** worth noting because **it'll happen again as v1 itself gets built.** There will be moments when v1 introduces tooling whose discipline-pattern doesn't exist yet (the audit viewer's first weeks of use; the concept browser's first iterations; the cross-Claude capture surface's first deployments). The discipline-aware-and-discipline-tolerant principle applies recursively — v1 itself will produce its own moments of "this tool is brand-new, discipline hasn't stabilized."

This is worth keeping in mind during v1 build. Don't lock down workflow rules around tools that haven't been used long enough to know what their workflow actually is.

### Q11 — confirmation that in-doc changelog convention is itself recent

This input duplicates what's already in Q11.2's "Important addition" subsection. Parallel Claude confirmed it independently when calibrating: in-doc changelog convention is a v1.5 addition, earlier architecture transitions captured refinement-history in handoff docs rather than the architecture doc itself. v1.5 promoted the changelog into the architecture doc proper. Already banked above.

---

## Meta-findings on workflow-of-the-audit (banked 2026-05-03)

These are findings about the audit-conducting workflow itself, surfaced during the parallel-Claude calibration round. They're meta-level — findings about the process that produced the findings — but they're worth banking because they describe patterns that v1 should support if v1 is going to be where work happens.

### Friction finding M1: Multi-Claude-instance pattern is a workflow innovation that emerged this week

**Severity: MEDIUM.**

The pattern of running parallel Claude instances on related-but-distinct work in the same project is a real working pattern Joseph is using right now. Today: Phase 2 evaluation in one chat, this audit in another, possibly more elsewhere. **This pattern emerged this week**, was not previously a workflow primitive, and is distinct from F6's cross-AI handoff (which covers different AI products — Claude / Perplexity / ChatGPT / Grok / Gemini).

**M1 is same-AI different-instance handoff with shared filesystem access.** Different beast structurally:

- F6: different AI products, different vendors, no shared filesystem, copy-paste transport.
- M1: same AI product, different chat instances, shared filesystem access, copy-paste transport.

Today's Q11 cross-instance handoff is the live demonstration. The parallel Claude instance had context the audit Claude couldn't replicate (firsthand v1.5 drafting, current Phase 2 work, etc.), but the only way to access that context was via Joseph as transport layer.

**Why this matters as a separate finding from F11b:**

F11b is "multi-instance Claude work has real value but no infrastructure." M1 names the specific pattern: **parallel instances on related-but-distinct work in the same project**. F11b is the friction; M1 is the pattern that produces the friction.

Distinguishing them matters because v1 needs to decide:
- Whether to build infrastructure for the *pattern* (M1) — e.g., persistent project-state index that any instance can read, cross-instance message passing.
- Whether to just provide capture for the *result* (F11b option 2) — accept that instance routing remains Joseph's job.

These are different scopes. M1 is a more ambitious framing.

**v1 implication:** Joseph's workflow already includes multi-instance coordination as a capability. The app shouldn't invent it; it should support whatever discipline emerges around it. Per F11b's recommendation, v1 = capture surface (Option 2). M1 confirms the scope of what's being captured: same-project multi-instance work, not just inter-vendor handoffs.

### Friction finding M2: The audit is generating findings about its own workflow

**Severity: LOW-MEDIUM.**

Tonight's audit-conducting workflow has been: Joseph asks questions, transcribes compressed answers, transcribes Claude responses, escalates questions to parallel Claude instance when depth is needed, transcribes those answers back. **That's a workflow pattern in itself — extended-structured-interview-with-AI.** It probably has its own friction profile worth surfacing.

**Surfaced friction in extended-structured-interview-with-AI:**

- Question/answer pairs accumulate in chat scrollback (same F1 problem, applied to interview Q&A rather than prompts).
- Transitioning between instances (F11a/M1 problem) when depth requires it.
- Long sessions (~6 hours tonight) test attention and produce compounding context.
- Depth-shifts in answers signal external sources, requiring source-attribution discipline.
- The audit doc itself is the durable artifact — losing the chat would lose the working state of the interview, but the doc captures the conclusions.

**v1 implication, modest:**

If v1 is going to be where work happens (per F7's workspace ambition), this kind of extended interview pattern should also work in v1. Not as a primary feature for v1, but worth ensuring the app's capture surface (per F11a) handles long-form Q&A as a content type, not just one-off question-answer pairs.

This is a low-priority finding for v1 spec. Banked for completeness because the audit itself is a working example of a pattern the app might eventually need to support.

### Friction finding M3: Compressed-text answers are a primary input pattern

**Severity: LOW-MEDIUM.**

Tonight's interview ran on compressed answers — "copy paste, no" / "B" / "yes" / "1" / "renamed and copied to new folder" / "When you remember to/When Claude prompts you to". **This is efficient, not lazy.** Substantive, fast, low-cost for Joseph; doesn't break flow; works.

But the pattern depends on the AI being able to **expand compressed answers into full findings using accumulated context.** The audit Claude has been doing that all night — taking "B" and producing F7's full v1 implication, taking "1. renamed and copied to new folder within the file system from the downloads folder" and producing F9's atomic-action specification, etc. That's heavy lifting on the AI side.

**v1 implication:**

If v1 supports interview-style flows or any extended back-and-forth with Claude, **"compressed-text answer + AI expansion" should be a primary input pattern to support.** This means:
- The app should not require structured forms or long-form input from Joseph by default. Short-answer / one-letter / yes-no responses should work.
- The AI on the other end (Claude API) needs project-context loaded so expansion can work. This connects to F3's sharpened framing — the app needs to materialize project history so any Claude API call has the context for expansion.
- Compressed answers should be captured verbatim alongside the AI's expansion, so the audit trail shows what Joseph actually said vs what Claude inferred.

This is a modest finding but worth banking because it shapes how v1 handles input. The default-form-fields pattern would actively work against Joseph's working style.

---

### Q12 — Cross-document synthesis

**Source attribution:** Q12 answer was sourced via a third cross-Claude handoff in this session. Same parallel Claude instance (Phase 2 evaluation chat) that supplied Q11 and the calibration round. Direct involvement in v1.5 closure today including the cross-doc updates being audited. Joseph copy-pasted the answer after verifying it matches his read. Banked per F11a discipline.

**Q12.1 — Authorship pattern for multi-doc updates.**

Pattern is **deliberately ordered serial, not parallel or batch.** Today's v1.5 closure touched 8 artifacts: architecture + exemplar README + handoff + 2 NOTES.md addenda + rename manifest + Claude Code instructions. Order: most canonical doc first (architecture), then artifacts referencing it (README, NOTES.md addenda), handoff last.

Cross-references embedded in-place during drafting, not added in a second pass — they encode reasoning that emerges during writing.

**No "all related docs" tooling exists.** The relationship between docs is encoded in Claude (the parallel instance) drafting them in sequence with each in mind. The discipline lives in held-context, not on filesystem.

**Failure mode that surfaced today:** Image 17 hybrid-dad scope mismatch between exemplar README and canonicalized state. Joseph caught it because he noticed; nothing systematic would have caught it. **Cross-references desynchronize when drafting order is interrupted** (correction mid-draft, chat ends, attention shift).

**v1 implication:** doc-set concept. When a structural commitment changes, the app should surface what other docs reference it and prompt coordinated updates. **Not auto-write** (would impose discipline against F10's discipline-evolution principle); **auto-flag.** Joseph writes; app prevents forgetting.

**Q12.2 — Consistency-checking when channel architecture changes.**

Honest answer: **no systematic check happens.** Assumed-on-faith with selective Claude-prompted spot-checks.

Today's v1.4 → v1.5: the parallel Claude explicitly noted EP1 architecture stays at v1.4 (single judgment call). It did NOT re-read project briefing v1.3 to verify alignment, did NOT re-walk channel staples #1-#15 to check whether any other staple needed updating, did NOT systematically review EP1 architecture for conflicts.

**This works for scope-bounded changes** (v1.5 was sub-staple addition with no canonical structure changes). **It's brittle for structural changes:** v1.2's AI-native positioning reframe should have triggered systematic review of project briefing + EP1 architecture. Project briefing was bumped; EP1 architecture wasn't systematically reviewed — integration happened opportunistically when EP1 work surfaced inconsistencies.

The discipline that would catch this — an "inheritance audit" running after channel architecture lock, walking every inheriting doc and flagging reference points — is missing.

**v1 implication:** when the app holds canonical docs as structured objects, inheritance relationships live in the data model. v1.5 architecture marks itself as "supersedes v1.4, inherited by EP1 v1.4 (verify no conflict)." On lock, the app generates a verification checklist. Joseph verifies; app makes sure nothing gets forgotten.

**Q12.3 — Cross-doc references / broken-link risk.**

Sharpest of the three sub-questions. Discipline is partial; broken links happen and get caught late, opportunistically.

**What works:** channel staple numbering has been stable v1.0 → v1.5 (staples #1-#15 not renumbered). Existing "channel staple #11" references still resolve.

**What doesn't:** v1.5 introduced sub-staple structure under #10 (#10a, #10b). Any doc previously referencing "channel staple #10" is now ambiguous — could mean parent or sub-staple a. **This ambiguity exists right now in undetermined places** (NOTES.md files, handoffs, EP1 architecture). No mechanism catches it.

§1.C NOTES.md specifically references "channel staple #11," "#6 (subject-imagery)," "#9 (Daniel tonal register)." If v1.6 renumbers any of those, §1.C NOTES.md is silently wrong. Discovery happens opportunistically when the next reader follows the reference.

**Asymmetry worth banking:** rigorous discipline around **forward references** (v1.5 cites prior versions cleanly via Refinement history + supersession markers). Weak discipline around **backward references** (when new version changes structure, existing references INTO new structure from older docs aren't checked). That's the failure mode.

**v1 implications, three layers:**

1. **Reference-as-data, not text.** Staple references should be structured (ID-based, anchor links), not free text. App holds resolution.
2. **Version-pinned references.** §1.C NOTES.md written against v1.4 resolves against v1.4. When v1.5 ships, app shows: "§1.C NOTES.md references 3 staples in v1.4. v1.5 changed 1 of those (#10 split). Review reference."
3. **Stale-reference inventory.** At any point, app answers "what docs reference structures that have changed since they were written?" That inventory is finer-grain version of Q12.2's inheritance audit.

### Friction finding F12: Cross-document synthesis runs on Claude's held context, not on data model

**Severity: HIGH.**

Cross-document work — coordinated multi-doc updates, inheritance verification when canonical docs change, reference-link maintenance across version-locks — currently runs on:
- Claude's held context during drafting (Q12.1 ordering discipline)
- Joseph's memory and Claude-prompted spot-checks (Q12.2 consistency-checking)
- Opportunistic discovery when references break (Q12.3 broken-link discipline)

None of it is in the data model. None of it is queryable. None of it survives chat-context dying.

**Severity is HIGH because the failure modes compound:**

- Multi-doc updates desynchronize when drafting order is interrupted.
- Architecture changes propagate inconsistently to inheriting docs.
- References break silently and get caught opportunistically.

These are the same gaps F1 (prompt-output binding) and F2 (concept-state in chat) name, but applied at the document-relationship layer rather than the prompt-render or concept layers. **The pattern is identical: structurally-consequential information lives in held context rather than on filesystem.**

**v1 implication:**

Three concrete v1 affordances:

1. **Doc-set as data model object.** Parallel to "concept as data model object" from F2. Doc-set captures: which docs are related, how (inheritance / reference / co-update), what the cross-references actually point to (structured, not free-text). When any doc in the set changes, the app surfaces affected relationships.

2. **Inheritance audit at lock time.** When channel architecture v1.4 → v1.5 ships, the app generates a verification checklist of every inheriting doc (EP1 architecture, project briefing, NOTES.md files referencing channel staples, handoffs). Joseph verifies each item. Not auto-update — auto-flag. Per F10's discipline-evolution principle.

3. **Stale-reference inventory as a queryable view.** The app answers "what docs reference structures that have changed since they were written?" at any time. Surfaces version drift before it becomes invisible. §1.C NOTES.md written against v1.4 marked as "references staple #10 — split into #10a/#10b in v1.5; review."

**Reference-as-data, not text.** This is the architectural commitment that makes the other two affordances tractable. Free-text "channel staple #11" can't be resolved by the app; structured `{type: staple_ref, version: v1.4, id: 11}` can. v1's data model needs this primitive, possibly with light syntax in markdown that the app parses (e.g., `[[staple#11]]` or similar).

This is substantial work. F12 is high-leverage for long-term project health: every architecture escalation (v1.6, v2.0, eventual EP2 architecture, channel #2 if it happens) makes the cross-doc relationship problem worse. Without infrastructure, the relationship-debt compounds. With F12 addressed, the cost of architectural change scales linearly rather than quadratically.

### Friction finding M4: Cross-document structural relationships live in Claude's held context and Joseph's memory, not in data model

**Severity: HIGH.** This is the highest-leverage meta-finding banked tonight.

**M4 is the pattern that F1, F2, F4, F11a, and F12 all instantiate at different layers:**

- F1: prompt → render binding lives in held context (chat scrollback)
- F2: concept-state lives in held context (chat-conversation context)
- F4 (third layer): conceptual chat-to-chat lineage lives in held context
- F11a: cross-Claude handoff lives in held context (no filesystem trail)
- F12: cross-document inheritance, coordination, references live in held context

**The unifying frame:** the project has rigorous filesystem discipline for *artifacts* (renders, audio, scripts, architecture docs as artifacts). The project has zero filesystem discipline for *relationships between artifacts*. Relationships live in Claude's held context and Joseph's memory, both of which are ephemeral compared to the artifacts they connect.

**Why severity is HIGH and why M4 reframes the v1 spec:**

Until tonight, the v1 spec was structured as "build the missing two-thirds of the pipeline" — pre-Downloads workspace + post-routing tooling around the existing router. M4 reframes the v1 ambition: **build the relationship layer the project doesn't have.**

That's a different framing. It's not "improve generation tooling" or "improve audit tooling" — it's "give the project a relationship-aware data model so artifacts can reference each other durably." The generation/audit/promotion features become surfaces over the relationship layer; the relationship layer is the structural commitment.

**Why this matters as a separate finding from F12:**

F12 names the cross-document case specifically. M4 names the underlying pattern that produces F1, F2, F4, F11a, F12, and likely future findings the audit hasn't yet surfaced. M4 is the structural insight that explains why the project's friction clusters where it does: the project has gotten very good at making artifacts durable, and hasn't yet built (because there hasn't been time) the layer that makes relationships between artifacts durable.

**v1 implication, structural:**

The v1 spec should be organized around two axes:

- **Axis 1: artifact layer.** Concepts, prompts, renders, audits, hero promotions, NOTES.md, architecture docs — all the things F1-F11b address as data model objects.
- **Axis 2: relationship layer.** Bindings (prompt ↔ render, render ↔ winners/, hero ↔ NOTES.md), lineages (render → render → render via craft vocabulary; concept → concept → concept via chat), inheritances (channel arch → EP1 arch → NOTES.md), references (NOTES.md → channel staple by ID).

These are separate but interdependent. The artifact layer is mostly what F1-F11b name. The relationship layer is what M4 / F12 / F4-third-layer / F11a name. **v1 cannot solve the artifact layer alone — the friction findings make sense only when the relationship layer is also in scope.**

**Concrete v1 design implication:**

The data model needs first-class relationship objects, not just first-class artifact objects. A concept doesn't just exist; it has prompts derived from it (1:N), prior concepts that anchored it (M:N), renders produced from it (1:N via prompts), hero-promotions made from those renders (subset). These are queryable graph relationships, not just attributes on artifacts.

This is more than F2's "concept as structured object." F2 said concepts need persistence on filesystem. M4 says concepts need *relationship-aware* persistence on filesystem — and so do prompts, renders, NOTES.md files, architecture docs, and every other structurally-consequential artifact.

**Recommendation: M4 reshapes the v1 architecture.** Worth synthesis discussion before drafting v1 spec proposal. The relationship layer is non-trivial to design well; getting it wrong locks in cost for every later iteration.

---

## Remaining Section 3 questions (still to interview)

- **Memory / handoff** (already partially answered via F5; deferred).
- **Editorial assembly (downstream)** (Q13 territory).
- **Friction hotspots within Phase 3 beyond F8/F9/F10/F11a/F11b/F12/M1/M2/M3/M4.**

