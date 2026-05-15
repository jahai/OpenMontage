# Unified Production Tool — Scoping Document v2

**Status**: Draft for Joseph review. Not yet committed. Supersedes v1 (uncommitted draft).
**Date**: 2026-05-15
**Decision context**: Joseph expanded scope from v1 (Higgsfield-only + Claude-in-app) to v2 (full production OS: Perplexity research + Higgsfield exploration + ComfyUI consistency + ElevenLabs voice + Claude orchestration). MidJourney skipped (no official API, third-party MCP wrappers operate in TOS gray zone). Skinner sequence becomes validation pilot. Hybrid build strategy: minimal scaffolding for pilot, then full app build informed by pilot lessons.

## What this is

A unified production OS where Joseph orchestrates EP1 (and subsequent episodes) inside one application. The app is **production memory and connective tissue** between specialized AI services — not a replacement for any of them.

Components:
- **Research and truth layer** — Perplexity (via official MCP)
- **Creative orchestration** — Claude-in-app via Anthropic API + MCP tools
- **Visual exploration** — Higgsfield (via official MCP)
- **Visual consistency** — ComfyUI Cloud (via official MCP)
- **Voice generation** — ElevenLabs (via official MCP)
- **Audit and approval** — extends existing tool_build rubric pipeline
- **Editorial assembly** — timeline + live playback
- **Production memory** — script beats, shot cards, research cards, workflows, references, candidates, approvals — all persisted

Built BY Joseph (directing Build-Claude), FOR Joseph (single user), to make EP1 and validate the production system for EP2-EP10.

## Architectural principle: the app is connective tissue

The visual production bible's core insight applies: **the app should not try to be "ComfyUI but simpler" or "Higgsfield but unified."** It should be the production memory that connects research, script, shots, prompts, workflows, generations, and approvals. Each specialized service keeps its specialized role:

- **Perplexity** = truth layer (research, citations, claim checking, visual constraints)
- **ComfyUI** = consistency engine (saved workflows, character/apparatus repeatability, exact seed/model/LoRA control, image-to-video for controlled motion)
- **Higgsfield** = exploration engine (fast cinematic variants, motion discovery, model comparison across 30+ models)
- **ElevenLabs** = voice engine (Daniel narration, voice profile management, audio asset generation)
- **Anthropic API / Claude** = orchestration layer (sees app state via MCP, calls other services, partners with Joseph editorially throughout)
- **The app** = remembers everything, surfaces the right context, gates progression, audits results

This division of labor protects against the common failure mode: an app that tries to be everything ends up being mediocre at all of it. Specialized services stay specialized. The app conducts the orchestra.

## What this is NOT

