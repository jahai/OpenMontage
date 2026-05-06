# LATENT SYSTEMS — Tool-build Phase 1 Design Notes

**Date:** 2026-05-04
**Status:** v0.4 — §1 / 3a.4 timeout deviation amendment per Days 11-15 cross-Claude review (verified against retry_queue.compute_backoff + dispatcher exhaustion path on Day 17)
**Source material:** v1 Spec Proposal v0.5 at `tool_build/v1_spec_proposal.md`
**Purpose:** Detailed design specifications that must be settled before Phase 1 code begins.

---

## Document scope

The v1 spec proposal commits to architectural decisions and feature surfaces. It does not specify: failure-mode behavior, schema-level details, seed content, lifecycle operations, coexistence verification, backup/recovery paths.

This doc fills those gaps for Phase 1 specifically. Phase 2-3 design notes will be written when those phases are imminent. This is not a complete v1 design doc — it is the minimum design substrate Phase 1 build needs.

If a question in this doc is deferred ("v1 won't decide this; Phase 2 will"), that's an explicit punt with rationale. If a question seems missing entirely, flag it for v0.4 of this doc.

---

## 1. Failure-mode specifications for Feature 3a (API generation) and 3b (clipboard handoff)

[Unchanged from v0.2. See git history if needed; section content carries forward intact.]

The v1 spec named failure modes at a high level. This section specifies Phase 1 behavior for each.

### Feature 3a — API generation failure modes

**3a.1 Rate limit (HTTP 429 from Anthropic / OpenAI / ElevenLabs).**

Behavior:
- App receives 429 with optional `retry-after` header.
- Update prompt status to `failed`, with `failure_reason: "rate_limited; retry_after=Ns"`.
- Queue prompt in retry queue with backoff (start at retry_after if provided, else 60s; double on subsequent 429s up to a 600s cap).
- UI shows status badge "Rate limited — retrying in Ns" with explicit "cancel retry" action.
- After 3 consecutive 429s on same prompt, stop auto-retry; surface "rate-limited persistently — manual retry available."

Retry queue persistence: queue lives in `tool_build/_data/_retry_queue.yaml`. Survives app restart. On startup, app resumes pending retries.

**3a.2 Auth error (HTTP 401/403).** Update prompt status to `failed`. Surface blocking modal "API auth failed for <provider>. Check credentials in `.env`." Do not retry. Surface link to credential-setup docs.

**3a.3 Hallucinated syntax.** Phase 1 does NOT pre-validate output syntax. Detection happens downstream at audit phase. v2 may add post-generation syntax validators.

**3a.4 Timeout.** Anthropic 120s, OpenAI 180s, ElevenLabs 60s short / 300s long. Mark prompt status `awaiting_retry` and enqueue a single auto-retry after 60s. If the retry also times out, set status to `failed` and surface the manual "retry" action in the UI. Rationale: a single timeout is most often a transient network blip; a single auto-retry preserves user attention for the genuinely stuck case. Cost ceiling: one extra failed call. (v0.4 amendment per Days 11-15 review; supersedes v0.3 "no auto-retry" rule.)

**3a.5 Network failure.** Single auto-retry after 30s. If second attempt fails, stop. UI offers "retry."

**3a.6 Malformed response.** No auto-retry. UI offers "retry."

**3a.7 Partial completion (streaming disconnect).** Mark prompt status `partial`. Save partial output. UI offers "Retry to complete" or "Use partial as-is."

### Feature 3b — Clipboard handoff failure modes (silent failures)

**3b.1 User never opened tool tab.** Timer-based: 30min "still waiting" status; 24h "was this generated?" with three actions.
**3b.2 File didn't land in `~/Downloads/`.** Same as 3b.1.
**3b.3 User pasted into wrong tool.** Detect via tool-mismatch on render; offer "bind anyway" / "rebind" / "mark as orphan."
**3b.4 User cancelled in tool UI.** Same as 3b.1.
**3b.5 Unknown filename pattern.** Router routes to `_inbox/`. UI surfaces "review."
**3b.6 Multiple uncaptured prompts.** Picker on render arrival; default = most recent.
**3b.7 User renamed file before routing.** Filesystem watcher hashes files at first detection; hash-stable identity persists across rename.
**3b.8 Multiple sequential generations from same prompt.** `generation_attempts` table — each clipboard-copy creates new attempt.

### General principle for both 3a and 3b

