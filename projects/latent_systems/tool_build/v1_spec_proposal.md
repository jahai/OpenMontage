# LATENT SYSTEMS — Tool-build v1 Spec Proposal

**Date:** 2026-05-04
**Status:** v0.5 DRAFT — incorporating AD-5 enforcement-infrastructure carve-out for git pre-commit hook
**Source material:** Workflow audit at `tool_build/workflow_audit_v1.md` + `tool_build/workflow_audit_v1_section3_addendum.md` + `tool_build/workflow_audit_v1_section3_closure.md`. Phase 1 design notes at `tool_build/phase1_design_notes.md`.
**Build approach:** AI-assisted via Claude Code

---

## Document purpose

This doc is the v1 specification for a local web-server-plus-browser-frontend application that addresses the gaps surfaced by the workflow audit. It synthesizes 13 friction findings, 5 meta-findings, 5 architectural decisions, 1 design principle, 1 enforcement-infrastructure pattern, and 7 confirmed open-question answers into a buildable v1 specification.

This is not the audit doc. The audit doc captures *what hurts and why*. This doc captures *what gets built and how*.

If terms or framings here seem under-explained, the audit doc is the reference.

---

## What this app is (one paragraph)

A local-web-server-plus-browser-frontend application for AI-native video production at unusual discipline density. It produces structurally-disciplined assets and the relationships between them; it integrates with OpenMontage's compose stage at a defined boundary. v1 is single-user, local-only, and Latent-Systems-specific. The app captures concept persistence, prompt-output binding, lineage anchoring, audit verdicts, hero promotions, NOTES.md authorship, and cross-AI/cross-Claude exchange — all as durable filesystem artifacts with relationships between them. It serves a project where the human makes structural decisions and AI executes against those decisions.

---

## Honest scope statement (v0.4 — sharpened third framing per cross-Claude review)

The earlier framing "v1 = match what Joseph already does, faster" is **incomplete and worth being explicit about.** The audit findings genuinely justify capabilities beyond streamlining — concept browser, doc-set data model, discipline-drift query, cross-AI capture surface, OpenMontage serialization are all *new capabilities* the project doesn't currently have at all.

**Sharpest framing (v0.4):** v1 is a **relationship-layer infrastructure with workflow surfaces over it.** The substance is the relationship layer (Layer 2 of the architecture per M4); the surfaces are nine features that make the layer accessible.

This third framing matters because it disciplines build prioritization. When scope creep tempts during Phase 1-3 build, the test is: **does this proposed feature make Layer 2 more accessible, or is it Layer 1 polish?** Layer-2-accessibility additions are in-scope. Layer-1 polish is out-of-scope or v2+.

Examples of how this test resolves ambiguous calls:

- "Add a richer concept-detail view with tabs and inline editing." → Layer 1 polish. Out of scope.
- "Add ability to query 'all concepts that share a register' across the database." → Makes Layer 2 (relationship layer) more accessible. In-scope.
- "Add prompt-syntax syntax highlighting in the drafting UI." → Layer 1 polish. Out of scope.
- "Add ability to query 'all renders that anchor against this concept'." → Makes Layer 2 accessible. In-scope.
- "Add custom theming / dark mode toggle." → Layer 1 polish. Definitely out of scope.

**Earlier framings, preserved:**

This is a substantial application, not a workflow-streamliner. Worth budgeting against this honestly rather than against a smaller framing.

The "match what you already do, faster" framing applies cleanly to features 4 (audit viewer), 5 (hero promotion), 6 (NOTES.md authorship) — these are streamlining what exists. Features 1 (concept browser), 7 (cross-AI capture), 8 (OpenMontage serialization), 9 (discipline-drift query) are net-new capabilities. Features 2 (prompt drafting), 3a/3b (generation triggering) are hybrids.

**Risk-variance flag among net-new features (v0.4 addition per cross-Claude review):**

Not all net-new features carry equal risk. Worth banking the variance:

- **Feature 1 (concept browser): low-risk net-new.** Data shape (concept-as-object) is well-specified by the audit. UI shape is conventional list-and-detail. Build risk minimal.
- **Feature 8 (OpenMontage serialization): medium-risk net-new.** Schema alignment with OpenMontage's `edit_decisions` and `asset_manifest` requires reading those schemas carefully and may surface fit issues; serialization itself is mechanical.
- **Feature 7 (cross-AI capture): high-risk net-new.** UX shape is genuinely uncertain. The "compressed-input + AI-expansion" pattern (per M3) is a primary input flow but hasn't been built before. Risk that the surface feels clunky and Joseph routes around it.
- **Feature 9 (discipline-drift query): high-risk net-new.** UX shape uncertain. Cross-artifact-type queries surfaced as a status badge + drill-down view is conceptually clean but not architecturally trivial; how it actually feels in use is the open question.

**If Phase 1 trips, it'll trip on Feature 9, not Feature 1.** Phase 1's build sequence (in Phase 1 design notes) reflects this — Feature 9 lands in Week 4, after the data substrate is in place to support it. If Feature 9 turns out to need substantial UX iteration, Phase 1 ends with that iteration rather than starting with it.

---

## What this app is NOT

- Not a replacement for OpenMontage. OpenMontage handles compose and render; this app handles upstream-of-compose.
- Not a generic AI-native video tool. v1 is Latent-Systems-specific by design.
- Not multi-user or cloud-based. Single-user local-only.
- Not an editorial timeline. Editorial assembly happens in OpenMontage / Remotion.
- Not a script editor. Script work happens in markdown files Joseph and Claude already use.
- Not an asset-generation tool. Asset generation happens in MJ / GPT Image 2 / Kling / ElevenLabs / etc. via API or browser handoff.
- Not a project-state index for arbitrary projects. v1 is one project's tool, not a generalizable platform.
- Not a backfill tool for three weeks of pre-v1 prompts (per AD-3). Existing canonical material stays as-is; v1 is forward-only.

---

## Architectural decisions

### AD-1: Horizontal-slice across all tools (per F7)

The app provides a workspace skeleton across all generation tools at lower fidelity, rather than a vertical slice that fully integrates one tool first.

**Implications:**
- For tools with API access (Anthropic, OpenAI / GPT Image 2, ElevenLabs): v1 fully automates generation triggering.
- For tools without individual-creator API access (MJ, Kling): v1 uses clipboard-handoff to web UI. App drafts the prompt, copies it to clipboard, opens the relevant tool's web UI, watches `~/Downloads/` for the file to land. Existing router (`tools/downloads_router.py`) handles the file return.
- API automation for currently-gated tools is v2+ when/if API access opens.

**Caveat (calibration round):** clipboard handoff UX is prototype-critical. If clunky, users route around the app and persistent-binding benefit evaporates. Prototype priority.

### AD-2: OpenMontage / tool-build boundary defines v1 scope

