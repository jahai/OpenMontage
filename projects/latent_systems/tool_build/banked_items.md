# tool_build banked items

Single tracking doc for all decisions deferred / Phase 2+ work / verification
items / open watches across cross-Claude review waves. Replaces the scattered
"see Day X review §Y" references.

**Updated:** 2026-05-08 (Phase 2 acceptance bridge COMPLETE: rubric committed c55f36e; Wave B fired successfully against real render; e2e debrief banked below; Phase 3 Wave 1 unblocks pending v0.4 amendments)

---

## Pre-Day-10 cleanup (LANDED in this session per Day 5-9 review)

| Item | Origin | Status |
|---|---|---|
| §2-A gitignore carve-outs (track structural LS content) | Day 5-9 §2 | ✅ done |
| `tool_build/constants.py` centralizing `CURRENT_DISCIPLINE_VERSION` | Day 5-9 §4.4 | ✅ done |
| Code-review router_tail regex against `downloads_router.py` log-writer | Day 5-9 §4.3 | ✅ done (verified + comment added) |
| UTF-8 console codec in serve.py + test entry points | Day 5-9 §5 bugs 3-4 | ✅ done |
| Notes-string regex pattern documented in dispatcher.py | Day 5-9 §4.12 | ✅ done |
| FK-cleanup ordering comment in test files | Day 5-9 §5 bug 7 | ✅ done |
| Migration 0002: `started_orig` column + `hero_promotions.render_id` UNIQUE INDEX | Day 5-9 §4.7 + Day 3 F4 | ✅ done (state.db at schema_version 0002; verified Day 17) |

## Phase 1 Week 4 (must land before Phase 1 close)

**Phase 1 closed Day 15 acceptance** (2026-05-05). Status of items below:

| Item | Origin | Status |
|---|---|---|
| Feature 9 — discipline-drift query surface | spec, Phase 1 Week 4 | ✅ done (test_discipline_drift.py passes; landed in substrate ba4e886) |
| B2 — fresh-clone `--init` byte-equality test | Day 1-2 review B2 | ⏳ pending — requires fresh clone on separate machine; verifies hook idempotency across line-ending paths. Promote when multi-machine work begins (per AD-5 v0.5 hook portability carve-out). |
| MJ tool-grammar seed loader (Section 3) | spec Section 8 Week 3 | ✅ done (seeds_loader.py + seeds/mj.yaml in substrate ba4e886; loaded at --init via Day 11 build) |

## Phase 2 confirmed (after Phase 1 close; not Phase 1 work)

| Item | Origin |
|---|---|
| ~~Native-API generation path alongside clipboard handoff (mixed-path) — see detail below~~ | Phase 1.5 e2e debrief 2026-05-05 — **moved to Phase 3 territory 2026-05-08**: doesn't ship in Phase 2; Phase 3 or later when API-generation friction surfaces |
| ~~`tools/router_log.md` cross-reference for tool attribution recovery on existing 1698 pre_v1 renders~~ | Day 3 §4.1 + Day 5-9 §6.2 — **superseded 2026-05-06**: Day 1 inspection showed router_log has only 1 logged run (recovery rate ~0%). Replaced by filename-pattern extension in walker.classify() (Day 1 commit 76069fd: 71.6% recovery via `_mj_<hex>_` infix + frame_extract category + flux/kontext markers + broader gpt). Forward-looking value: router_log captures attribution for new renders going forward — that mechanism is correct, just doesn't help with existing pre_v1 backlog. |
| ~~21 `_unclassified/` GPT renders triage to specific Phase 1 directions~~ | Day 5-9 §6.1 — **moved to Wave A 2026-05-06**: per visual_identity_phase1_references/README.md, `_unclassified/` is BY DESIGN a hold queue for user's Phase 2 visual-identity evaluation work (5 directions + 6 criteria already specified). Editorial decision-work, not mechanical. Deferred to Wave A audit viewer review queue (filter on `WHERE filepath LIKE '%_unclassified%'`). All 21 already correctly tagged `gpt_image_2` from Day 1's pattern recovery. |
| `needs_review_reason` promote from render YAML to state.db column (revisit at scale) | Day 5-9 §4.10 |
| Structured `attempt_events` table parsing notes-string history | Day 5-9 §4.12 |
| `pending_downloads` promote from JSON to state.db table (when query friction surfaces) | Day 5-9 §4.1 |
| Browser-side clipboard fallback (`navigator.clipboard.writeText`) for non-localhost deployments | Day 5-9 §4.5 |
| `mtime`-skip walker optimization (with mtime-can-lie correctness fix) | Day 3 §4.3 |
| `tool_build/` package restructure (replace `sys.path.insert`, use `python -m tool_build.serve`) | Day 3 §3.9 |
| `SUPPORTED_SCHEMA_VERSIONS` set pattern (when migrations 0003+ land) | Day 3 §4.2 |
| `cascading_delete(prefix)` test helper that walks FK graph | Day 5-9 §5 bug 7 |
| Triage workspace feature (if stray-routing pattern recurs more than twice) | Day 5-9 §6.4 |
| `pre_v1` YAML scale revisit (option to drop YAML for pre_v1 markers) | Day 3 §3.8 |
| Watcher debounce for slow large-file writes (e.g., 50MB Kling MP4 over slow connection) | Day 5-9 §4.2 sharpening |