**Failures are visible, not hidden.** Every failure produces a `failure_reason` field. UI surfaces failed prompts in a "needs attention" view.

[Detailed v0.2 content for each sub-mode preserved in git history; condensed here for v0.3 readability.]

---

## 2. State.db schema for cache layer

Per AD-5: state.db is cache, not source of truth.

### Tables (Phase 1)

```sql
-- Concepts
CREATE TABLE concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ep TEXT,
    section TEXT,
    subject TEXT,
    register TEXT,
    status TEXT NOT NULL,
    discipline_version TEXT NOT NULL,
    yaml_path TEXT NOT NULL,
    created TEXT NOT NULL,
    modified TEXT NOT NULL
);
CREATE INDEX idx_concepts_status ON concepts(status);
CREATE INDEX idx_concepts_ep ON concepts(ep);
CREATE INDEX idx_concepts_section ON concepts(section);
CREATE INDEX idx_concepts_discipline_version ON concepts(discipline_version);

-- Prompts
CREATE TABLE prompts (
    id TEXT PRIMARY KEY,
    concept_id TEXT,
    tool TEXT NOT NULL,
    text_preview TEXT,
    status TEXT NOT NULL,
    failure_reason TEXT,
    drafted_by TEXT,
    discipline_version TEXT NOT NULL,
    yaml_path TEXT NOT NULL,
    created TEXT NOT NULL,
    FOREIGN KEY(concept_id) REFERENCES concepts(id)
);
CREATE INDEX idx_prompts_concept_id ON prompts(concept_id);
CREATE INDEX idx_prompts_tool ON prompts(tool);
CREATE INDEX idx_prompts_status ON prompts(status);

-- Generation attempts (handles 3b.8 sequential re-rolls)
CREATE TABLE generation_attempts (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    started TEXT NOT NULL,
    completed TEXT,
    status TEXT NOT NULL,
    trigger_method TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY(prompt_id) REFERENCES prompts(id)
);
CREATE INDEX idx_attempts_prompt_id ON generation_attempts(prompt_id);
CREATE INDEX idx_attempts_status ON generation_attempts(status);
CREATE UNIQUE INDEX idx_attempts_unique_per_prompt ON generation_attempts(prompt_id, attempt_number);

-- Renders (links to attempt, not directly to prompt)
CREATE TABLE renders (
    id TEXT PRIMARY KEY,
    attempt_id TEXT,
    prompt_id TEXT,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    download_hash TEXT,
    canonical_hash TEXT NOT NULL,
    tool TEXT NOT NULL,
    variant INTEGER,
    hero_status TEXT,
    discipline_version TEXT NOT NULL,
    yaml_path TEXT,
    created TEXT NOT NULL,
    FOREIGN KEY(attempt_id) REFERENCES generation_attempts(id),
    FOREIGN KEY(prompt_id) REFERENCES prompts(id)
);
CREATE INDEX idx_renders_attempt_id ON renders(attempt_id);
CREATE INDEX idx_renders_prompt_id ON renders(prompt_id);
CREATE INDEX idx_renders_canonical_hash ON renders(canonical_hash);
CREATE INDEX idx_renders_download_hash ON renders(download_hash);
CREATE INDEX idx_renders_hero_status ON renders(hero_status);
CREATE INDEX idx_renders_filepath ON renders(filepath);

-- Audit verdicts
CREATE TABLE verdicts (
    id TEXT PRIMARY KEY,
    render_id TEXT NOT NULL,
    rubric_used TEXT,
    verdict TEXT NOT NULL,
    audited_by TEXT,
    discipline_version TEXT NOT NULL,
    yaml_path TEXT NOT NULL,
    created TEXT NOT NULL,
    FOREIGN KEY(render_id) REFERENCES renders(id)
);
CREATE INDEX idx_verdicts_render_id ON verdicts(render_id);
CREATE INDEX idx_verdicts_verdict ON verdicts(verdict);

-- Hero promotions
CREATE TABLE hero_promotions (
    id TEXT PRIMARY KEY,
    render_id TEXT NOT NULL,
    hero_filepath TEXT NOT NULL,
    reversed_at TEXT,
    reversed_reason TEXT,
    discipline_version TEXT NOT NULL,
    yaml_path TEXT NOT NULL,
    created TEXT NOT NULL,
    FOREIGN KEY(render_id) REFERENCES renders(id)
);
CREATE INDEX idx_hero_promotions_render_id ON hero_promotions(render_id);

-- Lineage edges (with temporal dimension per cross-Claude review)
CREATE TABLE lineage_edges (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    layer INTEGER NOT NULL,
    valid_from_version TEXT NOT NULL,
    valid_to_version TEXT,
    stale_reason TEXT,
    created TEXT NOT NULL
);
CREATE INDEX idx_lineage_source ON lineage_edges(source_type, source_id);
CREATE INDEX idx_lineage_target ON lineage_edges(target_type, target_id);
CREATE INDEX idx_lineage_layer ON lineage_edges(layer);
CREATE INDEX idx_lineage_validity ON lineage_edges(valid_from_version, valid_to_version);

-- API call tracking (cost tracking from day one)
CREATE TABLE api_calls (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    purpose TEXT NOT NULL,
    prompt_id TEXT,
    started TEXT NOT NULL,
    completed TEXT,
    status TEXT NOT NULL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd_estimate REAL,
    error TEXT,
    FOREIGN KEY(prompt_id) REFERENCES prompts(id)
);
CREATE INDEX idx_api_calls_provider ON api_calls(provider);
CREATE INDEX idx_api_calls_purpose ON api_calls(purpose);
CREATE INDEX idx_api_calls_started ON api_calls(started);
CREATE INDEX idx_api_calls_prompt_id ON api_calls(prompt_id);

-- Cross-AI captures (Phase 3 feature; table exists in Phase 1 for forward-compat)
CREATE TABLE cross_ai_captures (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    discipline_version TEXT NOT NULL,
    yaml_path TEXT NOT NULL,
    captured TEXT NOT NULL
);
CREATE INDEX idx_cross_ai_captures_source ON cross_ai_captures(source);

-- Tool-grammar configs
CREATE TABLE tool_grammar_configs (
    tool TEXT PRIMARY KEY,
    discipline_version TEXT NOT NULL,
    yaml_path TEXT NOT NULL,
    last_updated TEXT NOT NULL
);

-- App-level metadata
CREATE TABLE app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated TEXT NOT NULL
);
```