The tool-build owns everything **upstream of compose.** OpenMontage owns **compose and render.** Integration is JSON: tool-build's structured data serializes into OpenMontage-compatible `edit_decisions` and `asset_manifest`.

**v1 ships with Option A** (hand-author OpenMontage-compatible JSON from tool-build's structured data, invoke compose stage as runtime). v2 considers Option B (custom Latent-Systems pipeline in OpenMontage) after multiple episodes have shipped and patterns become extractable.

**Scope test:** any proposed feature that duplicates compose-stage capability is out-of-scope. Any feature that produces structural discipline upstream of compose is in-scope. Any feature that captures relationships between artifacts is in-scope.

### AD-3: v1 is forward-only; no backfill of pre-v1 material

Existing canonical material (three weeks of EP1 production: D4 spread, thesis-image work, h3_skinner production, Phase 2 evaluations, render_craft_exemplars, etc.) is **not migrated into v1's data model.** Every prompt that produced canonical output exists only in chat scrollback (per F1 calibration); reconstructing them would require hours per section and is project-wide infeasible.

**Treatment of pre-v1 material:**
- Existing renders, NOTES.md, architecture docs, hero promotions stay where they are.
- They get marked with `discipline_version: pre_v1` when v1 enumerates them for status views.
- They remain readable and referenceable from v1 (e.g., a new prompt can cite a pre-v1 render as lineage anchor).
- They do NOT get retroactively bound to reconstructed prompts.
- They do NOT get template-upgraded retroactively.

**Implication:** F1 (prompt-output binding) is solved going forward, not retroactively. The first ~40% of EP1 production stays in its current state; the remaining production work plus all future EPs benefit from v1's discipline.

**v0.3 pressure-test note:** if Phase 1 surfaces ongoing friction from unbound pre-v1 references (e.g., v1 keeps wanting to reference D4 P3 hero's originating prompt and can't), AD-3 may need partial revision. Mitigation already in spec: pre-v1 renders are referenceable as lineage anchors even without their originating prompts. Worth watching as Phase 1 deploys.

### AD-4: Form factor is local web server + browser frontend

v1 runs as a local web server (likely Python — FastAPI / Flask / similar — given the existing router is Python and the OpenMontage parent is Python) with a browser-based frontend served at `localhost:<port>`.

**Why this form factor over alternatives:**

- **Desktop app (Electron/Tauri/native):** assumes single-instance ownership of the project state. Conflicts with M1 (multi-Claude-instance pattern) where parallel Claude instances need to read shared state.
- **CLI / TUI:** doesn't accommodate parallel Claude instances reading shared state cleanly. Also doesn't fit creative-workflow software — image audit, batch viewing, lineage browsing are visual surfaces.
- **VS Code extension:** too dev-tooling-coded. Workflow software for creative work shouldn't require an IDE to be open.
- **Local web server + browser frontend (chosen):** multiple browser tabs can be open against the same backend. Parallel Claude instances can read filesystem-mediated state. MCP integration stays clean. No Electron overhead. Browser is already where MJ / Claude.ai / GPT live, so it integrates with existing browser-based workflows naturally.

**v1 commitments derived from this:**
- Backend: Python web framework, runs locally on a known port.
- Frontend: HTML/JS/CSS served by the backend. No build pipeline complexity in v1; modern vanilla JS or a minimal framework like HTMX or Alpine.js. React/Vue/etc. is overkill for v1's surface.
- State: filesystem-mediated. No backend-only memory state that browser tabs would race against.
- Auth: none. Localhost-only by default. v1 is single-user.

**Default operational mode (v0.4 — confirmed in Phase 1 design notes):** backgrounded via `pythonw tool_build/serve.py`. No persistent terminal commitment. Foreground / debug mode available via `--debug` flag.

### AD-5: Non-invasive coexistence with existing canonical structure

v1 writes its own data to `tool_build/_data/` (centralized index) and writes sidecars only for **new artifacts created post-v1-launch.**

**Specifically:**
- Centralized index: `tool_build/_data/state.db` (SQLite) for queryable state; `tool_build/_data/<artifact_type>/<id>.yaml` for YAML representations of structured artifacts where filesystem-greppability matters.
- Sidecars on new artifacts: `<filename>.toolbuild.yaml` extension. Distinct from canonical assets, filesystem-greppable, visually clear they're v1 metadata.
- Existing canonical files (NOTES.md, architecture docs, render PNGs, audio MP3s) are **read-only to v1** by default.
- The only exception (runtime): when Joseph explicitly invokes a migration action on a specific file (e.g., "promote this NOTES.md to current discipline version"), v1 may modify that file with a clear backup written first.

**Why this matters:**

- The router has rigorous safety around canonical files. v1 inherits this discipline.
- Joseph's existing filesystem patterns (Explorer browse to `winners/`, manual reads of NOTES.md, git commits of `docs/`) keep working unchanged.
- v1 augments the project rather than replacing it. If Joseph stops using v1, the project state is still valid; v1's data is additive metadata, not the primary substrate.

**State.db is cache, not source of truth.** Per AD-5 + state.db semantics:
- Source of truth: filesystem (canonical assets + sidecars + YAML representations).
- Cache: state.db (SQLite) for fast queries. Uses WAL mode + `synchronous=FULL` for immediate-flush per multi-Claude state coordination constraints (Phase 1 design notes Section 7).
- Recovery: if state.db corrupts, regenerate by walking filesystem. No data loss; just rebuild time.
- Backup: filesystem-level (git for docs, separate backup discipline for canonical assets — already Joseph's existing pattern). State.db itself doesn't need separate backup because it's regenerable.

This makes the backup/safety story clean: the project's existing filesystem discipline IS v1's backup discipline. v1 doesn't introduce new backup requirements; it inherits the project's.

**Build-time write protection (v0.4 — added per cross-Claude review):** Phase 1 ships with a pre-commit hook that blocks non-Joseph commits from modifying canonical paths (`projects/latent_systems/shared/**`, `projects/latent_systems/ep1/**`, `projects/latent_systems/docs/**`, `projects/latent_systems/tools/**`). Catches build-time accidents (Claude Code writing test files to canonical structure) that the runtime smoke test wouldn't catch. Detail in Phase 1 design notes Section 4.

**Carve-out for enforcement infrastructure (v0.5 — added per parallel-Claude review of git scope):**

The git repo lives at the `OpenMontage/` parent level (`OpenMontage/.git`), not at `projects/latent_systems/`. The pre-commit hook therefore lives at `OpenMontage/.git/hooks/pre-commit` — outside the `tool_build/_data/` namespace AD-5 commits to.

This is structurally different from runtime canonical writes and is an explicit carve-out, not a violation:

1. **One-time install action, not ongoing runtime behavior.** AD-5's "v1 writes only to `tool_build/_data/`" is a *runtime* promise. Hook installation is a *setup-time* action, more analogous to `pip install` writing to `site-packages/` than to v1 modifying canonical files during use.
2. **The hook serves AD-5; it does not violate it.** The hook exists *to enforce* AD-5 against build-time accidents. It's protecting the canonical structure from accidental writes, not making writes. Enforcement infrastructure is qualitatively distinct from artifact authorship.
3. **Scoped narrowly to Latent Systems paths.** OpenMontage's own work is unaffected. The hook only blocks if a non-Joseph commit touches `projects/latent_systems/shared/**`, `ep1/**`, `docs/**`, or `tools/**`. OpenMontage commits to its own paths (`remotion-composer/`, `pipeline_defs/`, etc.) pass through normally.
4. **User-invoked, not automatic.** Joseph runs install explicitly via `python tool_build/serve.py --init`. The app does NOT silently install hooks at first run. Install prompts for confirmation; if declined, app proceeds without the hook (build-time write protection reduced; runtime smoke test still operative).
5. **Reversible.** Uninstall procedure removes the hook (restoring any pre-existing backup) — see Phase 1 design notes Section 6.
6. **Existing-hook chaining.** If OpenMontage already has a pre-commit hook (lint, format, tests), v1's install backs it up to `pre-commit.backup_<timestamp>` and chains it: new hook calls existing hook first, then runs AD-5 enforcement, fails if either fails. Preserves OpenMontage's existing discipline.

### Enforcement-infrastructure principle (v0.5 — new)

Generalizing from AD-5's hook carve-out: **enforcement infrastructure (hooks, smoke tests, validators, watchers, backup scripts) gets explicit carve-out treatment, separate from runtime artifact authorship.** AD-5's strictness is what made the carve-out visible; without that strictness, the hook install would have been invisible scope creep.

The framing makes future similar decisions easier. When a Phase 2 or Phase 3 feature wants to install something outside `tool_build/_data/`:

- Is it **enforcement infrastructure** (protects AD-5 / coexistence / safety)? → Allowed with explicit carve-out banked in spec.
- Is it **artifact authorship** (creates content that the project will reference as canonical)? → Must live in `tool_build/_data/` per AD-5.

Examples this principle resolves cleanly:

- Phase 2 wants to install a filesystem watcher daemon at OS level → enforcement (detects external YAML edits per Section 7 multi-Claude constraints). Carve-out, allowed.
- Phase 3 wants to install a backup script that runs nightly → enforcement (backs up `tool_build/_data/`). Carve-out, allowed.
- Hypothetical Phase 4 wants to write summary stats to `docs/` so they're git-tracked → artifact authorship. Not allowed; lives in `tool_build/_data/` instead.

Each enforcement-infrastructure addition needs its own carve-out paragraph banked in the spec at the time it's added. The pattern doesn't auto-license future additions; it provides the framing for each one to be evaluated explicitly.

### Design principle: Discipline-aware AND discipline-tolerant (per F10)

The app is being built for a project that is itself learning its discipline as it builds. The app cannot impose a fixed standard on top of a moving discipline. It must support discipline-evolution, not freeze it.

**Concrete implications:**
- Templates are menus, not enforcement.
- Status views surface gaps without prescribing how to close them.
- Triggers prompt for action without forcing it.
- The data model captures *which version of discipline* a given artifact was authored against, so retroactive upgrading becomes a deliberate act rather than a retrofit.

This principle applies recursively. v1 itself will introduce tooling whose discipline pattern doesn't yet exist; the app should not lock down workflow rules around tools that haven't been used long enough to know what their workflow actually is.

**Discipline-version-drift surface (per spot-check Wobble 1 + parallel-Claude calibration):** the data-model `discipline_version` field is necessary but not sufficient for F10 compliance. Joseph needs to *experience* discipline-evolution-tolerance as a feature, not just as silent metadata. v1 includes a **discipline-drift query surface** — at minimum, "show me everything authored against v0.4 of the discipline" as a queryable view across artifact types. This is v1 minimum-viable for F10, not v2 polish.

---

## Architectural shape: two layers

### Layer 1 — Artifacts

Concepts, prompts, renders, audit verdicts, hero promotions, NOTES.md, architecture docs. Each is a structured object on filesystem with first-class identity, version history, and metadata.

### Layer 2 — Relationships

Bindings (prompt ↔ render, render ↔ winners/, hero ↔ NOTES.md), lineages (render → render → render via craft vocabulary; concept → concept → concept via chat), inheritances (channel arch → EP1 arch → NOTES.md), references (NOTES.md → channel staple by ID). Queryable graph relationships, not just attributes on artifacts.

**Layer 2 has temporal dimension (v0.4 — added per cross-Claude review).** Lineage edges carry `valid_from_version` / `valid_to_version` markers. When discipline evolves, edges can be marked stale without deletion (preservation of decision history per channel staple #12). This makes F12's "stale-reference inventory" implementable via lineage_edges queries rather than as a separate Phase 4 capability. Schema detail in Phase 1 design notes Section 2.

**The two layers are interdependent.** v1 cannot solve the artifact layer alone. M4 names this: the project has rigorous filesystem discipline for artifacts and zero filesystem discipline for relationships. The relationship layer is the structural commitment v1 ships with.

---

## v1 spine (the user-facing surface)

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PROJECT WORKSPACE                           │
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │  Concept    │ →  │   Prompt     │ →  │  Generation 3a/3b   │   │
│  │  Browser    │    │   Drafting   │    │  (API or            │   │
│  │  (F2)       │    │   (F3,F4)    │    │  clipboard-handoff) │   │
│  └─────────────┘    └──────────────┘    └─────────────────────┘   │
│         │                  │                       │                │
│         ↓                  ↓                       ↓                │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              Existing Router (tools/downloads_router.py)      │ │
│  │              Files land in ~/Downloads, route to canonical    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│         │                                                            │
│         ↓                                                            │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────┐ │
│  │   Audit      │ →  │   Hero       │ →  │   NOTES.md          │ │
│  │   Viewer     │    │   Promotion  │    │   Authorship        │ │
│  │   (F8)       │    │   (F9)       │    │   (F10)             │ │
│  └──────────────┘    └──────────────┘    └─────────────────────┘ │
│         │                                          │                │
│         └──────────────────────┬───────────────────┘                │
│                                ↓                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │       Serialization → OpenMontage compose stage              │ │
│  │       (per-section trigger: NOTES.md complete = ready)       │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Capture surface (cross-AI / cross-Claude / decision log)    │ │
│  │  — F6, F11a, F11b — present alongside main flow              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Discipline-drift query surface (F10 v1 minimum)             │ │
│  │  — "show me artifacts authored against v0.X" — cross-type    │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

This is the spine. Six primary surfaces (concept browser, prompt drafting, generation triggering split into 3a/3b, audit viewer, hero promotion, NOTES.md authorship) flowing into one integration boundary (serialization to OpenMontage). Two peripheral surfaces (cross-AI/cross-Claude capture; discipline-drift query) that cross every primary surface.

---

## Data model

Schemas detail in Phase 1 design notes Section 2. Summary here for context.

### Artifact objects

Each artifact gets a structured representation on filesystem (YAML in `tool_build/_data/<artifact_type>/<id>.yaml`, indexed in `tool_build/_data/state.db` per AD-5). Schema-validated. Each carries a `discipline_version` field for F10 compliance.

Artifact types: concept, prompt, render, generation_attempt (per cross-Claude review for sequential re-rolls), audit_verdict, hero_promotion, notes_md_state, cross_ai_capture, tool_grammar_config, api_call (cost tracking from day one).

### Relationship objects

Per M4: relationships are first-class data model objects, not attributes on artifacts.

Relationship types: lineage_edge (with temporal dimension per v0.4), doc_set, reference.

Full schemas in Phase 1 design notes Section 2.

---

## v1 features (organized by spine surface)

### 1. Concept browser

**Addresses:** F2 (concept-state dies at chat boundaries; ~1hr re-derivation tax).

**Capability category:** net-new — low-risk. Data shape is well-specified; UI shape conventional.

**v1 functionality:**
- List view of all concepts in the project, with status (drafting / generating / evaluated / locked / archived).
- Filter by EP, section, status, register, tool target.
- Open a concept → see its full structured object, all derived prompts, all renders, all audit verdicts, hero promotion status.
- Create new concept from menu (template menu per F10 — not enforcement).
- Edit concept fields (name, register, reference anchors, tool targets) at any time. Discipline-version updates automatically on substantive edit.

**Critical detail:** when a chat opens, the app's concept browser IS the concept state. No re-derivation from briefing+handoff at chat start. Joseph (or Claude API) opens the app, picks the concept, work continues from where it left off.

### 2. Prompt drafting

**Addresses:** F1 (prompt-output binding), F3 (tool-grammar dependency), F4 (lineage anchoring across three layers).

**Capability category:** hybrid — drafting flow streamlines existing pattern; tool-grammar config + binding + lineage are net-new.

**v1 functionality:**
- Select concept + target tool → app composes API call to Claude with `(concept, target_tool, accumulated_tool_grammar_config)`.
- Returns tool-specific prompt as draft. Joseph reviews, edits, locks.
- On lock: prompt is captured to filesystem with `concept_id` binding, `lineage` populated (render anchors via UI picker; prompt anchors and concept anchors via Claude API suggestion or manual entry).
- Locked prompt becomes durable. Surviving chat closure. Surviving multi-instance Claude work. Recoverable by `prompt_id`.

**Tool-grammar config (Phase 1 prerequisite):** detailed schema with MJ seed content in Phase 1 design notes Section 3. Includes (per cross-Claude review) novel-concept-resistance failure mode, split-focus + echo-anchor vocabulary priors, prompt-length sensitivity refinement.

**Graceful degradation:** if Claude API is down or rate-limited, app surfaces failure clearly. Manual prompt entry that bypasses the model is supported. Cache of last-N tool-specific prompts per concept available for offline reference.

### 3a. Generation triggering — API-accessible tools

**Addresses:** F7 (generation phase has zero project-aware tooling) for tools with API access.

**Capability category:** hybrid — generation step itself replaces existing browser-based pattern; status tracking + binding are net-new.

**v1 functionality:**
- "Generate" button → app calls API (Anthropic / OpenAI / ElevenLabs) with prompt → polls or waits for completion → captures output to canonical structure → updates render objects with `prompt_id` binding.
- Status visible during generation: pending / running / complete / failed / partial.
- Cancel button if generation is in flight.

**Failure modes (detailed in Phase 1 design notes Section 1, including 3a.7 partial completion per cross-Claude review):** rate limit (queue with backoff), auth error (no retry), hallucinated syntax (audit catches downstream), timeout (manual retry), network failure (single auto-retry), malformed response (manual retry), partial completion via streaming disconnect (user chooses retry-to-complete or use-partial-as-is).

### 3b. Generation triggering — clipboard-handoff tools

**Addresses:** F7 for tools without API access (MJ, Kling). The architecturally vulnerable surface per AD-1 caveat.

**Capability category:** hybrid — copy-paste-into-browser pattern preserved; orchestration + binding + status tracking are net-new.

**v1 functionality:**
- "Copy prompt + open MJ" button → app copies prompt to clipboard → opens MJ web UI in browser → updates app state to "expecting return for prompt X."
- Existing router (`tools/downloads_router.py`) detects new files in `~/Downloads/` → routes to canonical structure with audit log.
- App detects new render in canonical structure → matches against most recent uncaptured prompt → binds and updates render object.
- Orphan return detection: if user pastes manually outside the app, app detects orphan render and offers to bind it to the most recent uncaptured prompt.
- Generation-attempt model (per cross-Claude review): each clipboard-copy event creates a new `generation_attempt` record under the prompt. Renders bind to most recent open attempt. Re-rolls don't co-mingle.

**Failure modes (detailed in Phase 1 design notes Section 1, including 3b.7 rename-before-routing and 3b.8 sequential generations per cross-Claude review):** silent failures (timeout-based "did this complete" UI), tool mismatch on orphan returns, file-not-detected, multiple uncaptured prompts when render arrives, unknown filename patterns routed to `_inbox/`, file renamed before router detection, multiple sequential rolls of same prompt.

**The "did this complete" affordance is critical for 3b** in a way it isn't for 3a. v1's UI for 3b must include explicit "still waiting" / "got it" / "manually mark this failed" actions because the silent-failure mode is the dominant failure mode.

**Prototype priority per F7 leverage ranking:** failed-generation tracking + batch identification + reference-image persistence first. Tab-management and dead-time-utilization land later.

### 4. Audit viewer

**Addresses:** F8 (audit phase has minimal tooling, verdict durability delayed).

**Capability category:** streamliner — replaces Windows Media Player / Photos with project-aware viewer. AI-assisted evaluation flow is net-new but layers over existing multi-AI consultation discipline.

**v1 functionality:**
- Project-aware image viewer that displays render + prompt + concept context + lineage chain in one screen.
- Toggle between serial view (one-by-one, prev/next navigation) and grid view (4×5 with prompt headers).
- Criteria visible during audit as configurable rubric per concept-type. Rubric is versioned (per F10 + Q5).
- Two audit modes (per F8 calibration):
  - **Quick-pass-against-known-criteria:** minimal-friction advance/mark/advance for batches where vocabulary holds.
  - **Deep-evaluation-against-emerging-criteria:** full context (concept text, lineage, AI consultation panel) for batches where the question is structural.
- AI-assisted evaluation as one-click flow: select render or batch → invoke "AI evaluation against criteria" → Claude API call sends render + criteria → structured response logged alongside render as `verdict.ai_consultations` entry.
- Multi-AI evaluation discipline (per F8 calibration): app supports the existing role calibration (Perplexity for resistance, ChatGPT for adversarial structural read, etc.). Each AI consultation captured with attribution.
- Verdict capture writes to filesystem instantly. No "save" button. Verdict object created at the moment of marking.

### 5. Hero promotion (atomic action)

**Addresses:** F9 (hero promotion is partial discipline).

**Capability category:** streamliner — file-level mechanic preserved; atomic-action discipline + doc-update coordination + audit log are net-new.

**v1 functionality:**

When Joseph promotes a render to hero, the app executes a single atomic action:
1. Copy render to canonical `winners/` location with proper naming (existing mechanic preserved).
2. Write hero_promotion object to filesystem with `render_id`, source path, destination path, reasoning note, list of doc updates.
3. Trigger prompt: "this section's NOTES.md hasn't been updated since X — update now?" (per F9 + F10).
4. Coordinate updates to enumerated docs (per F9 calibration: `shared/<context>/README.md`, `docs/CHANNEL_STRUCTURAL_ARCHITECTURE_v1_X.md` if relevant, `docs/HANDOFF_<date>.md` if active session). The set of doc-update locations is config-driven (per F10 — discipline can evolve), not Claude-decides-each-time.

When Joseph un-heroes a render (per channel staple #12):
1. Move hero copy from `winners/` to `_work/<context>/_DEPRECATED_<category>/` directory.
2. Rename with `_DEPRECATED_<reason>.png` marker. **Reason field required, not optional** (per F9 calibration). App refuses to proceed without reason.
3. Update hero_promotion object with `reversed: {<reason>, <timestamp>}`.
4. Update relevant NOTES.md.

### 6. NOTES.md authorship

**Addresses:** F10 (NOTES.md discipline is evolving — coverage gap + intentional variance + no completeness state).

**Capability category:** streamliner — authorship pattern preserved (Claude drafts, Joseph approves); status view + template versioning + discipline-evolution tracking are net-new.

**v1 functionality:**
- **Status view per section:** list of all canonical EP1 sections, with NOTES.md presence/absence/staleness marked. Each NOTES.md displays its `authored_against` discipline version vs current. Older NOTES.md flagged "needs_revisit: true" when discipline advances, but never auto-upgraded.
- **Template menu (not enforcement):** when generating a new NOTES.md, app offers template variants the project has used (status-pending note, technical-spec doc, full recipe-authority). Joseph picks the appropriate level for what's actually being captured. App can suggest based on section state but doesn't force.
- **Templates are versioned** (per F10 calibration). Current template version 1.0 at v1 launch (per AD-3 baseline). When discipline evolves, bump template version. Existing NOTES.md flagged for revisit.
- **Hero-promotion-triggers-NOTES-prompt:** event-driven trigger that's currently missing (per F10). When hero promoted, app prompts but does not force.
- **Authorship via Claude API** (per Q9 + F3 sharpening): app sends `(concept, hero_renders, prior_notes_md, current_template_version, project_context, tool_grammar_config)` to Claude API. Claude drafts NOTES.md content. Joseph approves or directs revisions before write.

### 7. Cross-AI / cross-Claude capture surface

**Addresses:** F6 (cross-AI exchanges leave no filesystem trail), F11a (cross-Claude handoff is sub-case), F11b (multi-instance Claude work has no infrastructure), M1 (multi-Claude-instance pattern), M2 (extended-structured-interview-with-AI), M3 (compressed-text answer expansion).

**Capability category:** net-new — high-risk. UX shape genuinely uncertain; "compressed-input + AI-expansion" pattern is primary input flow but hasn't been built before.

**v1 functionality:**
- "Capture cross-AI exchange" action available from any context.
- Form fields: source (Perplexity / ChatGPT / Grok / Gemini / parallel Claude instance), source identifier (chat URL or name when known), question asked, answer received, Joseph's verification note, relevance binding.
- **Default relevance binding (per Q4):** last-touched finding/decision (whatever Joseph was last looking at). Editable before save. This gives fast capture while preserving binding discipline. Required field with no default would fight the M3 compressed-input pattern; unbound-allowed would be too sloppy.
- Captured exchange written to filesystem as `cross_ai_capture` object.
- Searchable / queryable: "what cross-AI inputs informed AD-2?" "what did parallel Claude instance say about Q12?"
- Compressed-answer + AI-expansion as primary input pattern (per M3): app does not require structured forms or long-form input. Joseph can paste compressed answer + Claude API expands using project context. Captured pair preserves verbatim Joseph input alongside Claude expansion.
- **v1 = Option 2 from F11b** (capture surface only, no orchestration). v3+ might consider orchestration if the capability becomes available.

### 8. Serialization to OpenMontage (per AD-2)

**Addresses:** F13 (editorial assembly is at OpenMontage layer; gap is upstream-of-compose handoff), M5 (OpenMontage / tool-build boundary).

**Capability category:** net-new — medium-risk. Schema alignment with OpenMontage may surface fit issues; serialization itself is mechanical.

**v1 functionality:**
- Per-section trigger (per Q6): NOTES.md-completion event surfaces "section X is NOTES.md-complete; ready to serialize" as action.
- Serialization composes structured app data into OpenMontage-compatible JSON: `edit_decisions` (one per section) + `asset_manifest` (heroes + alternates).
- Tool-build's data model aligns with OpenMontage's schemas where possible (per Q13 calibration sharpening) — serialization is mechanical, not translation-heavy.
- Joseph reviews serialized JSON before handing off to OpenMontage's compose stage.
- Compose invoked via existing OpenMontage mechanism (CLI, agent invocation, or direct script). v1 produces the JSON; v1 does NOT invoke compose itself — that's user action.
- v1 captures the handoff as an event (per-section): app records "section X serialized for OpenMontage at <timestamp>" so the audit trail is durable.

### 9. Discipline-drift query surface (F10 minimum-viable per spot-check Wobble 1)

**Addresses:** F10 design principle as experienceable feature, not silent metadata.

**Capability category:** net-new — high-risk. UX shape uncertain. Cross-artifact-type queries surfaced as status badge + drill-down view is conceptually clean but not architecturally trivial; how it actually feels in use is the open question. **If Phase 1 trips, it's most likely to trip here.**

**v1 functionality:**
- Cross-artifact query: "show me everything authored against discipline_version v0.X" — returns concepts, prompts, renders, verdicts, hero_promotions, NOTES.md, cross_ai_captures matching the version.
- Per-artifact view: "what discipline_version is this artifact, and how does it differ from current?"
- Status badge in main UI: "N artifacts authored against earlier discipline versions (review available)."
- Stale-reference inventory (v0.4 — possible per temporal lineage_edges): "what lineage edges are valid_from a discipline version that has since been changed?" implementable as queries against the temporal-dimension-extended lineage_edges table.
- No auto-upgrade actions. Per F10 design principle, all upgrades are deliberate.

This is the surface that makes M4's relationship layer + F10's discipline-evolution principle visible to Joseph as a working tool. Without it, F10 is enforced silently and Joseph has no way to act on discipline-version drift.

---

## Out of scope for v1 (CONFIRMED via spec synthesis)

- **Multi-user collaboration.** Single-user only.
- **Cloud sync.** Local-only filesystem.
- **Editorial assembly UI.** OpenMontage's compose stage handles assembly; v1's job is producing structurally-disciplined inputs that match OpenMontage's existing artifact schemas. (Per F13, M5, AD-2.)
- **Editorial-tool-agnosticism.** Latent Systems lives inside OpenMontage's parent directory. v1 doesn't think about Premiere/Resolve/Final Cut Pro compatibility.
- **Backfill of pre-v1 prompts/concepts/relationships.** Per AD-3. Existing canonical material stays as-is with `discipline_version: pre_v1` marker.
- **AI-orchestrated multi-tool batch generation.** v1 calls APIs for individual generations, not "generate this concept across all three tools and rank results automatically." That's v2+.
- **Auto-prompt-improvement.** v1 doesn't try to be a prompt engineer. Joseph drafts prompts collaboratively with Claude; app captures and routes. Prompt-improvement-by-the-app is v2+.
- **Cross-project generalization.** v1 is Latent-Systems-specific. Generalization happens later, by extracting patterns that survive multiple projects.
- **Distribution / multi-tenancy / "release as app for others."** Different project entirely; explicitly deferred.
- **Built-in handoff-doc generator** (per F5). Phase 0 removed the forcing function. v1 does not replicate.
- **API automation for MJ and Kling** (per AD-1). v1 uses clipboard-handoff. API automation is v2+ when/if API access opens.
- **Multi-instance Claude orchestration** (per F11b option 3). v1 captures cross-Claude-instance handoffs after the fact. Orchestration is v3+.
- **Custom Latent-Systems pipeline in OpenMontage** (per AD-2: A → B sequenced commitment). v1 = Option A. v2+ = Option B.
- **Inheritance audit automation** (per F12 v1 implication 2). v1 surfaces verification checklists at architecture-lock time; Joseph performs verification. Auto-update is v2+.
- **Reference-as-data parsing of existing markdown** (per F12 v1 implication 1, partial). v1 supports new references as structured data; existing free-text references in NOTES.md are not auto-parsed. Migration is v2+.
- **Audits-as-first-class-artifacts.** v1 treats audits as flat markdown in `tool_build/`. Audits ARE relationship-layer-concentrated artifacts (they reference doc-sets, renders, concepts, cross-AI exchanges) and v2 may promote them to first-class artifacts if relationship layer benefits emerge. v1 punts. (Per parallel-Claude calibration major addition.)
- **Hook portability across machines** (v0.5 — added per parallel-Claude review). Pre-commit hooks live in `.git/hooks/` which isn't tracked in git. If Joseph clones the project on another machine, the hook is missing. Phase 1 single-user single-machine = fine. Multi-machine work would need different mechanism (husky, pre-commit framework, or docs with manual install step) — v2+ if it ever becomes relevant.

---

## Confirmed answers to open questions

### Q1 — Filesystem layout

**Decision: Hybrid (centralized index + sidecar references).**

- Centralized state in `tool_build/_data/state.db` (SQLite, cache per AD-5).
- YAML representations of structured artifacts in `tool_build/_data/<artifact_type>/<id>.yaml` (filesystem-greppable source of truth).
- Sidecars on new artifacts use `.toolbuild.yaml` extension. Filesystem-greppable, visually distinct from canonical assets, doesn't conflict with anything.
- All app data in `tool_build/_data/` namespace. No project-root pollution. No hidden directories.

### Q2 — Discipline-version starting value

**Decision: `1.0` for v1 launch.**

- v1 launch baseline is `1.0`.
- Existing canonical material that v1 enumerates is marked `pre_v1` (per AD-3).
- Future evolution: `1.1`, `1.2`, etc. Major rethinks would be `2.0`.
- Per-artifact-type discipline versions (NOTES.md template version, audit rubric version, etc.) start at `1.0` independently. Not all coupled.

### Q3 — Tool-grammar bootstrapping

**Decision: Hybrid (initial seed + auto-population).**

- Phase 1 ships with hand-authored seed config for MJ minimum. Joseph + Claude write from accumulated experience.
- App auto-populates from successful prompt+output bindings over time (when verdict.verdict ∈ {hero_zone, strong}).
- `successful_examples: [<prompt_id>, <prompt_id>]` field references prompts that produced verdict-confirmed-strong outputs; tool-grammar config draws from these for future drafts.
- Empty-config approach was rejected because Phase 1 prompt drafts would be worse than current state. Defeats v1 purpose.

### Q4 — Cross-AI capture defaults

**Decision: Last-touched finding/decision as default, editable before save.**

- Required-field-no-default rejected (fights M3 compressed-input pattern).
- Unbound-allowed rejected (sloppy, defeats binding discipline).
- Default-with-edit gives fast capture + preserves binding.

### Q5 — Audit rubric configuration

**Decision: In project, versioned alongside other architecture docs.**

- Rubrics live at `docs/AUDIT_RUBRICS_v1_0.md` (or similar naming consistent with project's existing `_v1_X.md` versioned-doc convention).
- Per-concept-type rubrics with project-level defaults.
- Versioned via the same lock cycle as channel architecture (full-rewrite per version, in-doc changelog, archive lifecycle for predecessors).
- App reads rubrics from filesystem, not from app config.

### Q6 — OpenMontage serialization granularity

**Decision: Per-section, triggered by NOTES.md-completion.**

- Section is the natural unit (matches v1's existing section-level structure: ep1/h1_hook, ep1/section_1c, etc.).
- NOTES.md-completion is the natural trigger event (channel staple #11 = NOTES.md-as-recipe-authority; section is "ready" when its recipe is captured).
- Per-block aggregation can be v2 if useful patterns emerge.
- Per-episode monolithic serialization rejected (too coarse; doesn't match the NOTES.md trigger).

### Q7 — Prototype priority order

**Decision: Phase 1 builds substrate FOR high-leverage features per F7 ranking.**

The apparent tension between F7's leverage ranking ("failed-generation tracking + batch identification + reference-image persistence first") and Phase 1's surface ("concept browser + prompt drafting + clipboard handoff") resolves like this:

- F7's high-leverage features all require the data model foundation (prompt + render objects with status fields, prompt-output binding, concept objects with reference_anchors).
- Phase 1 builds that foundation. The high-leverage features become *possible* in Phase 1 but may not be fully *exposed* in Phase 1's UI.
- Phase 2 surfaces them prominently.

Phase 1 is not deprioritizing F7. Phase 1 is the substrate. Confirming.

---

## Build approach

Per project briefing: AI-assisted via Claude Code. v1 = a relationship-layer infrastructure with workflow surfaces over it (per honest scope statement).

**Effort estimate (v0.4 — adjusted per cross-Claude review):**

- **Phase 1: 3-6 weeks** (raised from v0.3's 2-4). Building applications with Claude Code is a different tempo from creative-direction work — different fail modes, different debug loops, different "what does done look like" judgment calls. Past three weeks have been creative-direction (architecture lock, evaluation, exemplar canonicalization), not application build. The 2-4 week estimate was optimistic by ~1.5x.
- Phase 2: roughly 2-3 weeks layered onto Phase 1's data model foundation.
- Phase 3: roughly 2-3 weeks closing the loop with cross-AI capture + serialization.
- **Total Phase 1-3: 8-12 weeks** (raised from v0.3's 6-10). Phase 4 deferred to v2 territory.

This is rough. It assumes Joseph + Claude Code working at compressed-iteration tempo. Estimate assumes some things go wrong and need re-work; doesn't assume catastrophic re-architecture.

**Suggested phasing (Phase 1 detail in design notes Section 8 — risk-aware sequence per cross-Claude review):**

**Phase 1 (MVP — addresses F1, F2, F4 first):**
- Form factor commitment per AD-4: Python web framework + browser frontend, default-backgrounded via `pythonw`.
- Filesystem layout per Q1: `tool_build/_data/` + sidecars on new artifacts.
- Concept + prompt + render + generation_attempt objects with first-class identity.
- Existing router integration (read router_log, populate render objects on routing events).
- Basic concept browser UI (list view, open concept).
- Prompt drafting via Claude API with hand-authored MJ tool-grammar config seed (Q3).
- Clipboard handoff for MJ (Feature 3b with explicit "did this complete" affordances per Wobble 2 sharpening).
- Discipline-drift query surface (Feature 9) with `pre_v1` markers populated for existing canonical material per AD-3.
- API call instrumentation (cost tracking from day one).
- Build-time write protection (pre-commit hook per AD-5 carve-out, with existing-hook chaining).
- Schema migrations via Alembic (un-punted from v0.2 per cross-Claude review).

This produces durable prompt-output bindings (F1) and concept persistence (F2) and partial lineage anchoring (F4 layers 1 and 2). It's the minimum that makes the project's existing patterns durable.

**Phase 1 design notes** at `tool_build/phase1_design_notes.md` v0.3 — covers failure modes (3a/3b including 3a.7 + 3b.7-8), state.db schema (with generation_attempts + api_calls tables + temporal lineage_edges), MJ tool-grammar seed (with novel-concept-resistance + split-focus + echo-anchor additions), coexistence verification + build-time write protection (with install/uninstall procedures + existing-hook chaining), backup story, operational lifecycle (default-backgrounded with `pythonw` + uninstall), multi-Claude state coordination constraints (immediate-flush + external-edit detection), risk-aware Phase 1 build sequence.

**Phase 2 (addresses F7, F8, F9):**
- Audit viewer (project-aware image viewer with prompt + lineage display).
- Multi-AI evaluation flow with role calibration (Perplexity / ChatGPT / Grok / Gemini configured).
- Verdict capture as immediate filesystem write.
- Hero promotion atomic action with doc-update coordination.
- Tool-grammar config expansion to GPT Image 2 + Kling + ElevenLabs (driven by usage patterns from Phase 1).
- Failure-mode handling for API generation (3a) hardened.

This makes the audit and promotion phases project-aware. F7's six sub-flavors get addressed in priority order per leverage ranking.

**Phase 3 (addresses F10, F11a/b, F12, M5 integration):**
- NOTES.md authorship with template menu and discipline-version tracking.
- NOTES.md template versioning (first opportunity to test discipline-version bump per success criterion 10).
- Cross-AI / cross-Claude capture surface.
- Doc-set data model and reference-as-data primitives.
- Serialization to OpenMontage with per-section trigger.

This closes the loop. The integration with OpenMontage at AD-2's boundary is operational. Future episodes reuse v1's patterns; vocabulary annex findings get banked durably; cross-AI input is captured.

**Phase 4 (deferred to v2 territory):**
- Inheritance audit at architecture-lock time (F12 v1 implication 2).
- Stale-reference inventory as queryable view (F12 v1 implication 3) — note: temporal lineage_edges added in v0.4 makes this implementable in v1 via Feature 9 if the surface allows.
- Migration tools for existing free-text references.
- Audits-as-first-class-artifacts if relationship-layer benefits emerge.
- Patterns that emerged from Phase 1-3 use that suggest custom OpenMontage pipeline (Option B per AD-2).

---

## Success criteria for v1

The audit identified concrete tests for whether v1 is working. These become success criteria:

1. **F1: Prompt-output binding.** Given any post-v1 render in canonical structure, the prompt that produced it is recoverable by `render_id` query in <2 seconds. No chat-history search required. (Pre-v1 renders are unbound per AD-3 and excluded from this criterion.)

2. **F2: Concept persistence reduces re-derivation tax.** New chat opens. Joseph wants to resume work on a concept. Time from "open app" to "ready to draft next prompt" is <5 minutes (vs current ~1 hour).

3. **F4: Lineage anchoring works for all three layers.** Pick a render. Query "what prompts cite this as anchor?" Returns list. Query "what concepts informed the prompt that produced this?" Returns list. Both queries answerable in app, no chat-history search.

4. **F7: Generation phase friction reduced.** During a generation session, Joseph reports: failed-generation tracking visible, batch identification clear (including across re-roll attempts), reference images persistent across the session.

5. **F8: Audit verdicts durable from moment of marking.** Mark a render as hero-zone. Close the chat. Reopen the app a day later. Verdict still present, with reasoning, with audit-rubric used, with AI consultations logged.

6. **F9: Hero promotion is atomic.** Promote a render. App copies file, writes hero_promotion object, prompts NOTES.md update, triggers doc-update coordination, all in one user action with single audit-log entry.

7. **F10: NOTES.md status view shows coverage AND discipline-drift surface works.** Open status view: app displays all canonical sections with NOTES.md presence/absence/staleness. Open discipline-drift query: app returns artifacts authored against earlier versions across all artifact types.

8. **F11a/F11b/M1: Cross-Claude capture works.** Joseph asks parallel Claude instance a question. Pastes answer into capture surface. App writes structured artifact with attribution + relevance binding. Future query "what did parallel Claude say about X?" returns the captured exchange.

9. **F12 / M4 / M5: Serialization to OpenMontage works.** Section X is NOTES.md-complete. App surfaces "ready to serialize." Joseph triggers serialization. App generates OpenMontage-compatible JSON. Joseph hands JSON to OpenMontage compose stage. Compose runs and produces a finished section render.

10. **Discipline-version bump tested in Phase 3:** during Phase 3 testing, app handles a NOTES.md template version bump (1.0 → 1.1) without breaking existing NOTES.md state objects of other artifact types. Existing NOTES.md flagged for revisit; concept/prompt/render/verdict/hero_promotion objects unaffected. Demonstrates per-artifact-type discipline-version independence (per Q2 confirmation).

---

## Cost / API model

v1 is Claude-API-dependent for core functions (per F3): prompt drafting, NOTES.md authorship, audit AI consultation, cross-AI expansion of compressed answers. API costs are real ongoing operational cost.

**Rough estimate (v0.3 — still placeholder pending Phase 1 measurement):**

- Prompt drafts: ~50 / week × ~$0.05 per draft = ~$2.50/week
- NOTES.md authorship: ~5 / week × ~$0.20 per draft = ~$1/week
- Audit AI consultation (vision API — dominant cost driver): ~20 calls/week × ~$0.30/call = ~$6/week. Could go higher if batches are larger or multi-AI consultation is heavy.
- Cross-AI expansion: ~10 / week × ~$0.05 per expansion = ~$0.50/week

**Roughly $10-25/week in Claude API spend (placeholder, vision-API-driven).** The audit AI consultation is the dominant variable. Phase 1 includes actual cost tracking from day one (via `api_calls` table per design notes Section 2) so the estimate gets validated or revised based on real usage.

**Graceful degradation paths:**
- API down → manual entry bypass; surface failure clearly.
- Rate limited → queue and retry with exponential backoff.
- Budget approached → pause and prompt for confirmation (existing OpenMontage budget governance pattern can be borrowed).

---

## What v2 looks like (preview)

Banked here so v1 build doesn't drift into v2 territory:

- API automation for MJ and Kling (when API access opens).
- Custom Latent-Systems pipeline in OpenMontage (Option B per AD-2) after multiple episodes have shipped.
- Inheritance audit automation (auto-walks inheriting docs at architecture-lock time).
- Stale-reference inventory as queryable view (note: temporal lineage_edges in v1 may make this implementable earlier).
- Migration tools for existing free-text references (turn "channel staple #11" mentions into structured references).
- AI-orchestrated multi-tool batch generation.
- Auto-prompt-improvement based on accumulated prompt+render history.
- Cross-project generalization (extract patterns that survive multiple projects).
- Multi-instance Claude orchestration (if capability becomes available).
- Audits-as-first-class-artifacts (if relationship-layer benefits become evident).
- Backfill tooling for pre-v1 material (only if it ever matters; AD-3 currently says no).
- Hook portability across machines (per AD-5 v0.5 carve-out — out-of-scope for v1).

---

## Architectural Decisions Register (consolidated)

| Code | Decision | Rationale |
|------|----------|-----------|
| AD-1 | Horizontal-slice across all tools (concept persistence, prompt drafting, audit, lineage all work everywhere; generation triggering varies by API availability). | F7 — pain points are upstream of API automation. |
| AD-2 | OpenMontage / tool-build boundary defines v1 scope. Tool-build owns upstream-of-compose; OpenMontage owns compose+render. v1 ships with Option A (hand-author OpenMontage-compatible JSON). | Q13 + parallel-Claude calibration. Resolves editorial-assembly question structurally. |
| AD-3 | v1 is forward-only; no backfill of pre-v1 material. Existing canonical material gets `discipline_version: pre_v1` marker and stays unbound. | F1 calibration: prompts have never been on filesystem; reconstruction is project-wide infeasible. |
| AD-4 | Form factor: local web server + browser frontend, default-backgrounded via `pythonw`. | M1 multi-instance compatibility; browser-based workflow integration; no Electron overhead; matches Joseph's no-persistent-terminal pattern. |
| AD-5 | Non-invasive coexistence with existing canonical structure. v1 writes to `tool_build/_data/` and sidecars on new artifacts only. State.db is cache, not source of truth. Build-time write protection via pre-commit hook (v0.5 enforcement-infrastructure carve-out). | Inherits router's safety discipline; doesn't disrupt Joseph's existing filesystem patterns. |

---

## Document maintenance

- **v0.1 (2026-05-03):** initial draft synthesizing audit findings F1-F13, M1-M5, AD-1, AD-2, design principle, v1 spine.
- **v0.2 (2026-05-03):** spot-check pass + parallel-Claude calibration. Added AD-3 (forward-only), AD-4 (form factor), AD-5 (coexistence). Sharpened wobbles 1-6. Banked confirmed answers to Q1-Q7. Split Feature 3 into 3a/3b. Added Feature 9 (discipline-drift query surface). Reframed success criterion 10. Added audits-as-first-class-artifacts to out-of-scope per parallel-Claude major addition. Phase 1 design notes called out as prerequisite to code starts.
- **v0.3 (2026-05-04):** morning-read refinements after overnight refinement-stop. Added honest scope statement (v1 is more than streamlining). Added capability-category labels to each feature. Added Phase 1-3 effort estimate (6-10 weeks total). Raised API cost estimate to $10-25/week placeholder with vision-API-as-dominant-driver named. Added operational lifecycle to Phase 1 design notes prerequisites. Added pressure-test note to AD-3.
- **v0.4 (2026-05-04):** cross-Claude review of v0.3 + Phase 1 design notes v0.1. Added third framing for honest scope (relationship-layer infrastructure with workflow surfaces over it; build-prioritization test). Added risk-variance flag among net-new features (Feature 9 highest-risk). Adjusted Phase 1 estimate to 3-6 weeks (Phase 1-3 to 8-12 weeks total). Added build-time write protection to AD-5. Added default-backgrounded `pythonw` to AD-4. Added temporal dimension to Layer 2 (lineage_edges valid_from/to_version). Added stale-reference inventory potential to Feature 9 via temporal lineage_edges. Updated Phase 1 detail to reflect risk-aware sequence and added items (generation_attempts, api_calls, build-time write protection, Alembic). Pointer added to Phase 1 design notes v0.2.
- **v0.5 (2026-05-04):** parallel-Claude review of pre-commit hook scope (git lives at OpenMontage parent, not latent_systems project). Added enforcement-infrastructure carve-out to AD-5: hook install at `OpenMontage/.git/hooks/` is allowed enforcement-infrastructure (not artifact authorship). Added new general principle: "enforcement infrastructure gets explicit carve-out treatment, separate from runtime artifact authorship" — reusable for Phase 2/3 similar decisions (filesystem watcher daemon, backup script, etc.). Added existing-hook chaining requirement (back up + chain, not replace). Added hook portability to out-of-scope (single-machine v1; multi-machine = v2+). Pointer to Phase 1 design notes v0.3.