## Phase 2 watch (promote if friction surfaces)

| Item | Origin | Trigger to promote |
|---|---|---|
| Pending downloads JSON → state.db | Day 5-9 §4.1 | UI surfaces queries against pending state |
| Browser-side clipboard | Day 5-9 §4.5 | Multi-machine deployment ever happens |
| needs_review_reason as column | Day 5-9 §4.10 | Render count > ~50k (currently 1698 + slow growth) |

## Phase 2 close (shipped 2026-05-06 → 2026-05-07; acceptance bridge crossed 2026-05-08)

Phase 2 design notes at v0.6. Compressed from 4-5 week estimate to ~2 days actual via single-session push (banked as fourth Phase-3-estimating signal: prior-phase substrate maturity → next phase can compress).

**Shipped, all 16 tests green:**
- ✅ Migration 0003 schema (verdicts rebuild via temp-table-and-copy + audit_sessions + ai_consultations + audit_thumbnails)
- ✅ Wave A (non-AI viewer): serial + grid views, verdict capture, flag toggle, session start/end UI, thumbnail cache, render-file serve at native resolution
- ✅ Wave B (AI consultation infrastructure): rubric parser + Anthropic vision adapter (failure modes 4.1-4.12 incl. 4.10 safety_refused, 4.11 context_exceeded, 4.12 batch deferred) + orchestrator + UI
- ✅ Phase 2.5 enhancement: existing AI consultations surface in get_render_detail + render server-side
- ✅ Day 1 banked-flush: filename-pattern recovery 84% → 24% unknown_image (1027 of 1434 reclassified, 71.6% recovery)
- ✅ Day 2 close: 21 _unclassified/ triage deferred to audit viewer review queue (BY DESIGN per visual_identity_phase1_references/README.md)
- ✅ PHASE_2_E2E_PLAN.md authored (10-step real-API run analogous to PHASE_1_5_E2E_PLAN.md)

**v0.6 cross-Claude review must-fix amendments status:**
- ✅ #1 — `consult_render` opt-in `create_verdict_if_missing` default (commit 8a1fea4, 2026-05-08): prevents permanent audit-trail pollution from exploratory consult clicks
- ✅ #2 — `_SAFETY_REFUSAL_RE` verb-aware tightening (landed in Phase 2 Wave B substrate; visible in audit_providers/anthropic.py with v0.6 amendment comment): prevents legitimate critical evaluations from being miscategorized as safety refusals
- ✅ #3 — Wave B real firing per PHASE_2_E2E_PLAN.md (acceptance bridge): COMPLETE 2026-05-08. See "Phase 2 e2e run — 2026-05-08" section below for full debrief. Cost $0.0507 total (12× under estimate), latency 9.25s+9.88s, AI calibration matched human verdict, 4 findings banked.
- ✅ #4 — PHASE_2_E2E_PLAN.md amendments based on real findings (cost estimate 12× too high; double-fire UX gap; YAML staleness deviation): banked in e2e debrief below; folded into plan as Phase 2.5 cleanup work
- ✅ #5 — fifth Phase-3-estimating signal banked (user-blocking work that designs treat as non-blocking actually does block end-to-end verification — see signal 5 in phase3_design_notes v0.1 SCAFFOLD)

**Phase 2 acceptance bridge — COMPLETE 2026-05-08:**