### Schema migrations: Alembic in Phase 1

Migration files at `tool_build/migrations/<timestamp>_<description>.py`. App refuses to start if `app_meta.schema_version` mismatch detected without `--migrate-schema` flag.

### Regen-from-filesystem path

If state.db corrupts: move to `state.db.corrupted_<timestamp>`, walk YAMLs, walk canonical structure for pre_v1 markers, populate lineage_edges, repopulate api_calls from `_api_calls.log`, log to `_regen_log.txt`.

Invokable: automatic on startup if missing/corrupted; manual via UI; manual via `python tool_build/serve.py --rebuild-cache`.

Estimated regen time: <30s for current project size.

### What state.db does NOT do

Cache holds queryable metadata. Full content lives in source-of-truth YAML files. Does NOT store: prompt text, reasoning notes, full audit-rubric scores, tool-grammar config content.

---

## 3. Tool-grammar config — MJ seed content

[Unchanged from v0.2. Full seed content carries forward.]

### File: `tool_build/_data/tool_grammar_configs/mj.yaml`

```yaml
tool: mj
version: v7
discipline_version: 1.0

syntax_rules:
  - name: aspect_ratio
    pattern: "--ar 16:9"
    when: "all renders unless square or vertical needed"
    rationale: "channel format is 16:9; deviations are exceptions"
  - name: version_flag
    pattern: "--v 7"
    when: "always (current MJ version)"
    rationale: "v7 is current; older versions produce different aesthetic"
  - name: lens_specification
    pattern: "shot on <lens>mm <camera_type>"
    when: "cinematic register required"
    examples:
      - "shot on 35mm anamorphic"
      - "shot on 85mm prime"
    rationale: "lens vocabulary calibrates depth/feel"

vocabulary_priors:
  - phrase: "1940s archival B&W"
    register: "schematic apparatus / lab"
    confidence: high
  - phrase: "behavioral research observation"
    register: "schematic apparatus"
    confidence: high
  - phrase: "fluorescent overhead lighting"
    register: "clinical / institutional"
    confidence: medium
  - phrase: "desk lamp practical light"
    register: "intimate / focused"
    confidence: high
  - phrase: "subject in foreground, apparatus in background bokeh"
    register: "subject-imagery"
    confidence: high
  - phrase: "split-focus composition"
    register: "dual-subject foreground/midground separation"
    confidence: high
    note: "proven in 8 craft-test renders"
  - phrase: "echo-anchor"
    register: "presence-by-absence (e.g., empty recliner with implied subject)"
    confidence: high
    note: "produces subject presence through environmental traces"

failure_modes:
  - mode: "white-coat collapse"
    trigger: "explicit researcher mention"
    mitigation: "describe apparatus-as-architecture instead"
    severity: high
  - mode: "register-relativity break"
    trigger: "mixing modern + period vocabulary in same prompt"
    mitigation: "commit to single era"
    severity: high
  - mode: "thesis-image overload"
    trigger: "too many concept elements stacked in one render"
    mitigation: "one concept per render; spread for layered ideas"
    severity: medium
  - mode: "movie-trailer drift"
    trigger: "performative-ominous language ('haunting', 'mysterious', 'shocking')"
    mitigation: "calm-observational register"
    severity: high
  - mode: "MJ schematic-precision weakness"
    trigger: "expecting MJ to render precise diagrammatic content"
    mitigation: "route schematic-precise content to GPT Image 2"
    severity: medium
  - mode: "novel-concept resistance"
    trigger: "subject combinations unusual enough that MJ training data lacks direct precedent"
    mitigation: |
      Two-part: (1) explicit negation of nearest-stock-image MJ defaults; 
      (2) redundant compositional anchoring — specify foreground/midground/background plane assignments redundantly to force structural attention.
    severity: high

successful_examples:
  - prompt_id: "<populated_after_phase_1_seed_run>"
    note: "D4 P3 archival lab — held register at 100%, exemplary craft"

drafting_notes: |
  When drafting MJ prompts:
  - Lead with subject, then setting, then register.
  - Apply syntax rules unconditionally unless prompt specifies override.
  - Check vocabulary priors first.
  - Run failure-mode check.
  - For novel composite subjects, apply novel-concept-resistance mitigation aggressively.
  
  Prompt length sensitivity:
  - Target 50-80 words for atmospheric photographic register.
  - High-density apparatus renders can extend to 90 words.
  - Above 100 words MJ visibly degrades on register coherence.
  - Below 30 words MJ defaults to its native aesthetic (often unwanted).
```

