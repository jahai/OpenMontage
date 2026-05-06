# tool_build banked items

Single tracking doc for all decisions deferred / Phase 2+ work / verification
items / open watches across cross-Claude review waves. Replaces the scattered
"see Day X review §Y" references.

**Updated:** 2026-05-06 (Day 17 sweep: Migration 0002 status corrected, Phase 1 acceptance + Day 16/17 cleanup landed)

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
| Native-API generation path alongside clipboard handoff (mixed-path) — see detail below | Phase 1.5 e2e debrief 2026-05-05 |
| `tools/router_log.md` cross-reference for tool attribution recovery on existing 1698 pre_v1 renders (~84% currently `unknown_image`) | Day 3 §4.1 + Day 5-9 §6.2 (high-priority) |
| 21 `_unclassified/` GPT renders triage to specific Phase 1 directions | Day 5-9 §6.1 |
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

## Phase 3 territory (not Phase 1 or Phase 2 — full features)

- Audit viewer (Feature 4) + AI evaluation flow (Feature 4 sub-feature)
- Hero promotion atomic action (Feature 5)
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
- NOTES.md authorship via Claude API (Feature 6)
- Cross-AI / cross-Claude capture surface (Feature 7)
- Serialization to OpenMontage `edit_decisions` + `asset_manifest` (Feature 8)
- Concept browser full UI (Feature 1) — concept CRUD endpoints land Week 3-4 of Phase 1; full UI is Phase 3

## Investigations (not code; verification only)

| Item | Origin | Why |
|---|---|---|
| B4 — empirical `git log -1 --format='%an <%ae>'` after a real Claude Code commit | Day 1-2 B4 | Determine what identity Claude Code commits actually carry. Hook reads `git config user.name` (full scope fallthrough). Currently shows `calesthio` somewhere; need to know if hook will catch real CC commits or silently allow them. |

## Investigations COMPLETED in earlier sessions

- B1 — Windows graceful shutdown (psutil + control-file mechanism). LANDED Day 4.
- B3 — full `--init` → `--uninstall` cycle verified. LANDED Day 4.

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

## Phase 2 design — native-API generation path (mixed-path)

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

**Open questions for Phase 2 design notes.**
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
