# Claude Code session starter — paste this into any fresh `claude` session

**Purpose.** Re-orient a new Claude Code instance to the current state of the
Latent Systems tool_build project. Skeleton stable; "Active task" section
updates when work shifts. Replaces ad-hoc orientation prompts.

**How to use.**
1. `cd /c/Users/josep/Desktop/desktop1/OpenMontage`
2. `claude` (fresh session) or `claude --resume` (if you want to pick up an
   in-flight session — usually fresh is cleaner for bounded tasks)
3. In the Claude Code REPL (NOT in bash directly), paste a prompt like:
   "Read `projects/latent_systems/tool_build/SESSION_STARTER.md` and follow
   its instructions. Run the state-check, then execute the active task."

---

# Project orientation

You are working on **Latent Systems tool_build** — the production-tooling
substrate for an AI-native investigative-essay documentary YouTube channel
(behavioral psychology + attention economy). EP1 is "THE BUSINESS OF
ADDICTION" launching 2026-05-16.

The project lives at `projects/latent_systems/tool_build/` inside the
parent OpenMontage repo. Phase 1 + Phase 2 are code-shipped; Phase 3 prep
substrate is durable; Phase 3 Wave 1 code is gated on Phase 2 acceptance
bridge crossing.

## AD-5 hook scope (CRITICAL — pre-commit hook enforces)

The pre-commit hook at `.git/hooks/pre-commit` REFUSES to commit changes
under `projects/latent_systems/{shared,ep1,docs,tools}/` and `NOTES.md` /
`PROJECT_ARCHITECTURE.md` at the project root. These paths are Joseph's
canonical creative output — Claude Code commits would corrupt the
audit trail.

**Claude Code is allowed to write to:** `projects/latent_systems/tool_build/`
(and only that subtree). If you find yourself wanting to write to any
canonical path under shared/ ep1/ docs/ tools/, STOP and surface to Joseph.
He commits those paths himself.

The hook also restricts commits to specific authoring identities. If you
hit `pre-commit hook FAILED: identity check`, your `git config user.email`
isn't set right; surface and Joseph fixes via explicit authorization.

## Read these to load context (in priority order)

1. **`tool_build/banked_items.md`** — single tracking doc for deferred
   items, watch-list items, completed investigations, known quirks.
   Most-recent entries at top of relevant section. **This is the
   source of truth for "what's done / what's pending."**
2. **`tool_build/AUDIT_PATTERNS.md`** — 8 recurring failure patterns
   with rules + how-to-apply. Read when about to write tests, regex,
   or anything content-matching. Pattern #2 (cascading_delete), #3
   (console encoding), #7 (derived-IDs test infrastructure), #8
   (content-matching with project-specific test fixtures) bite the
   most often.
3. **Current-phase design notes** — `tool_build/phase[1|2|3]_design_notes.md`
   maintenance log at bottom shows what landed when. Currently Phase 3
   v0.3 is the active design substrate; Phase 2 v0.6 is closed; Phase 1
   v0.4 is closed.
4. **Most recent commits** — `git log --oneline -20` shows what landed
   recently. Phase 2 close + Phase 3 prep work landed in the last few
   sessions.

## State-check (run BEFORE making any code changes)

```bash
# 1. Working tree
git status
# Expected: clean. Joseph commits canonical-path work himself.

# 2. Recent commits
git log --oneline -10
# Expected: shows recent Phase 3 prep work landed cleanly.

# 3. Schema version
sqlite3 projects/latent_systems/tool_build/_data/state.db \
  "SELECT value FROM app_meta WHERE key='schema_version'"
# Expected: 0003 currently. Phase 3 Wave 1 lands 0004.

# 4. Test baseline (scripts, NOT pytest — see banked_items.md "Test runner")
for f in projects/latent_systems/tool_build/tests/test_*.py; do
  python "$f" >/dev/null 2>&1 && echo "PASS: $(basename $f)" || echo "FAIL: $(basename $f)"
done
# Expected: 15 PASS lines. Tests are standalone scripts (main() + cleanup()
# bookends, write to real state.db with prefix-keyed cleanup). pytest
# discovery skips main()/cleanup() → pollutes state.db with orphan rows
# that cause UNIQUE constraint failures on retry. Don't run pytest here.

# 5. Server status (informational; don't restart)
python projects/latent_systems/tool_build/serve.py --status
# Expected: running on port 7890, OR not running.
```

