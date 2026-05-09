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

# 4. Test baseline
pytest projects/latent_systems/tool_build/tests/ -x --no-header -q | tail -20
# Expected: 16 suites green at Phase 2 close.

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

**EOD checkpoint — 2026-05-08:**

Phase 2 acceptance bridge COMPLETE 2026-05-08 (4 commits + 5 findings
banked: `c3fbbe2`, `a4a0397`, `95b4831`, `a0bc668` + e2e debrief
edits).

Daily-usability sprint COMPLETE 2026-05-08 (`a32572f` — web-UI
ingestion + JS interaction fixes + hover tooltips + consult button
full-width fix).

Phase 3 v0.4 amendments fully landed 2026-05-08 (6 commits: `f7e0604`
+ `1065d75` + `ae48115` + `2411811` + `120ac7f` + `717b385`). All F5
[OPEN] questions resolved including file copy vs move (decision:
copy). Phase 3 Wave 1 Day 4-5 implementation has zero remaining design
ambiguity.

Branch 44 ahead of `origin/main`; push-architecture (calesthio org owns
repo, jahai needs different remote) unresolved — local commits durable.

## Next session options (Joseph picks)

**(A) Phase 3 Wave 1 Day 1** — Migration 0004 schema implementation +
F8 schema-read against actual OpenMontage schemas. Wave 1 Day 4-5
unblocked by tonight's v0.4 amendments. ~2-3 hours.

**(B) Push-architecture resolution** — fork-to-jahai or similar, get
44 commits durable on GitHub. ~30 min UI + 1 git command.

**(C) H#3 v3 reenactment production work** — rat anchor + State 1
upscales + canonical filename saves, then human anchor MJ generation.
EP1-launch May 16 (8 days). Drafted human anchor prompt available in
chat history if needed. ~2-3 hours.

**(D) Phase 2.5 fixes** (5 banked findings from Wave B real run):
consult button disable + elapsed counter; discipline_drift extension
to Migration 0003 tables; YAML staleness audit; PHASE_2_E2E_PLAN.md
cost amendment paper-work; Step 8 verify-end-link amendment.
~2-3 hours.

**Recommended: A or C** depending on energy + EP1-launch timeline
pressure.

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