- Not a multi-user product
- Not a SaaS offering
- Not deployment-ready
- Not a ComfyUI replacement
- Not a Higgsfield replacement
- Not a generic AI tool
- Not optimized for users-who-aren't-Joseph
- Not Latent Systems Studio (the product) — yet
- Does not include MidJourney integration (no official API; third-party MCP wrappers operate in TOS gray zone; equivalent aesthetic achievable via Higgsfield's Nano Banana Pro / Soul 2 / GPT Image 2 + ComfyUI workflows)

## Productization optionality (deferred, preserved)

Per Joseph's call: "personal first BUT keep in mind productization later."

**Made WITH productization in mind**:
- Code architecture: clean separation of concerns, modular service boundaries
- Data models: extensible to multi-user (`user_id`/`project_id` fields present even at single-user scale)
- Configuration: file-based per-project, not global constants
- Auth/secrets: env-var-based, ready for proper secret management later
- API surface: REST/GraphQL endpoints structured as if external clients existed
- MCP servers: standard protocol, swappable, not hardcoded

**Explicitly deferred**:
- Login UI / user management
- Billing / subscription / payment processing
- Multi-tenant data isolation
- Per-user quotas and rate limiting
- Public marketing surface
- Onboarding flows
- Support documentation
- Cloud deployment infrastructure
- CDN / edge caching
- Cross-region replication
- Compliance work (GDPR, SOC2, etc.)

## Architecture

### High-level system shape

```
┌────────────────────────────────────────────────────────────────────┐
│  Unified Production App (browser-accessed, localhost)               │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Script   │  │ Research │  │ Shot     │  │ Generation       │  │
│  │ Editor   │  │ Drawer   │  │ Board    │  │ Surface          │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                                      │
│  ┌──────────────────┐  ┌─────────────────────────────────────┐   │
│  │ Audit / Verdicts │  │ Timeline + Live Playback             │   │
│  └──────────────────┘  └─────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Claude Chat Surface (always-visible side panel)             │   │
│  │  ↔ sees app state via app-state MCP                          │   │
│  │  ↔ acts on app and external services via MCP tools           │   │
│  └────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
                                  ↕
                  ┌───────────────────────────┐
                  │ Anthropic API             │
                  │ (Claude inference engine) │
                  └───────────────────────────┘
                                  ↕
        ┌─────────────────────────────────────────────────────┐
        │ MCP Layer (five MCP integrations)                    │
        │                                                       │
        │  ├─ Higgsfield MCP (exploration / motion)            │
        │  ├─ ComfyUI Cloud MCP (consistency / workflows)      │
        │  ├─ ElevenLabs MCP (voice generation)                │
        │  ├─ Perplexity MCP (research / Sonar / claim check)  │
        │  └─ App-state MCP (custom — exposes app data         │
        │     to Claude: shot cards, research cards, verdicts, │
        │     sequences, references, scripts)                  │
        └─────────────────────────────────────────────────────┘
                                  ↕
        ┌─────────────────────────────────────────────────────┐
        │ App Backend Services                                  │
        │                                                       │
        │  ├─ Production memory database (SQLite)              │
        │  │   - Projects, Episodes, Sequences                 │
        │  │   - ScriptBeats, ShotCards                        │
        │  │   - ResearchCards, ClaimChecks                    │
        │  │   - VisualConstraintSets, PromptVersions          │
        │  │   - Workflows, ReferencePacks                     │
        │  │   - GenerationJobs, Assets                        │
        │  │   - Verdicts, ReviewNotes                         │
        │  │   - Timeline state                                 │
        │  ├─ File storage (renders, audio, timeline exports)  │
        │  ├─ Status pipeline state machine                    │
        │  ├─ Audit pipeline (extends existing rubric)         │
        │  └─ Generation ingestion (auto-routes MCP outputs)   │
        └─────────────────────────────────────────────────────┘
```

### Five MCP integrations

**1. Higgsfield MCP** (already connected at chat.claude.ai)
- Role: Exploration / motion / fast cinematic variants
- Models: Soul 2, Nano Banana Pro, GPT Image 2, Kling 3.0, Seedance 2.0, Veo 3.1, Flux 2, Seedream v4.5, and ~25 more
- Use case: "Discover the look fast. Test 6 models in parallel. Find what works visually."
- Output: Hosted on Higgsfield CDN, fetched into app's asset registry
- Endpoint: `https://mcp.higgsfield.ai/mcp` (HTTP transport)

**2. ComfyUI Cloud MCP** (official, `@comfy/mcp-server`)
- Role: Consistency engine / saved workflows / repeatable production
- Use case: "Once we know the look, port to ComfyUI. Locked character, locked apparatus, locked seed bands, repeatable across 20+ shots."
- Output: Cloud GPU rendering, retrieved into app
- Storage: Workflow JSON saved in app's Workflow table for reuse
- Setup: API key via Comfy Cloud account; MCP server connects automatically

**3. ElevenLabs MCP** (official, `@elevenlabs/elevenlabs-mcp`)
- Role: Voice generation / Daniel narration / voice profile management
- Use case: "Generate Beat 4 VO at X=24, validate per voice profile parameter map. Run voice design exploration. Apply pronunciation dictionary."
- Output: Audio files ingested into existing `audio_assets` table
- Capabilities: Text-to-speech, voice cloning, voice design, transcription, audio isolation, pronunciation dictionaries
- Setup: ELEVENLABS_API_KEY env var; runs via `uvx elevenlabs-mcp`

**4. Perplexity MCP** (official, `@perplexity-ai/mcp-server`)
- Role: Research / truth layer / Sonar models / claim checking
- Models: sonar, sonar-pro, sonar-reasoning-pro, sonar-deep-research
- Use case: "Generate research card for §3. Run claim check on this narration line. Verify period accuracy. Deep research on specific historical detail."
- Output: Source-grounded answers with citations, stored in ResearchCards/ClaimChecks tables
- Setup: PERPLEXITY_API_KEY env var

**5. App-state MCP server** (custom — built by Joseph + Build-Claude in Phase 1)
- Role: Exposes app's own data to Claude
- Tools (~15-20 in v1):
  - **Read tools**: `get_project_state`, `get_research_cards`, `get_shot_cards`, `get_verdicts`, `get_assets`, `get_workflows`, `get_reference_packs`, `get_scripts`, `get_sequences`, `get_timeline_state`, `search_assets`, `search_by_status`
  - **Write tools**: `update_shot_status`, `create_research_card`, `link_research_to_shot`, `add_verdict`, `store_workflow`, `attach_reference_pack`, `create_visual_constraints`, `update_timeline`
- Implementation: Python MCP server in tool_build, stdio transport
- Design principles: token-efficient responses, drill-down via additional calls, idempotent writes

### Anthropic API integration

**Architecture**: Claude consumes the five MCP servers above via Anthropic API. App runs Claude as a backend service with conversation state management.

**Context management strategy** (critical — this determines whether the app feels magical or frustrating):

- Per-turn injection: app prepends a concise "project state summary" to each Claude request (current section, recent verdicts, active shot cards). ~500-1000 tokens.
- Drill-down via tool calls: Claude requests detail via `get_*` tools when context summary is insufficient.
- Conversation history pruning: keep last 10 turns full, summarize older turns to ~100 tokens each.
- Multi-modal where useful: send rendered thumbnails to Claude for "look at this and tell me if pacing works" beats.

**Cost management**:
- Per-conversation budget caps (warn at $0.50, hard limit at $2.00 per conversation by default)
- Per-day budget caps (warn at $20, hard limit at $50 per day by default)
- Configurable thresholds in app settings

## Data model

Substantially expanded from existing tool_build (which has: renders, verdicts, concepts, audio_assets, sections sidecar).

### Existing tables (extended)

- **concepts** — already exists; extended with new relationships to ShotCards
- **renders** — becomes a subtype of generic Asset; new metadata fields for full MCP audit trail
- **verdicts** — extended with linkage to status pipeline
- **audio_assets** — extended for ElevenLabs MCP outputs and voice profile metadata
- **sections** — already exists via sidecar; remains canonical structural document

### New tables

#### projects
```
id, name, description, created_at, updated_at, user_id
```

#### episodes
```
id, project_id, episode_number, title, status, created_at, updated_at
```

#### sequences
Sequences are sub-units within sections — e.g., the Skinner sequence within §3. Lets a section contain a multi-shot mini-film.
```
id, episode_id, section_id, name, runtime_target_seconds,
narrative_arc, status, created_at, updated_at
```

#### script_beats
```
id, episode_id, section_id, sequence_id (nullable), beat_number,
timecode_in, timecode_out, narration_text, voice_profile_tier (X=20/22/24),
emotional_function, required_visuals, factual_constraints,
status, created_at, updated_at
```

#### research_cards
```
id, project_id, episode_id, script_beat_id (nullable), shot_card_id (nullable),
topic, question, answer, key_facts (jsonb), visual_implications (jsonb),
safe_inferences (jsonb), avoid_claims (jsonb), confidence (high/medium/low),
source_quality_notes, status (draft/reviewed/approved/deprecated),
perplexity_session_id, created_at, updated_at
```

#### research_sources
```
id, research_card_id, title, url, domain, snippet, date, last_updated,
source_type (primary/secondary/academic/archive/news/unknown),
credibility_note, fetched_at
```

#### claim_checks
```
id, claim_text, related_research_card_ids (jsonb),
verdict (verified/likely/inferred/creative_metaphor/unsupported/contradicted),
explanation, required_revision, risk_tags (jsonb), sources (jsonb),
status, perplexity_session_id, created_at
```

#### visual_constraint_sets
```
id, shot_card_id, research_card_ids (jsonb),
must_include (jsonb), may_include (jsonb), avoid (jsonb),
anachronism_risks (jsonb), prompt_addendum, negative_prompt_addendum,
source_ids (jsonb), created_at
```

#### shot_cards
```
id, project_id, episode_id, section_id, script_beat_id (nullable),
sequence_id (nullable), shot_family, composition, prompt_text,
avoid_list (jsonb), references (jsonb), aspect_ratio,
tool_route (comfyui/higgsfield/elevenlabs/composite),
visual_constraint_set_id (nullable),
status (research_needed/research_cleared/prompt_drafted/test_generated/
candidate_selected/consistency_pass/factual_qa/editorial_approved/locked_for_edit),
approved_asset_id (nullable), created_at, updated_at
```

#### prompt_versions
```
id, shot_card_id, version_number, prompt_text, negative_prompt,
model, parameters (jsonb), reference_images (jsonb), workflow_id (nullable),
created_at, created_by (user_id or "claude"), notes
```

#### workflows
```
id, project_id, name, tool (comfyui/higgsfield/elevenlabs),
workflow_json (jsonb), node_dependencies (jsonb), model_files (jsonb),
parameters (jsonb), notes, output_examples (jsonb),
status (draft/validated/locked/deprecated), created_at, updated_at
```

#### reference_packs
```
id, project_id, name, pack_type (character/apparatus/style/location/composition),
description, reference_images (jsonb), negative_references (jsonb),
descriptive_prompt, avoid_list, preferred_aspect_ratios (jsonb),
status (draft/approved/locked), created_at, updated_at
```

Example reference packs for EP1:
- Young Skinner Pack (character)
- Operant Apparatus Pack (apparatus)
- Episode 1 Look Pack (style)
- Boylston Hall Lab Pack (location)
- Mirror Motif Pack (composition)

#### generation_jobs
```
id, shot_card_id (nullable for exploration), prompt_version_id,
tool (higgsfield/comfyui/elevenlabs), external_job_id, status,
parameters (jsonb), references_used (jsonb), workflow_id (nullable),
cost_credits, cost_usd, started_at, completed_at, error_message (nullable)
```

#### assets
```
id, generation_job_id, project_id, file_path, file_type (image/video/audio),
thumbnail_path, duration_seconds (nullable), resolution, file_size_bytes,
metadata (jsonb — prompt, seed, model, references, etc.),
ingested_at, status
```

Note: existing `renders` and `audio_assets` tables become specialized views/subtypes of `assets` (or `assets` becomes a superset that absorbs them — design decision at implementation time).

#### review_notes
```
id, asset_id, issue_type (factual_risk/visual_drift/continuity/tone/composition),
note_text, suggested_action, status (open/resolved/ignored),
created_at, created_by (user_id or "claude")
```

#### timeline_state
```
id, episode_id, section_id (nullable), structure (jsonb — beats, assets, durations),
last_modified, last_played_at, export_count
```

## Status pipeline (9 stages)

Per visual production bible — applies to every shot that needs to be generated:

1. **Research needed** — Shot card created, no research yet
2. **Research cleared** — ResearchCard linked and approved
3. **Prompt drafted** — Initial prompt + VisualConstraintSet generated
4. **Test generated** — First candidate(s) generated, awaiting selection
5. **Candidate selected** — Joseph or Claude picks a candidate to advance
6. **Consistency pass** — Verified against ReferencePacks (character, apparatus, style)
7. **Factual QA** — ClaimCheck passed, no anachronism risks
8. **Editorial approved** — Joseph signs off on the shot
9. **Locked for edit** — Shot is final, ready for timeline

**State transitions**: each stage has gate criteria. Cannot skip stages. Backwards transitions allowed (e.g., editorial rejection → back to "prompt drafted").

**Gate criteria for advancement**:
- 1 → 2: At least one approved ResearchCard linked
- 2 → 3: PromptVersion exists, VisualConstraintSet generated
- 3 → 4: At least one GenerationJob completed successfully
- 4 → 5: Joseph or Claude designates winner from candidates
- 5 → 6: Verdict graded against rubric, passes Consistency criterion
- 6 → 7: Verdict graded against Documentary integrity v1.1, passes apparatus/period accuracy
- 7 → 8: Joseph approves explicitly (audit rubric pass + editorial signoff)
- 8 → 9: Asset locked in timeline, no further changes allowed

**Pipeline visualization**: app shows per-section status board (kanban-style) with shots in their current stage.

## Skinner sequence as validation pilot

Per the Workflow Validation Pilot doc — the Skinner sequence is the first real test of the full production system.

**Pilot success conditions** (from validation doc):
- Creative control: sequence feels like premium short film, not AI clips collection
- Consistency: character + apparatus + lighting + grammar stable across shots
- Factual discipline: dramatic without false claims (no "Skinner invented infinite scroll")
- Workflow validation: every approved shot has linked research, prompt constraints, generation metadata, review status

**Five validation gates**:
1. Research Lock — all research cards approved
2. Style Frame Lock — 5-8 approved keyframes
3. Workflow Repeatability — 3+ shot families reproducible via saved ComfyUI workflows
4. Motion Viability — Higgsfield motion + ComfyUI image-to-video both produce usable cuts
5. Edited Pilot Cut — standalone short film grade, app audit trail complete

**Hybrid build strategy** (per Joseph's call):

The pilot runs DURING app construction, not after. Minimal app scaffolding precedes pilot start; full app build completes informed by pilot lessons.

### Phase 0 — Minimal pilot scaffolding (~3-5 days)

Just enough app structure to run the Skinner pilot. Not full production app yet.

**Deliverables**:
- ResearchCard + ClaimCheck schema + Perplexity MCP integration
- ShotCard schema + status pipeline state machine (skeletal)
- ReferencePack schema for character/apparatus/style packs
- Asset ingestion from Higgsfield + ComfyUI (file-based, minimal UI)
- Simple shot board (list view) showing pilot shots and their status
- Basic Claude chat surface (no fancy UI, just functional)
- App-state MCP server v0 (5-8 tools — read research cards, read shot cards, update status, link cards)

**Goal**: Pilot can run inside the app, even if UI is rough.

### Phase 1 — Skinner pilot execution (~7 days)

Run the validation pilot using Phase 0 scaffolding.

**Day-by-day** (from pilot doc):
- Day 1: Short-film beat map locked, ShotCards created, ResearchCards drafted
- Day 2: Research + constraint lock, ResearchCards approved, ClaimChecks run, VisualConstraintSets built, Young Skinner + Apparatus + Style reference packs built
- Day 3: Look discovery via Higgsfield, 5-8 keyframes selected
- Day 4: ComfyUI workflow build for repeatable shot families
- Day 5: Motion tests (Higgsfield + ComfyUI image-to-video)
- Day 6: Assembly cut + sound + temporary grade
- Day 7: Validation review (5-10 viewers if available; otherwise solo audit + scale-up decision)

**Pilot output**:
- Edited Skinner sequence cut (~90-180s)
- Full audit trail in app for every approved visual
- Rejection log
- Workflow library (ComfyUI workflows saved + reusable)
- Reference packs (character/apparatus/style) locked
- Scale-up decision: green/yellow/red light for rest of EP1

### Phase 2 — Full app build (~4-5 weeks)

Build out the production OS informed by pilot lessons.

**Deliverables**:
- Polished script editor with AI collaboration (Claude reads/writes/edits via MCP)
- Polished generation surface with multi-model testing, side-by-side comparison
- Full research drawer with Perplexity-backed source browsing
- Full shot board with kanban view, status filters, batch operations
- Audit pipeline UI extending existing rubric system
- Timeline editor with live playback
- ElevenLabs MCP integration with voice profile management
- App-state MCP server expanded (15-20 tools)
- Conversation history persistence
- Cost tracking dashboards (per-section, per-shot, per-conversation)
- Export pipeline (timeline → .mp4 cuts for external review)

### Phase 3 — Rest of EP1 production (~3-4 weeks)

Use the validated production OS to produce the rest of EP1's heroes (K1, H#5, H#9, etc.) and section work. Each hero gets its own sequence plan + channel-staple integration audit + pilot-style validation pass (lighter weight since architecture is proven).

**Deliverables**:
- All EP1 hero sequences produced
- All EP1 sections composed in timeline
- Final cut assembled
- Audio mix complete
- Color grade applied
- Ship-ready master

## Total timeline

**Phase 0 (pilot scaffolding)**: 3-5 days
**Phase 1 (Skinner pilot)**: 7 days
**Phase 2 (full app build)**: 4-5 weeks
**Phase 3 (EP1 production)**: 3-4 weeks

**Total**: 8-10 weeks to EP1 ship.

This assumes:
- Build-Claude does most engineering implementation
- Joseph directs and reviews architecture decisions
- Parallel work where possible (Joseph creative work during Build-Claude engineering)
- No major architectural rebases mid-stream

## What gets kept from current tool_build

The existing tool_build infrastructure is the foundation, not the discard pile:

- ✅ Audit pipeline (verdicts, renders, concepts, rubric) — extends into universal status pipeline
- ✅ Section sidecar (section_structure.yaml v1.0) — used directly, becomes canonical sequence definition
- ✅ Rough-cut player — replaced by Phase 2 timeline (asset-binding logic transfers)
- ✅ Audio assets table + management — extends into ElevenLabs MCP integration
- ✅ Migration discipline (Alembic) — continues
- ✅ Test suite — extends (currently ~99 tests baseline)
- ✅ AD-5 protected paths discipline — continues
- ✅ Session_starter / banked_items.md pattern — continues
- ✅ Git history of sprint work — durable
- ✅ Verdict-grading rubric (v1.1 with sharpened Documentary integrity) — load-bearing for status pipeline

What gets replaced:
- ❌ One-shot `_inbox_review/` classifier → production-grade ingestion pipeline triggered by MCP outputs
- ❌ Manual file handling → automated ingestion via MCP + app-state coordination
- ❌ Rough-cut player (HTML-only) → full timeline editor with live playback

## What gets added

- 🆕 Anthropic API integration (Claude-in-app)
- 🆕 Five MCP integrations (Higgsfield, ComfyUI Cloud, ElevenLabs, Perplexity, custom app-state)
- 🆕 Chat UI / Claude interaction surface
- 🆕 Script editor (markdown-aware, voice-profile-aware, AI-collaborative)
- 🆕 Generation UI (multi-model testing, side-by-side comparison)
- 🆕 Research Drawer (Perplexity-backed research card management)
- 🆕 Shot Board (kanban-style status pipeline visualization)
- 🆕 Reference Pack management (character/apparatus/style packs)
- 🆕 Timeline editor with live playback
- 🆕 Full data model (ResearchCard, ClaimCheck, ShotCard, ReferencePack, etc.)
- 🆕 Status pipeline state machine
- 🆕 Cost tracking (per-conversation, per-section, per-day)
- 🆕 Frontend (TypeScript + React, replaces current minimal HTML)

## Real estimated costs

**Engineering time**: 8-10 weeks of focused work. Joseph + Build-Claude. ~$0 direct labor cost; opportunity cost real but absorbed by Phase 3 producing EP1 during/after build.

**API costs during build**:
- Anthropic API: $50-150/month at building-velocity Claude usage
- Higgsfield: $99/month Ultra (already committed; 6000 credits/month)
- ComfyUI Cloud: ~$20-60/month depending on usage tier
- ElevenLabs: ~$22/month Starter or $99/month Creator (depending on character volume)
- Perplexity: $20/month Pro tier (with API access via Pro)

**API costs at production**:
- Anthropic API: $100-300/month at heavy single-user usage during EP1 production
- Higgsfield: $99/month, potentially upgrade if credit usage exceeds plan
- ComfyUI Cloud: $30-100/month at production usage
- ElevenLabs: $22-99/month depending on Daniel narration volume
- Perplexity: $20/month

**Infrastructure**: $0 (localhost-only)

**Total monthly during build**: ~$210-430/month
**Total monthly at production**: ~$270-620/month

Within Joseph's stated funding window. Real but manageable.

## Real engineering tech stack

**Backend** (extends existing tool_build):
- Python 3.14 (existing)
- FastAPI (existing pattern in tool_build/app.py)
- SQLite (existing; single-user appropriate, swappable to Postgres for productization)
- Alembic migrations (existing discipline)
- Pytest (existing test suite, ~99 tests baseline)
- New: `anthropic` Python SDK for Anthropic API integration
- New: MCP client implementation in Python (for app calling MCP servers + custom app-state MCP server)

**Frontend** (new):
- TypeScript + React (standard, well-supported by AI assistance)
- shadcn/ui or Mantine for UI components (Build-Claude proposes during Phase 1)
- Tailwind CSS
- React Query for backend state management
- Real-time updates via Server-Sent Events or WebSocket for generation status

**External services**:
- Anthropic API for Claude
- Higgsfield MCP via existing connection
- ComfyUI Cloud + official MCP
- ElevenLabs + official MCP
- Perplexity + official MCP

**Deployment**: localhost first. App runs on Joseph's desktop. Backend on `localhost:7890` (existing pattern); frontend on `localhost:3000` or similar.

## Open questions deferred to Phase 0 architecture document

These don't get decided in this scoping doc. They get answered as Phase 0 begins and design becomes concrete.

1. **MCP tool design for app-state server**: Exactly which tools, what parameters, what return shapes? Resolution: Phase 0 architecture doc.

2. **Context management strategy specifics**: How much project state per turn? Auto-injected vs requested-on-demand? Resolution: Phase 0 design; iterate based on UX.

3. **Frontend component library**: shadcn/ui vs Mantine vs custom? Resolution: Phase 0 architecture doc.

4. **Real-time playback architecture**: Browser MediaSource API vs Electron native? Resolution: Phase 2 design work when timeline is being built.

5. **Anthropic API key management**: Env var only, or file-based with rotation? Resolution: Phase 0 (env var for now, file-based for productization later).

6. **Conversation persistence**: Per-session in-memory only, or persisted to database? Resolution: Phase 0 (likely simple per-session in v1, persisted in v2).

7. **MCP server hosting**: All MCP servers run as separate processes, or some in-process? Resolution: Phase 0 — likely separate processes for external MCPs (Higgsfield, ComfyUI, ElevenLabs, Perplexity), in-process for custom app-state MCP.

8. **Cost cap UX**: How are budget warnings surfaced? In-conversation? Settings page? Both? Resolution: Phase 2 UX design.

9. **Generation cost budgets per section**: Hard-set or learned? Resolution: Phase 3 UX design based on pilot data.

10. **Failover and offline mode**: What happens if Higgsfield/ComfyUI/ElevenLabs/Perplexity are down? Resolution: Phase 2 — likely graceful degradation with clear UI status, no hard offline mode for MVP.

## What this commits to

- 8-10 week timeline for full unified production OS + EP1 ship
- Architecture: Claude-in-app via Anthropic API + 5 MCP integrations
- Single-user, localhost, no productization features
- Code structure ready for eventual productization without paying productization cost now
- Skinner sequence as validation pilot (Phase 1)
- Hybrid build: minimal scaffolding for pilot, full app build informed by pilot lessons
- Universal 9-stage status pipeline applied to all generated assets
- Build on existing tool_build foundation; add new layers
- Five external MCPs: Higgsfield + ComfyUI Cloud + ElevenLabs + Perplexity + custom app-state MCP
- No MidJourney integration (TOS gray zone; equivalent aesthetic via Higgsfield + ComfyUI)

## What this does NOT commit to

- Specific frontend framework details (Phase 0 decision)
- Specific MCP tool inventory (Phase 0 design)
- Specific UI/UX patterns (per-phase design)
- Productization timeline or commitment (deferred indefinitely)
- Real-time editing performance targets (Phase 2 design)
- Backwards compatibility with any non-Joseph users (none exist)
- Specific cost caps (Phase 2 UX decision)
- Failover/offline behavior beyond graceful degradation (Phase 2)

## First concrete next move

**Phase 0 architecture document drafted by Build-Claude.**

After this scoping doc is committed:
1. Joseph fires Build-Claude directive: "Read scoping doc v2. Draft Phase 0 architecture document covering: app-state MCP server design (tool inventory, schemas, transport), Anthropic API integration approach, frontend stack selection, ResearchCard + ShotCard + ReferencePack data model details, Phase 0 deliverable specifications. Surface 5-10 architectural decisions needed and propose defaults. Don't begin coding yet."
2. Joseph reviews Phase 0 architecture doc
3. Once approved, Phase 0 engineering begins with concrete tickets
4. Phase 0 lands in 3-5 days
5. Skinner pilot starts Phase 1 immediately after

Joseph stays creative-direction. Build-Claude does engineering architecture (informed by this scoping). Coding follows architecture approval.

## Decision authority

This scoping document is Joseph's editorial call, made 2026-05-15 after explicit consideration of:
- Latent Systems Studio as product (rejected — too ambitious for current ambition)
- Personal tool only (rejected — productization optionality matters)
- Personal-first-with-productization-optionality (accepted)
- 4-5 week MVP scope (rejected — too narrow given pilot doc + production bible + Perplexity spec)
- 8-10 week MVP scope (accepted — full production OS with pilot validation)
- Parallel build with EP1 production (accepted, Hybrid pilot-first strategy)
- MCP + Anthropic API architecture (accepted, after correction from earlier REST API recommendation)
- ComfyUI Cloud (accepted)
- ElevenLabs MCP integration (accepted)
- Perplexity MCP integration (accepted)
- MidJourney MCP integration (rejected — no official API, TOS gray zone)
- Universal 9-stage status pipeline (accepted)

Banked as legitimate production-driven engineering investment. Aligns with the channel reframe (2026-05-15, commit 964bf4d): ship when pipeline meets standard, build pipeline by using it.

References documents:
- `docs/EP1_VISUAL_PRODUCTION_BIBLE_v1.md` (to be committed)
- `docs/integration_specs/PERPLEXITY_INTEGRATION_SPEC_v1.md` (to be committed)
- `docs/sequence_plans/SKINNER_SEQUENCE_WORKFLOW_VALIDATION_PILOT_v1.md` (to be committed)
- `docs/sequence_plans/SKINNER_SEQUENCE_PRODUCTION_PLAN_VERSION_B.md` (committed pending)
- `docs/sequence_plans/SKINNER_SEQUENCE_AUDIT_VERSION_B.md` (drafted pending)
- `docs/PROJECT_REFRAME_2026-05-15.md` (committed: 964bf4d)
- `docs/AUDIT_RUBRICS_v1_0.md` (committed: 61ac94f)
- `projects/latent_systems/ep1/section_structure.yaml` (committed: 131cec0)