Report findings as a short list. Don't fix anything yet — surface
anything off (uncommitted work, red tests, schema mismatch) BEFORE
proceeding to the active task.

## Two parallel threads

**Thread A — tool_build (Claude Code's primary work).**
- Phase 1 + Phase 2 code-shipped, Phase 2 acceptance-pending
- Phase 3 prep substrate (8 DRAFT docs + Patterns #7/#8 + 7 NOTES.md
  seed scaffolds) durable
- Phase 3 Wave 1 code BLOCKED until Phase 2 acceptance bridge crosses

**Thread B — H#3 v3 reenactment (Joseph's creative work, NOT Claude
Code's).**
- Active in `shared/h3_reenactment_phase3/` (read-only for Claude Code
  per AD-5)
- Rat anchor LOCKED, rat State 1 LOCKED (per
  `shared/h3_reenactment_phase3/NOTES.md`)
- DO NOT modify any path under `shared/` even if asked — surface to
  Joseph instead

## Working style

- Plain, direct, unpretentious; no rocket-emoji enthusiasm; no
  reflexive validation
- Push back substantively when you have an alternative argument
- Joseph makes final calls; Claude Code advises and executes
- Quantified observations over vibes; forced rankings when listing
  options
- Audit-spec-design loop: read actual artifacts before pressure-
  testing claims
- Cross-Claude review pattern: must-fix vs nice-to-have vs banked-as-
  known-quirk rankings on amendments

---

# Active task

**Last updated 2026-05-13 (second pivot, same-day).** Phase 3
complete-the-app sprint IN PROGRESS — target 2026-05-23 EP1 launch
(pushed +7 days from 2026-05-16).

## ACTIVE: Phase 3 complete-the-app sprint — target 2026-05-23 EP1 launch

Scope locked: full Phase 3 (F5 hero promotion / F6 NOTES.md authorship /
F7 cross-AI capture / F8 OpenMontage serialization / F9 doc-set
coordination) + ROUGH-CUT PLAYER (new feature for EP1 creative judgment
in-app) + WIP multi-page UI finishing + Phase 2.5 fixes including
conftest.py + rubric calibration (Pattern #8 reinforcement #4 —
apparatus accuracy + period authenticity criteria added to Documentary
integrity).

**Day-by-day plan:**

- **Day 1 (2026-05-13):** Phase 2.5 conftest.py + tmp_path-isolated DB
  migration across the 15-test script suite. Single-workstream (code).
  Operational discipline: run the full 15-test suite after every 3-4
  file migration batch to localize isolation regressions — don't
  migrate all 15 then run tests. **Workstream 1B (parallel doc-draft,
  non-blocking):** draft proposed apparatus-accuracy + period-
  authenticity criterion language as scratch file in `tool_build/` for
  Joseph review before integration into `docs/AUDIT_RUBRICS_v1_0.md`
  on Day 2 morning.
- **Day 2:** Rubric calibration morning — integrate apparatus accuracy
  + period authenticity criteria into Documentary integrity criterion
  in `docs/AUDIT_RUBRICS_v1_0.md` (per Day 1 Workstream 1B scratch).
  Must land before F5 so all downstream verdict-derived artifacts
  inherit the sharpened criteria (causal chain: rubric → verdict
  grading → hero state → F6 NOTES.md drafts auto-drafted from verdict
  state via Claude API on Day 3). Per AD-5, Joseph commits the
  `docs/` integration; Claude Code prepares the scratch + diff. Then
  Migration 0004 + F5 hero promotion atomic action + audio asset
  first-class support in state.db (prereq for rough-cut player).
- **Day 3:** F6 NOTES.md authorship via Claude API.
- **Day 4:** Rough-cut player v1 — narration audio playback + sequenced
  asset display + scrub controls. Sequencing metadata: hybrid (auto from
  `EP1_STRUCTURAL_ARCHITECTURE_v1_4.md` + manual overrides). Asset
  timing: narration timing primary + hardcoded defaults fallback. Gap
  handling: honest partial state.
- **Day 5:** Rough-cut player polish — timeline visualization, asset
  highlight, partial-state surfacing, manual sequence override UI.
- **Day 6:** F8 OpenMontage serialization (asset_manifest only per v0.4
  amendment) + WIP multi-page UI finishing.
- **Day 7 (2026-05-19):** F7 cross-AI capture surface (M3 pattern) +
  F9 doc-set coordination.
- **Days 8-10 (2026-05-20 to 2026-05-22):** Buffer + integration
  testing + EP1 final production work using rough-cut player + final
  polish + Phase 2.5 remaining fixes (consult button disable + elapsed
  counter; discipline_drift extension to Migration 0003 tables; YAML
  staleness audit; `PHASE_2_E2E_PLAN.md` cost amendment; Step 8
  verify-end-link amendment).

**Cut-order if novel-work velocity slips:** F7 first, then F9. F8 +
Phase 2.5 conftest + rubric calibration + rough-cut player are
non-negotiable for May 23 ship.

**Velocity assumption:** observed velocity over the past week has been
5-10× prior estimates on substrate-on-substrate work (Phase 2
4-5 weeks → 2 days; Phase 2 e2e cost 12× under estimate; v0.4
amendments hours not days; multi-page UI mostly-finished in one
session). Sprint scope assumes this velocity sustains across
partially-novel work (F7 M3 pattern; F8 schema mapping; rough-cut
player). **Day 5 EOD checkpoint criteria (binary):** F8 asset_manifest
serialization landing on Day 5 = clean. Uncovered schema gap requiring
scope expansion beyond asset_manifest mapping = cut F7 (cross-AI
capture + M3 compressed-input + AI-expansion pattern) immediately and
reallocate Day 7 to F8 completion. F9 (doc-set coordination — "which
canonical docs may need updating when X changes") remains in scope;
it's small and substrate-heavy. Specific schema-gap risks to evaluate
against: `scene_id` mapping (OpenMontage `asset_manifest` requires
`scene_id` on every asset but tool_build has no scenes concept —
closest is `concepts.section`); filename heuristics for
`unknown_image_terminal` status; `additionalProperties: false` strict
mode meaning tool_build-specific metadata can't ride on individual
assets.

## H#3 v3 reenactment PARKED

H#3 v3 reenactment (h3_skinner Skinner box section, parallel
exploratory work) PARKED at locked rat anchor + State 1. v2 SHIPPED
canonical for EP1 launch. Water-in-rat-anchor issue resolved by
parking v3; resume post-2026-05-23 with sharpened rubric (apparatus
accuracy + period authenticity criteria from Day 1 calibration).

Render/verdict/session/consult trail preserved for v3 resume:
render `34db51db61c34c9e`, verdict `46e04a597551c562`, session
`013a9cf917cbd5da`, AI consult `e9969034b45d3e0b`.

## Multi-page UI WIP — `b9935cb` + `a17e36a` (resumes Day 6 of sprint)

WIP commit `b9935cb` (2026-05-13) introduced a journey-oriented multi-page
UI (home shell with sidebar, episode dashboard with chat panel, section
workspace, settings page, video-new stub) backed by `assistant_runner.py`
(Anthropic tool-use loop with system-prompt caching + cost accounting +
vision support) and `assistant_tools.py` (8 tools with AD-5 enforcement).
Audit on 2026-05-13 confirmed the work is **mostly-functional, not scaffold**
— end-to-end-wired home + episode dashboard + chat + section workspace +
`/audit/rank-batch` Claude-vision pre-ranking.

Cleanup commit `a17e36a` fixed three cosmetic bugs the audit surfaced:
iterations counter expression that always returned 1, no-op bare attribute
access in `/audit/rank-batch`, and an over-greedy auto-linker regex in
`episode_dashboard.html` that matched any `/foo`-shaped substring (now
whitelisted to `/audit|video|tools|settings` prefixes).

**Day 6 completion items:**
- `/video/new` wizard (greenfield project creation — currently stub)
- write-to-`.env` for `/settings/keys` (currently read-only)
- Fold `assistant_ranks` table into Migration 0004 (currently
  `CREATE TABLE IF NOT EXISTS`; schema_version stays 0003 despite new table)
- Tests for `assistant_runner`, `assistant_tools`, `/video/*` endpoints,
  `/audit/rank-batch`, `/homepage_stats` — none exist yet

## Decision deferred to post-launch: `_data/` YAML commit cadence

b9935cb bundled ~90 runtime YAMLs (`_data/renders/`, `_data/verdicts/`,
`_data/audit_sessions/`, `_data/ai_consultations/`) alongside the code WIP.
This muddies audit-trail signal. Three options to choose deliberately
post-launch: commit-every-audit-session (audit-trail tax), gitignore them
(breaks AD-5 reproducibility), or middle path. Decide before next
multi-page UI session resumes.

## Earlier completed milestones (audit trail)

- **2026-05-08** Phase 2 acceptance bridge: `c3fbbe2` + `a4a0397` +
  `95b4831` + `a0bc668`. Daily-usability sprint: `a32572f`. Phase 3 v0.4
  amendments: `f7e0604` + `1065d75` + `ae48115` + `2411811` + `120ac7f` +
  `717b385`.
- **2026-05-09** Push resolved (forked to `jahai/OpenMontage`,
  origin/upstream set, 49 commits durable). Hash translation: `1ac0a76`.
  H#3 v3 nycwillow render audited end-to-end. Rubric calibration banked:
  `8d4815f`.
- **2026-05-13 (first decision, same-day)** b9935cb (WIP multi-page UI +
  assistant runner) audited + `a17e36a` cleanup landed. Multi-page UI
  initially parked; H#3 v3 promoted to active priority on 3-day EP1
  launch path.
- **2026-05-13 (second pivot, same-day)** Strategic pivot. EP1 launch
  pushed from 2026-05-16 to 2026-05-23 (+7 days). Phase 3
  complete-the-app sprint scoped (F5-F9 + rough-cut player + multi-page
  UI finishing + Phase 2.5 + rubric calibration). H#3 v3 re-parked at
  locked rat anchor; v2 SHIPPED carries EP1. Multi-page UI work resumes
  Day 6 as part of sprint. Rationale: observed velocity 5-10× prior
  estimates over the past week sustains the expanded scope with
  variance buffer; rough-cut player added for EP1 creative judgment
  in-app; rubric calibration ships before EP1 to catch
  apparatus-accuracy issues going forward.

## Post-reboot startup checklist

If Claude conversation didn't resume cleanly:

1. Open Claude Code in `OpenMontage/projects/latent_systems/tool_build`
2. Try `claude --resume` first; if fails, fresh session is fine
3. Restart server: `python serve.py` (in `tool_build/` dir). If `--status`
   reports stale PID from pre-reboot, run `python serve.py --stop` first
   to clear, then `python serve.py`
4. Reload browser at `http://localhost:7890/audit/grid`
5. Reference this SESSION_STARTER.md + `banked_items.md` "Updated:"
   index line for current state

---

# Maintenance

- Update "Active task" section at start/end of every meaningful work
  block. When this task closes, replace with the next active task; the
  skeleton above stays stable.
- Don't update Read paths or AD-5 reminder unless project structure
  shifts (rare — quarterly at most).
- This doc lives at `projects/latent_systems/tool_build/SESSION_STARTER.md`.
- Commit changes when project shape shifts (new phase, new threads, new
  banked-items categories).