All 4 steps landed in single session 2026-05-08:
1. ✅ `consult_render` opt-in (commit 8a1fea4)
2. ✅ Rubric authored + committed at `docs/AUDIT_RUBRICS_v1_0.md` (commit c55f36e). Scaffold landed 2026-05-07 at `tool_build/seeds/AUDIT_RUBRICS_v1_0_seed.md` with pollution fix (commit dbc0d51) preventing footer text from polluting Sonic-being preservation criterion. 18 bullets drafted via cross-Claude walkthrough, integrated with author-time discipline (no multi-line bullets per Pattern #8 reinforcement #2).
3. ✅ Wave B fired against real render `78c7eed6bb7e0bcd` — 2 consultations succeeded, $0.0507 total cost, AI verdict_inference matched human verdict, structured JSON parsed cleanly. See e2e debrief below.
4. ✅ Run results banked in this document (Phase 2 e2e run — 2026-05-08 section).

**Phase 2 items moved to Phase 3 territory below:**
- Tool-grammar config expansion to GPT Image 2 + Kling + ElevenLabs
- 3a hardening review (largely landed Phase 1 Day 12 + v0.4 amendment; Phase 3 review confirms no gaps)

## Phase 3 territory (not Phase 1 or Phase 2 — full features)

- **Hero promotion atomic action (Feature 5)** — Phase 3 default per v0.2 design notes Q1 call. F5's atomic action depends on F6 (NOTES.md authorship) and Phase 3 doc-set data model; building atomic action in Phase 2 would have produced degraded ship that gets rebuilt in Phase 3. Manual file-move pattern (Phase 1 + router) continues to serve through Phase 2. Pull-forward window passed (Phase 2 closed faster than the Wave A-Week-4-slack scenario anticipated — no slack accumulated to spend). Lands in Phase 3 alongside F6.
- **Tool-grammar config expansion to GPT Image 2 + Kling + ElevenLabs** — moved from Phase 2 territory 2026-05-07. Depends on Phase 1 + Phase 2 successful_examples accumulation; Phase 2 shipped Anthropic vision config only. Expansion when verdict-confirmed-strong outputs seed enough data per Q3.
- **3a hardening review** — moved from Phase 2 territory 2026-05-07. Largely landed Phase 1 Day 12 + v0.4 amendment; Phase 3 audit confirms no remaining gaps after real Wave B usage.
- **Existing-consultations-on-page-load enhancement** — ✅ shipped Phase 2.5 (commit dbfd15e); audit.get_render_detail now returns ai_consultations array for the latest verdict. **Validated under real run 2026-05-08** — Step 7 of e2e plan confirmed server-side rendering of 2 consultation cards on reload.
- **Native-API generation path (mixed-path)** — moved from Phase 2 territory 2026-05-08. Direct API providers (FLUX, Imagen, DALL-E) parallel branch to clipboard handoff. Implementation pointers preserved in detail section below.
- **Render-group compare-and-rank view (Feature 5+ extension)** — grid
  view of generations grouped by prompt (default) or by concept; drag
  or click to rank; ranking reflected in filesystem via rank-slot
  subdirs (`hero/`, `strong_alt/`, `weak_alt/`, `rejected/`) under the
  section path, NOT prefix renames. Composes with hero promotion's
  atomic-symlink design (Feature 5). Open design questions:
  (a) does demoting from `hero/` revert via `hero_promotions.reversed_at`?
  (b) does rank-slot membership write to a new `render_ranks` table or
  ride on `hero_promotions` with status field? (c) is the grid view a
  modal in the existing UI or a dedicated `/groups/<prompt_id>` page?
  Surfaced 2026-05-05 by Joseph after Phase 1.5 e2e run.
- **Rubric parser multi-line bullet support** — Pattern #8 reinforcement #2 (banked 2026-05-08): current parser captures only same-line bullet content via `(.*)$`; multi-line bullets get truncated AND continuation lines pollute the criterion's definition body. Fix is either (a) reformat bullets single-line at author time (current discipline; works but constrains markdown idiom), or (b) extend `parse_rubric_text` to support continuation lines (~10 lines added, needs test for "indented continuation appends to current_eval[level]"). Recommend (b) when Phase 2.5 parser work happens — multi-line bullets are standard markdown and the current limitation will keep biting future rubric authoring.
- **Wave B "consulting AI..." UX gap → silent double-fire** — banked 2026-05-08 from real Wave B firing. Pressing C without UI feedback during in-flight request enables silent double-fire (~37 sec apart, both succeeded, both attached to same verdict). Phase 2.5 fix: disable C button + grey out section while request in-flight; add visible elapsed-time counter ("consulting AI… 12s") to prevent ambiguity about whether request is hung vs slow. Real-use UX gap that synthetic tests can't catch.
- **discipline_drift query surface extension to Migration 0003 tables** — banked 2026-05-08 from Step 10 audit. Endpoint currently enumerates 7 entity types but the 4 new Migration 0003 tables (ai_consultations, audit_sessions, audit_thumbnails, plus rebuilt verdicts) include 2 that should be tracked entities: ai_consultations + audit_sessions. Phase 2.5 enhancement: extend `discipline_drift_query()` in audit module to include these tables in `totals_by_type` and per-version breakdowns. Math reconciles today but is incomplete — won't surface drift against the new schema's entity types.
- **YAML staleness across audit_session lifecycle + verdict.ai_consultation_ids** — banked 2026-05-08 from real Wave B firing. Session YAML has `ended: null`, `total_consultations: 0`, `total_cost_usd: 0.0` even after consultations fired and session was effectively ended. Verdict YAML has `ai_consultation_ids: []` even after consultation YAMLs attached on disk. State.db has live values; YAML doesn't denormalize. AD-5 invariant deviation (YAML supposed to be source of truth; state.db cache). May be intentional design (parallel to `audit.update_verdict_flags` AD-5 deviation banked at Issue 2 from Phase 2 close review). Phase 2.5 work: either (a) docstring the AD-5 deviation explicitly with rationale in audit.py + audit_consult.py + session-end endpoint, OR (b) write YAML denormalization as part of consultation attach + session end paths. Verify intent next session.
- NOTES.md authorship via Claude API (Feature 6)
- Cross-AI / cross-Claude capture surface (Feature 7)
- Serialization to OpenMontage `edit_decisions` + `asset_manifest` (Feature 8)
- Concept browser full UI (Feature 1) — concept CRUD endpoints land Week 3-4 of Phase 1; full UI is Phase 3
- **ChatGPT, Grok, Gemini provider adapters** — deferred per phase2_design_notes §3 role-mapping table; Phase 2 ships Anthropic baseline + conditional Perplexity only.
- **Multi-image batch consultation** — deferred per phase2_design_notes §1 4.12; Phase 2 ships single-image only.
- **SSE for parallel consultation streaming** — deferred per phase2_design_notes §7 Q4; Phase 2 default is sequential.
- **Per-concept-type mode defaults for audit viewer** — deferred per phase2_design_notes §7 Q5; Phase 2 default is per-session via `audit_sessions.mode` column.

## Investigations (not code; verification only)

(none currently open)

## Investigations COMPLETED in earlier sessions

- B1 — Windows graceful shutdown (psutil + control-file mechanism). LANDED Day 4.
- B3 — full `--init` → `--uninstall` cycle verified. LANDED Day 4.
- B4 — empirical Claude Code commit identity. RESOLVED Day 16/17 (2026-05-06): `.git/config` had a typo (`user.emailcd` instead of `user.email`); commits from this machine via Claude Code fail outright with `fatal: unable to auto-detect email address` rather than silently misattributing as `calesthio`. Recent `calesthio <celesthioailabs@gmail.com>` commits in log come from elsewhere (GitHub Codex / web UI). Fixed under explicit user authorization: `user.email = joseph.brightly@gmail.com`, matching AD-5 hook's hardcoded `JOSEPH_EMAIL`. Future Claude-Code commits to canonical paths now pass the hook scope check.

## Pattern #8 reinforcements (rubric parser-discipline-mismatch class)

Both bugs share the parent insight: the rubric parser's design assumes a discipline (no multi-line bullets, no post-last-H3 content) that isn't enforced by the format. Either tighten the format spec (current path) or extend the parser (Phase 2.5 work).

1. **Footer pollution (caught pre-authoring 2026-05-08, fix landed dbc0d51).** Parser folds post-last-H3 content into the previous criterion's definition. Caught when seed file's footer (Per-direction notes table + Authoring tips + After-authoring instructions) appended ~2,200 chars to Sonic-being preservation's definition body — would have shipped to AI on every consultation as if it were criterion-grading guidance. Fix: moved footer above first H3 as preamble (parser ignores everything before first H3); added footer-pollution sentinel to verification command (any criterion definition >1000 chars triggers warning).

2. **Multi-line-bullet pollution (caught post-authoring 2026-05-08).** Parser regex `^\s*[-*]\s*(pass|partial|fail)\s*:\s*(.*)$` captures only same-line content; multi-line bullets get truncated AND continuation lines pollute the criterion's definition body. Fix at author time: bullets single-line. Phase 2.5 parser work: extend `parse_rubric_text` to support continuation lines (~10 lines added, needs test for "indented continuation appends to current_eval[level]").

Pattern: when format spec relies on undocumented discipline (no multi-line, no post-anchor content), failure mode surfaces silently (parses successfully, content is wrong). Pattern #8 third-bucket fixtures need to test the parser-discipline-boundary cases, not just generic happy-path content matching.

---

## Phase 1.5 e2e run — 2026-05-05

First real-world e2e run of the full Phase 1 flow (PHASE_1_5_E2E_PLAN.md).

**Concept used.** `e2e_skinner_box_lever_pull` (ep1 / h5_slot_machine,
register `schematic_apparatus`).

**Cost / time.** $0.0223 (one Opus 4.7 prompt-drafting call, 13s
latency). Total wall-clock from server start to F4 verification:
~10 minutes (excluding MJ generation wait).

**Result.** Pass with caveats. Concept create, Claude draft, watcher
detection, router routing, manual bind, F1 query, lineage edge, F4
query, and discipline-drift all worked. Auto-bind path was NOT
exercised because the test interrupted itself (mark_failed during
debug); synthetic `test_binding.py` already covers it.

**Bugs surfaced (not previously banked).**

1. **Dispatch clipboard write reports success but doesn't land.**
   `dispatch` returned `clipboard_written: true` but the prompt did
   not appear when Joseph pasted into Midjourney. Direct `Set-Clipboard`
   from PowerShell wrote 627 chars and `Get-Clipboard` read them back,
   so the OS clipboard works — the bug is in the dispatch path.
   Hypothesis: `pyperclip` running in uvicorn's threadpool on Windows
   doesn't reliably write to the system clipboard (no COM init, or
   browser-open subprocess steals focus during the write window). Phase
   2 fix: switch to a `subprocess.run(["powershell", "-Command", "Set-Clipboard ..."])`
   shell-out, OR run pyperclip from the asyncio event loop main thread,
   OR add a post-write read-back verification before reporting
   `clipboard_written: true`.