### Phase 1 expansion plan

Phase 1 ships MJ only. GPT Image 2, Kling, ElevenLabs in Phase 2 once Phase 1 usage informs them.

---

## 4. Coexistence verification + build-time write protection

Per AD-5: existing canonical files are read-only to v1 by default. This section enumerates what Phase 1 reads, confirms no writes touch canonical paths, and specifies build-time write protection.

### Phase 1 reads from canonical structure

| Path | Why | Modify? |
|------|-----|---------|
| `projects/latent_systems/tools/router_log.md` | Populate `renders` table on routing events | NO |
| `projects/latent_systems/tools/router_config.yaml` | Read confidence-tier rules and direction heuristics | NO |
| `projects/latent_systems/shared/<direction>/run_<date>/*.png` | Enumerate existing renders for `pre_v1` markers | NO |
| `projects/latent_systems/shared/<direction>/winners/*.png` | Enumerate existing hero renders for `pre_v1` markers | NO |
| `projects/latent_systems/ep1/<section>/*.png`, `*.mp4`, `*.mp3` | Enumerate existing section assets for `pre_v1` markers | NO |
| `projects/latent_systems/ep1/<section>/NOTES.md` | Enumerate NOTES.md state | NO |
| `projects/latent_systems/docs/CHANNEL_STRUCTURAL_ARCHITECTURE_v*.md` | Enumerate channel staples for reference resolution | NO |
| `projects/latent_systems/docs/EP1_STRUCTURAL_ARCHITECTURE_v*.md` | Enumerate section structure | NO |
| `projects/latent_systems/docs/LATENT_SYSTEMS_PROJECT_BRIEFING_v*.md` | Read project context for Claude API calls | NO |
| `projects/latent_systems/docs/AUDIT_RUBRICS_v*.md` (Phase 2 dependency) | Read audit rubrics — Phase 1 punts | N/A |

### Phase 1 writes