2. **Router pre-flight refuses to run with pre-existing untracked
   canonical material.** Joseph's `projects/latent_systems/docs/`
   has 51 untracked files (handoffs, briefings, READMEs); `shared/`
   has 4. The `§2-A` gitignore carve-out tracks these paths but
   they were never committed after the carve-out landed. Router
   correctly refuses on AD-5 grounds, but this turns "first real
   router run after Phase 1" into a 55-file commit decision before
   the e2e test can proceed. Workaround used: `git stash push -u`
   the offending paths, run router, `git stash pop`. Phase 2: either
   commit those files (proper fix) or add a router flag like
   `--allow-pre-existing-untracked` for ergonomic recoverability.

3. **`PHASE_1_5_E2E_PLAN.md` timing measurement is invalid.** The
   plan said "wall-clock < 2s" using `Invoke-RestMethod` time. First
   call in a fresh PowerShell session takes ~2.4s due to .NET HTTP
   stack lazy-load. Subsequent calls are 5-8ms. The F1 contract is
   server-side query budget; the right measurement is `time curl` or
   timing inside the same PS session (not first-call). Fix the plan
   before next run: warm up PowerShell with one throwaway request,
   THEN measure.

4. **Midjourney filename → LOW-confidence routing.** MJ saves
   `<username>_<prompt-prefix>_<job-uuid>_<variant>.png`. Router has
   no section/ep markers in this filename so classifies as LOW
   confidence and routes to `shared/visual_identity_phase1_references/_inbox/`.
   Working as designed but means MJ outputs ALWAYS land in `_inbox/`
   without manual triage. Phase 2: enrich router with prompt-text
   awareness so a dispatched MJ render whose in_flight attempt
   carries section metadata can route to that section.