| Path | Why |
|------|-----|
| `projects/latent_systems/tool_build/_data/state.db` | Cache layer per AD-5 |
| `projects/latent_systems/tool_build/_data/concepts/*.yaml` | Concept artifacts |
| `projects/latent_systems/tool_build/_data/prompts/*.yaml` | Prompt artifacts |
| `projects/latent_systems/tool_build/_data/renders/*.yaml` | Render artifacts (post-v1 only) |
| `projects/latent_systems/tool_build/_data/tool_grammar_configs/*.yaml` | Tool-grammar configs |
| `projects/latent_systems/tool_build/_data/_retry_queue.yaml` | API retry queue persistence |
| `projects/latent_systems/tool_build/_data/_regen_log.txt` | State.db rebuild log |
| `projects/latent_systems/tool_build/_data/_app_log.txt` | App operational log |
| `projects/latent_systems/tool_build/_data/_api_calls.log` | API call audit log |
| `<canonical_render>.toolbuild.yaml` | Sidecar on new post-v1 renders only |

### Verification: no Phase 1 write path touches canonical files

The list above is exhaustive for Phase 1. No path under `projects/latent_systems/{shared,ep1,docs,tools}/` is in the write list.

**The only runtime exception** (per AD-5): user-invoked migration actions modify canonical files with backup written first. Phase 1 does NOT include any migration actions — Phase 3 territory at earliest.

**Enforcement-infrastructure exception** (per AD-5 v0.5 carve-out): pre-commit hook installation at `OpenMontage/.git/hooks/pre-commit`. This is install-time, not runtime, and serves AD-5 enforcement rather than violating it. See "Pre-commit hook installation" below.

### Coexistence smoke test

CI-style check that verifies the coexistence promise:

1. Capture pre-test snapshot: `git status --porcelain projects/latent_systems/{shared,ep1,docs,tools}/` should be empty (or equal baseline).
2. Run a Phase 1 user-flow (create concept, draft prompt, clipboard handoff, simulate render return).
3. Capture post-test snapshot.
4. Result must equal baseline (or show only legitimate router routing into `shared/<...>/run_<date>/` from existing router behavior).

If post-test snapshot shows v1-attributable changes to canonical files, that's a regression. Phase 1 build must include this as a CI-style check.

### Pre-commit hook installation (specified per AD-5 v0.5 carve-out + parallel-Claude review)

**Where the hook lives:** `OpenMontage/.git/hooks/pre-commit`. Git lives at the OpenMontage parent level, not at `projects/latent_systems/`.

**What the hook does:**
- Reads the staged diff via `git diff --cached --name-only`.
- For each changed path, checks if it matches any of:
  - `projects/latent_systems/shared/**`
  - `projects/latent_systems/ep1/**`
  - `projects/latent_systems/docs/**`
  - `projects/latent_systems/tools/**`
- If any match: examines `git config user.name` and `git config user.email`.
  - If author is Joseph (`@jahai` / `joseph.brightly@gmail.com`): allow.
  - If author is anyone else (Claude Code commits, automated agents, etc.): block with explanatory message.