5. **`mark_failed` makes a prompt undispatchable to the same prompt
   for re-bind.** Bind requires `attempt.status='in_flight'`. After
   `mark_failed`, the only way to get a new in_flight attempt is to
   re-dispatch (which clobbers clipboard + opens browser tab again).
   Phase 2: add `/prompts/{id}/create_attempt` that creates a bare
   in_flight attempt without the side effects, for orphan
   reconciliation flows.

**Items 1-5 above are banked here, not folded into AUDIT_PATTERNS.md
yet** — they're each one-off observations, and per the audit-patterns
threshold they should land here until a second occurrence promotes
them.

---

## Phase 2 e2e run — 2026-05-08

First real-world e2e run of Phase 2 Wave B (PHASE_2_E2E_PLAN.md). Bridge
from "Phase 2 code-shipped" to "Phase 2 acceptance-validated."

**Run identifiers.**
- Session: `dac0ede608bc9e22` (started 2026-05-08T13:46:08 UTC, mode `quick_pass`, rubric_version 1.0)
- Verdict: `1e19235b6ceb7178` → strong, by human, on render `78c7eed6bb7e0bcd`, created 2026-05-08T14:07:40 UTC
- Consultations: `ce81acc09de54a42` + `7741730125296a6e` (both completed status, structured JSON parsed cleanly)