- If no canonical-path matches: pass through.
- Also checks paths OUTSIDE `projects/latent_systems/` (OpenMontage's own work like `remotion-composer/`, `pipeline_defs/`, etc.): pass through unconditionally. The hook is scoped narrowly to Latent Systems canonical paths only.

**Existing-hook chaining (per parallel-Claude review):**

OpenMontage may already have a pre-commit hook (lint, format, tests). v1's install must:
1. Detect existing hook at `OpenMontage/.git/hooks/pre-commit`.
2. If found: rename to `pre-commit.backup_<ISO_timestamp>` and prompt user before continuing.
3. Install new hook that:
   - First calls the backup hook (if it exists). If backup hook fails (non-zero exit), abort commit.
   - Then runs AD-5 enforcement check.
   - Both must pass for commit to succeed.

This preserves OpenMontage's existing discipline. v1's hook is additive enforcement, not replacement.

**Hook script (Phase 1 starter — refined during Week 1 build):**

```bash
#!/usr/bin/env bash
# Pre-commit hook installed by latent_systems tool_build v1
# Purpose: enforce AD-5 (canonical paths read-only to non-Joseph commits)
# Scope: projects/latent_systems/{shared,ep1,docs,tools}/ only

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$REPO_ROOT/.git/hooks"
BACKUP_HOOK="$(ls -t "$HOOK_DIR"/pre-commit.backup_* 2>/dev/null | head -1 || true)"

# Step 1: chain to backup hook if one exists
if [ -n "$BACKUP_HOOK" ] && [ -x "$BACKUP_HOOK" ]; then
    "$BACKUP_HOOK" || exit $?
fi

# Step 2: AD-5 enforcement
JOSEPH_NAME="@jahai"
JOSEPH_EMAIL="joseph.brightly@gmail.com"
CURRENT_NAME="$(git config user.name)"
CURRENT_EMAIL="$(git config user.email)"

CANONICAL_PATTERNS='^projects/latent_systems/(shared|ep1|docs|tools)/'

CHANGED=$(git diff --cached --name-only | grep -E "$CANONICAL_PATTERNS" || true)

if [ -n "$CHANGED" ]; then
    if [ "$CURRENT_NAME" = "$JOSEPH_NAME" ] || [ "$CURRENT_EMAIL" = "$JOSEPH_EMAIL" ]; then
        # Joseph's commit — allow
        exit 0
    else
        echo "ERROR: AD-5 violation detected." >&2
        echo "Build process must not modify Latent Systems canonical paths." >&2
        echo "Current commit author: $CURRENT_NAME <$CURRENT_EMAIL>" >&2
        echo "Affected paths:" >&2
        echo "$CHANGED" | sed 's/^/  /' >&2
        echo "" >&2
        echo "Move changes to projects/latent_systems/tool_build/, OR" >&2
        echo "have Joseph commit canonical changes separately." >&2
        echo "" >&2
        echo "Override (only if you understand the risk): git commit --no-verify" >&2
        exit 1
    fi
fi

exit 0
```

This script runs against the OpenMontage repo. It blocks non-Joseph commits that touch Latent Systems canonical paths, while leaving OpenMontage's own paths (`remotion-composer/`, `pipeline_defs/`, etc.) unaffected.

---

## 5. Backup story confirmation

[Unchanged from v0.2.]

Source-of-truth YAML files: backed up via git (same as `docs/` discipline).
State.db: regenerable cache, not backed up.
Operational files: not backed up (logs, retry queue, regen log).

`.gitignore` patterns to add for `projects/latent_systems/tool_build/_data/`:
```
state.db
state.db.corrupted_*
_retry_queue.yaml
_app_log.txt*
_api_calls.log*
_regen_log.txt
_server.pid
```

Everything else under `tool_build/_data/` is git-tracked.

Recovery scenarios (state.db corrupted, single YAML deleted, entire `_data/` deleted) detailed in v0.2 — carry forward unchanged.

---

## 6. Operational lifecycle (sharpened per parallel-Claude review)

### Install (with hook installation per AD-5 v0.5 carve-out)

```bash
cd C:/Users/josep/Desktop/desktop1/OpenMontage/projects/latent_systems
pip install -r tool_build/requirements.txt
python tool_build/serve.py --init
```

What `--init` does:
1. Creates `tool_build/_data/` directory structure.
2. Creates `tool_build/_data/state.db` with initial schema (Alembic migration `0001_initial`).
3. Runs initial filesystem walk to populate `pre_v1` markers for existing canonical material.
4. Loads MJ tool-grammar seed config.
5. **Prompts for git pre-commit hook installation:**
   ```
   Install git pre-commit hook at OpenMontage/.git/hooks/pre-commit?
   This hook enforces AD-5 (canonical paths read-only to non-Joseph commits).
   
   Detected existing hook: <path or "none">
   If installing: existing hook will be backed up to pre-commit.backup_<timestamp> 
                  and chained (called first by new hook).
   
   Install? [y/N]
   ```
6. If user accepts: backs up existing hook (if any), installs new hook, marks executable.
7. If user declines: proceeds without hook. Logs decision to `_app_log.txt`. Build-time write protection reduced; runtime smoke test still operative.
8. Prints summary: "Init complete. Server not yet running. Start with: pythonw tool_build/serve.py"

User confirmation is the right discipline — Joseph explicitly opts in. Hook install is reversible (see uninstall).

Requirements pinned in `tool_build/requirements.txt`. Phase 1 dependencies (estimate): FastAPI, SQLAlchemy + Alembic, PyYAML, anthropic SDK, openai SDK, watchdog, Pillow.

### Start (default mode: backgrounded)

Joseph's working pattern shows no ongoing terminal-management discipline. Existing router runs as needed without persistent terminal commitment. v1 matches this.

**Default Phase 1 start command (backgrounded, no console window):**
```bash
pythonw tool_build/serve.py
```

`pythonw` (Python for Windows, no console) starts the server detached from terminal. Server runs silently in background. Joseph opens browser to `http://localhost:7890`.

**Foreground / debug mode (explicit opt-in):**
```bash
python tool_build/serve.py --debug
```

Default port: 7890.

### Discovering whether the server is running

```bash
python tool_build/serve.py --status
```
Prints "running on port X (PID Y)" or "not running."

App writes PID file at `tool_build/_data/_server.pid` on startup; removes on graceful shutdown.

### Stop

```bash
python tool_build/serve.py --stop
```
Reads PID file, sends SIGTERM (Windows equivalent), waits for graceful shutdown.

Foreground mode: `Ctrl+C`.

Either path: graceful shutdown finishes in-flight API calls, flushes state.db cache, persists retry queue, removes PID file, exits.

### Update

```bash
python tool_build/serve.py --stop
git pull
pip install -r tool_build/requirements.txt --upgrade
python tool_build/serve.py --migrate-schema  # applies any pending Alembic migrations
pythonw tool_build/serve.py
```

App refuses to start if Alembic detects pending migrations without `--migrate-schema` flag.

### Uninstall (NEW per parallel-Claude review)

```bash
python tool_build/serve.py --uninstall
```

What `--uninstall` does:
1. Stops the server if running (sends SIGTERM via PID file).
2. **Removes pre-commit hook:**
   - Detects v1's hook at `OpenMontage/.git/hooks/pre-commit`.
   - If a backup exists (`pre-commit.backup_<timestamp>`): restores most recent backup, deletes v1's hook.
   - If no backup exists: deletes v1's hook (leaves no pre-commit hook installed — restores the pre-v1 baseline).
3. **Preserves data (move-not-delete):**
   - Moves `tool_build/_data/` to `tool_build/_data.uninstalled_<ISO_timestamp>/`.
   - This way reinstall via `--init` can recover by moving `_data.uninstalled_<>` back to `_data/`.
4. Prints confirmation: "Uninstall complete. Hook removed (backup restored: <yes/no>). Data preserved at <path>."

Uninstall is reversible. Reinstall reads from preserved data if user wants to restore state, or starts fresh if user wants clean state.

The hook removal is the only canonical-adjacent action; it must be reversible. Data move-not-delete preserves all post-v1 work.

### Logs and error reporting

App log at `tool_build/_data/_app_log.txt` (rotates at 10MB, up to 5 archives).
API call log at `tool_build/_data/_api_calls.log` (per-call records, used by `api_calls` table).

Logged: startup/shutdown, schema migrations, filesystem walk events, failures with `failure_reason`, external-edit detection events, hook install/uninstall events.
NOT logged: successful API calls (in `_api_calls.log`), UI interactions, successful artifact reads.

Verbose logging via `--debug` flag.

### Health check

UI surfaces a "system status" indicator: green/yellow/red. Hover surfaces details.

---

## 7. Multi-Claude state coordination — design constraints

[Unchanged from v0.2.]

### Constraint 1: state.db writes are immediate-flush

SQLite connection: `synchronous=FULL` and `journal_mode=WAL`. WAL mode allows external readers to see committed state without blocking writers. Marginal performance cost for v1's write volume.

### Constraint 2: app detects external YAML edits and refreshes affected cache rows

`watchdog` watches `tool_build/_data/<artifact_type>/*.yaml`. On detected change: app reads YAML, updates corresponding state.db row, logs external-edit event. Stale-cache window <1 second.

### What still gets punted

Multi-Claude orchestration (routing questions to instances) remains user-managed per F11b option 2.

---

## 8. Phase 1 build sequence (revised per cross-Claude review + AD-5 v0.5 carve-out)

### Risk-aware revised sequence

**Week 1: foundation + coexistence safety.**
- **Day 1: pre-commit hook install** (per Section 4 + AD-5 carve-out). First thing built before any code that could write to disk. Includes existing-hook backup + chaining logic.
- **Day 1-2: coexistence smoke test** (CI-style check per Section 4).
- Install/start/stop scaffolding (with backgrounded `pythonw` default per Section 6, plus uninstall per Section 6).
- State.db schema + initial Alembic migration (per Section 2).
- Filesystem walker (populates pre_v1 markers).
- YAML serialization for concept/prompt/render artifacts.

**Week 2: clipboard handoff + filesystem watching.**
- Filesystem watcher on `~/Downloads/` with hash-tracking primitive (per 3b.7).
- Existing router integration.
- Clipboard handoff for MJ (Feature 3b).
- 3b.1-3b.8 failure mode handling.
- Generation-attempt logic.
- Binding logic (render → most-recent-open-attempt → prompt).

**Week 3: API integration + prompt drafting.**
- Anthropic SDK integration with retry queue.
- 3a.1-3a.7 failure mode handling.
- Prompt drafting flow (Feature 2) with tool-grammar config loading.
- MJ tool-grammar config seed.
- API call instrumentation (`api_calls` table populated).

**Week 4: frontend + discipline-drift query + Phase 1 acceptance.**
- Frontend skeleton (HTMX + minimal CSS).
- Concept browser UI (Feature 1).
- Discipline-drift query surface (Feature 9).
- Status badges in main UI.
- Cost tracking dashboard.
- Multi-Claude state coordination constraints applied.
- Phase 1 acceptance test against success criteria 1, 2, 4.

### Realistic estimate

**Phase 1: 3-6 weeks.** The 4-week sequence is the "everything goes well" path. Allow buffer for: schema refinements during use, frontend UI iterations, failure-mode behavior tuning, multi-Claude coordination edge cases, hook install edge cases (existing hooks Joseph forgot about, etc.).

Total Phase 1-3: 8-12 weeks.

---

## 9. Open questions for Phase 1 build

Phase 1 design notes punt the following to be answered during build:

1. **Web framework choice (FastAPI vs Flask).** Default: **FastAPI** for async + Alembic integration.
2. **Frontend framework (vanilla JS vs HTMX vs Alpine.js).** Default: **HTMX**.
3. **Image viewer implementation for Feature 4.** Phase 2 builds; Phase 1 ensures data model supports <100ms queries.

**Note:** schema migration tooling is **un-punted** — Alembic in Phase 1 (per Section 2). Multi-Claude state coordination is **partially un-punted** — implementation punted, design constraints banked (per Section 7). Pre-commit hook details are **un-punted** — full spec including chaining and uninstall (per Section 4 + Section 6).

---

## Document maintenance

- **v0.1 (2026-05-04):** initial draft. Six sections specifying Phase 1 build prerequisites: failure modes (3a/3b), state.db schema, MJ tool-grammar seed, coexistence verification, backup story, operational lifecycle. Open questions deliberately punted to build itself. Phase 1 build sequence recommended.
- **v0.2 (2026-05-04):** cross-Claude review pass. Added 3a.7, 3b.7, 3b.8 failure modes. Added `generation_attempts` and `api_calls` tables. Added temporal dimension to `lineage_edges`. Un-punted schema migrations to Alembic. Added three MJ tool-grammar additions. Added build-time write protection (pre-commit hook). Sharpened operational lifecycle to default-backgrounded `pythonw`. Added Section 7 multi-Claude state coordination constraints. Reordered Phase 1 build sequence (coexistence first, clipboard before API). Adjusted Phase 1 estimate to 3-6 weeks.
- **v0.3 (2026-05-04):** parallel-Claude review of pre-commit hook scope (git lives at OpenMontage parent level). Section 4 expanded with pre-commit hook installation detail (paths, scoping, existing-hook chaining via backup, full bash script starter). Section 6 expanded with `--init` hook install procedure (user confirmation prompt, existing-hook handling) and new `--uninstall` procedure (hook removal with backup restore, data preservation via move-not-delete). Phase 1 build sequence (Section 8) updates Day 1 to include hook install with chaining. v0.1/v0.2 sections 1, 3, 5, 7 condensed (full content in git history) for v0.3 readability. Pointer to v1 Spec v0.5.
- **v0.4 (2026-05-06):** Day 16 cleanup fold-in. §1 / 3a.4 timeout amended to allow a single 60s auto-retry before marking failed — rationale: transient-network-blip case dominates; one free retry costs at most one extra failed call and preserves manual-retry path verbatim. Captured as a build-time deviation from v0.3 spec text per Days 11-15 cross-Claude review; staging draft was at `_data/_inbox_review/_design_notes_pending_v0.4.md` §"Section to amend: §1 / 3a.4 Timeout". `dispatcher.py` and `retry_queue.py` 3a.4 inline references should be updated to point at v0.4 in a future commit.