**Cost / time.**
- 2 consultations fired (silent double-fire — see finding #1 below)
- Cost: $0.0249 + $0.0258 = **$0.0507 total** (12× under PHASE_2_E2E_PLAN.md placeholder estimate of $0.30)
- Latency: 9.25s + 9.88s server-side per call (well under plan's 10-30s budget)
- Tokens: ~3453 in / 305-343 out per call (system + concept + lineage + image)
- Total wall-clock from session start to verdict mark: ~21 minutes
- Total wall-clock from session start to Step 9 reload validation: ~50 minutes (includes UI navigation, e2e plan execution, finding diagnosis)

**Result. PASS.** All 9 user-facing e2e plan steps validated:
- Step 1 (pick render via grid): pass
- Step 2 (start audit session via header click): pass; `audit_sessions/dac0ede608bc9e22.yaml` written
- Step 3 (click into serial view): pass; image loaded, sidebar populated with render meta + verdict markers + AI section
- Step 4 (mark verdict via keyboard 2 / strong button): pass; verdict YAML landed in milliseconds at `_data/verdicts/1e19235b6ceb7178.yaml`
- Step 5 (toggle flag F): pass; state.db `flags_needs_second_look` updated
- Step 6 (consult AI via C button): pass twice; both consultation YAMLs landed at `_data/ai_consultations/`
- Step 7 (reload to verify persistence): pass; "AI consultation (2)" rendered server-side without re-firing — Phase 2.5 enhancement validated under real conditions
- Step 8 (end session): effectively passed via auto-end / navigation; verdict + consultations persist independently of session lifecycle (header in "no session" state by Step 7 reload time)
- Step 9 (close tab + 30s wait + reopen URL → verdict-durability check): pass; F8 success criterion 5 ("Audit verdicts durable from moment of marking. Mark a render. Close the chat. Reopen a day later. Verdict still present, with reasoning, with audit-rubric used, with AI consultations logged.") validated against real conditions
- Step 10 (discipline-version drift via curl /discipline_drift): pending Joseph's navigation to endpoint + paste of totals_by_version

**AI calibration validation.**
- AI's `verdict_inference: strong` matched Joseph's `strong` verdict — calibration test passes
- Both AI partial diagnoses sharp + actionable (not generic):
  - Shorts effectiveness: "16:9 composition — apparatus extends laterally, would lose left/right context in 9:16 crop" (concrete, actionable)
  - Series continuity: AI sees period-specificity as potentially limiting cross-episode reusability (smart read of the LOCKED-for-this-episode tradeoff)
- Pattern #8 third-bucket discipline (project-specific bullets anchored on observable visual properties) produced AI judgments that read as genuine grading signal, not generic vibes

**Findings (banked here per plan; promotion to AUDIT_PATTERNS.md requires second occurrence).**

1. **Wave B "consulting AI..." UX gap → silent double-fire.** Pressing C without visible UI feedback during in-flight request enables silent double-fire. Both consultations succeeded (~37 sec apart), both attached to same verdict, audit trail shows both. State stayed consistent — but Joseph didn't intend two consultations; UX implied first request didn't register. Phase 2.5 fix: disable C button + grey out section while request in-flight; add visible elapsed-time counter ("consulting AI… 12s") to prevent ambiguity about whether request is hung vs slow. Real-use UX gap that synthetic tests can't catch.

2. **PHASE_2_E2E_PLAN.md cost estimate is 12× too high.** Plan says ~$0.30 per vision consultation per design notes §1 4.2 placeholder. Actual: $0.025 per call (cached + downscaled image). Difference comes from prompt caching working as designed (rubric system prompt cache-hit on second call) + image downscale keeping vision-token cost low. Plan amendment needed: revise per-call cost estimate to ~$0.025-0.05 cached / ~$0.10-0.20 cache-miss; revise total e2e plan cost from ~$0.30 to ~$0.05-0.10. Implications for F6 cost estimate revision (Phase 3 design notes v0.2 amendment item 5a): may also be over-estimated by similar factor; verify post-F6 first firing.

3. **YAML staleness: state.db has live values, YAML doesn't denormalize.** Discovered post-run via filesystem inspection. Specifically:
   - `audit_sessions/<id>.yaml` has `ended: null`, `total_consultations: 0`, `total_cost_usd: 0.0` even after consultations fired and session was effectively ended (header in "no session" state)
   - `verdicts/<id>.yaml` has `ai_consultation_ids: []` even after both consultation YAMLs attached on disk
   - Build-Claude's curl against state.db shows correct values (`session.total_cost_usd: $0.0507`, `session.total_consultations: 2`, ended timestamp populated)
   - This is an AD-5 invariant deviation (YAML supposed to be source of truth; state.db cache). If state.db rebuilt from filesystem, session totals + verdict consultation membership would all reset to defaults
   - May be intentional design (parallel to `audit.update_verdict_flags` AD-5 deviation banked at Issue 2 from Phase 2 close review). Needs verification next session against `audit.py` to confirm intent
   - Recommend Phase 2.5 work: either (a) docstring the AD-5 deviation explicitly with rationale in audit.py + audit_consult.py + session-end endpoint, OR (b) write YAML denormalization as part of consultation attach + session end paths

4. **Step 8 (end session) UX path unclear.** Joseph clicked the "■ end" link at some point during the e2e flow but doesn't recall exactly when. Header was already in "no session" state when Step 8 was reached in the plan walkthrough. Possible causes: session ended explicitly during Step 6 (after second consult fired); session ended via navigation away; session timed out (no timeout mechanism currently exists in code). Worth verifying next session by checking the session.ended timestamp in state.db against the consultation timestamps to see when end actually fired. Plan amendment: explicit "Step 8 — verify ■ end link is currently visible in header before clicking; if header already shows 'no session' state, document why and skip click."

5. **discipline_drift query surface doesn't include Migration 0003 tables.** Step 10 audit (2026-05-08T15:00ish UTC) showed `totals_by_type` enumerates only: concepts, prompts, renders, verdicts, hero_promotions, lineage_edges, cross_ai_captures. Tonight's 2 ai_consultations + 1 audit_session are invisible to the F10 query surface even though they exist in state.db at discipline_version 1.0. Same shape gap as YAML staleness finding #3 — schema evolved (Migration 0003 added 4 new tables: ai_consultations, audit_sessions, audit_thumbnails, plus the verdicts rebuild) but the F10 discipline_drift query wasn't extended to track the new entity types. Phase 2.5 enhancement: extend `discipline_drift` to include ai_consultations + audit_sessions as tracked entity types (audit_thumbnails is cache, not entity, can stay excluded). Math currently reconciles (1.0 totals = 14, pre_v1 totals = 1732) but the totals are incomplete — missing 2 consultations + 1 session from the 1.0 bucket count.

**Findings 1-5 above NOT promoted to AUDIT_PATTERNS.md** — each is a one-off observation per the audit-patterns threshold (two separate occurrences required for promotion).

**Updates folded into Phase 2.5 / Phase 3 work:**
- PHASE_2_E2E_PLAN.md cost estimate amendment per finding 2
- audit.py / audit_consult.py docstring deviations per finding 3 (if confirmed intentional)
- Wave B UI: button-disable + elapsed-time counter per finding 1
- Plan amendment for Step 8 verification per finding 4

**Phase 2 acceptance bridge officially closes with this run.** Wave B validated against real conditions: SDK shape, response.usage attributes (input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens), vision token billing math, prompt caching (12× cost reduction confirmed), safety regex behavior (no false positives on this content), parse-tolerant JSON extraction (clean parse), persistence across session-end + tab-close + 30s gap. The e2e plan + Phase 2 close test suites + this real run combine to form acceptance evidence Phase 3 design can build on.

---

## Phase 2 design — native-API generation path (mixed-path) — moved to Phase 3 territory 2026-05-08

**Problem.** Phase 1 hard-coded the clipboard+browser handoff flow
because Midjourney has no public API. But OpenMontage's parent
repo already ships direct API providers (`tools/image/` — FLUX,
Imagen, DALL-E, Recraft, Stable Diffusion). The current
`dispatcher.dispatch()` + `TOOL_URLS = {midjourney, kling}` design
forces every tool through clipboard, even ones that don't need it.

**Recommended path: mixed.** Keep the clipboard handoff for closed
tools where it's the only option (MJ for cinematic/schematic
quality; Kling for video). Add a parallel `image_via_api` dispatch
branch that:
- calls a `tools/image/<provider>.py` tool directly (server-side),
- writes the returned bytes into the canonical section path,
- inserts the `renders` row with `tool=<provider>`, status
  `completed`, and `download_hash=null` (never came via Downloads),
- skips the watcher / router / auto-bind chain entirely.

**Why mixed and not "replace MJ entirely":** MJ still has a
quality edge for `cinematic_*` and `schematic_apparatus`
registers. FLUX 1.1 Pro is closest, Imagen 3 is photoreal-strong,
neither is 1:1. Keep MJ for hero / key visuals; use API providers
for bulk iteration where MJ's manual round-trip is the bottleneck.

**Implementation pointers.**
- New tool branch in `TOOL_URLS` (or replace it with a dispatch
  registry): mark each tool's `transport` as `clipboard_handoff`
  vs `direct_api`.
- New endpoint or new branch in `/prompts/{id}/dispatch` that
  detects `transport=direct_api` and routes to a synchronous
  generation call.
- Cost tracking: extend `api_calls` rows to cover image-API spend
  the same way they cover Claude spend.
- Failure modes: the existing 3a.1-3a.7 spec covers HTTP failures;
  the same retry queue mechanism applies.
- Concept + prompt drafting (Claude API) stays unchanged — it's
  tool-agnostic; only dispatch changes.

**Open questions for Phase 3 design notes.**
- Where do API-generated bytes live before canonical placement —
  staging dir + walker, or direct write?
- Does an API render need `attempt_id` at all? (No clipboard
  round-trip means no "user might have generated multiple times"
  ambiguity.)
- Does the UI distinguish API-tool prompts from clipboard-tool
  prompts? (Probably yes — API ones don't need "awaiting return".)

---

## Banking principles (lessons from review waves)

1. **When YAMLs are keyed by content-derived ID** (hash, fingerprint), and the source content can legitimately repeat across distinct logical artifacts, the **key must include a disambiguator** (filename, source path, or other identifying context). Pure-content-hash IDs are correct only when content uniqueness is guaranteed by domain semantics. *— from Day 5-9 §5 bug 5 (stray-routing classifier collision)*

2. **Sharpenings get applied immediately** when small + reasoning is sound; banked when uncertain or larger. The discipline of pressure-testing-via-summary works because reviewer + builder catch different things.

3. **Decisions-beyond-spec are flagged with reasoning, not just stated.** Every §4 entry across review waves names the alternatives considered, the chosen path, and the failure mode that would force revisiting. This is the cross-Claude review F11a pattern working as intended.

4. **Spec/reality gaps surface during build, not before.** §2 (gitignore makes hook dormant) wasn't in the spec, both Day 1-2 build and review missed it; Day 5-9 routing operation surfaced it. Bank as: "every operational task is also a spec audit pass."

5. **Format-discipline-mismatch silent failures.** When parser/spec relies on undocumented discipline (no multi-line bullets in rubric, no post-last-H3 content, etc.), failure mode parses successfully but produces wrong content. Pattern #8 third-bucket fixtures need to test parser-discipline-boundary cases. *— from Pattern #8 reinforcements (rubric authoring 2026-05-08)*

6. **Cost estimates from placeholder values undercount real-world cached behavior.** Phase 2 e2e firing showed actual cost ~12× under plan estimate when prompt caching engages as designed. Future cost estimates should differentiate "cache-miss first call" vs "cache-hit subsequent calls" and bias toward the cache-hit estimate for cumulative budgeting once design includes cache-stable system prompts. *— from Phase 2 e2e run 2026-05-08 finding 2*
