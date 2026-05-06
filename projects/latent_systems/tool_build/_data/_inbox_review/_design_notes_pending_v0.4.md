# Pending additions for design notes v0.4

Items surfaced during build that should land in the next spec revision.
Lives outside the spec docs (which are canonical authored material) so
build-Claude doesn't accidentally edit those. Joseph reviews + folds in.

**Drafted:** 2026-05-04 (after Days 1-9 build + 3 review waves)
**Updated:** 2026-05-05 (Day 16 cleanup — added §3a.4 timeout deviation)

---

## Section to add: "v1 git tracking posture" (resolves §2 gap)

**Recommendation:** Update spec §5 backup story.

Current state: `projects/` is gitignored at OpenMontage repo level. Day 5-9 §2-A introduced carve-outs in `OpenMontage/.gitignore` that track:
- `projects/latent_systems/PROJECT_ARCHITECTURE.md` + `NOTES.md` (project root)
- `projects/latent_systems/docs/**`
- `projects/latent_systems/tools/**`
- `projects/latent_systems/tool_build/**` (excluding `_data/state.db`, `_data/_*.json/_*.txt/_*.log`)
- `projects/latent_systems/ep1/**/NOTES.md` + `**/README.md`
- `projects/latent_systems/shared/**/NOTES.md` + `**/README.md`

Generated assets (PNG/MP4/MP3/WAV/JPG under `ep1/` and `shared/`) stay ignored.

**Implications worth banking in spec §5:**
- AD-5 hook enforcement is now operational (was dormant before §2-A).
- Backup-via-git is now factually true for structural content (was false before).
- New canonical commits are gated by hook + Joseph's identity. Build-time accidents would be caught.
- Per-render YAMLs at `_data/<artifact_type>/*.yaml` are tracked — git history of every artifact's structured representation, satisfying AD-5 source-of-truth invariant.

---

## Section to add: "Design principle — content-hash IDs need disambiguators"

Surfaced in Day 5-9 §5 bug 5 (stray-routing classifier YAML collision).

**Principle:** When YAMLs (or other artifacts) are keyed by content-derived ID (hash, fingerprint), and the source content can legitimately repeat across distinct logical artifacts, the key MUST include a disambiguator (filename, source path, or other identifying context). Pure-content-hash IDs are correct only when content uniqueness is guaranteed by domain semantics.

**Where this applies in v1:**
- `walker.py` and `router_tail.py` derive render_id as `sha256(canonical_hash + "|" + filepath)[:16]` — disambiguated. ✓
- `_classifier.py` (stray-routing) initially derived classifier YAML id as `sha256[:16]` only — collided on byte-identical browser duplicates. Fixed to `sha256(filename + "|" + sha256_content)[:16]`. ✓

**Where this should be applied going forward:**
- Phase 2 audit_verdict YAMLs (verdict per render — but if verdict captures content-hash of the render, two renders with identical content would collide unless disambiguator added).
- Phase 3 cross_ai_capture YAMLs (if keyed by capture-content hash, similar concern).

---

## Section to add: "Decision pattern — discipline_version constant unification"

Surfaced in Day 5-9 §4.4. Originally walker hardcoded `pre_v1` and router_tail hardcoded `1.0`. Day 10 cleanup centralized as `tool_build/constants.py`:

```python
CURRENT_DISCIPLINE_VERSION = "1.0"
DISCIPLINE_PRE_V1 = "pre_v1"
```

Both walker + router_tail + dispatcher now import from `constants`.

**Pattern for spec to bank:** any value that must evolve consistently across multiple modules (versions, schema identifiers, threshold constants) lives in `constants.py`, imported elsewhere. Avoids "hardcoded in two files, will silently drift" failure mode.

---

## Section to add: "Decision pattern — UTF-8 console codec on Windows"

Surfaced repeatedly across Day 7, Day 8, Day 9 builds. Windows default cp1252 console codec crashes on em-dashes (`—`), arrows (`→`), and other non-ASCII in Python `print` output.

Day 10 cleanup added `setup_console_encoding()` in `constants.py`, called from each entry point (serve.py, walker.py CLI, future test runners).

**Pattern for spec to bank:** v1 commits to UTF-8 stdout/stderr regardless of platform. Test discipline doesn't need ASCII-only print restrictions. Future modules with CLI entry points should call `setup_console_encoding()` early.

---

## Sections to update with sharpenings

### AD-5 v0.5 carve-out (gitignore reality)
Before §2-A: hook was dormant insurance because LS files weren't tracked.
After §2-A: hook is operational — gates real commits. AD-5 enforcement is now load-bearing rather than precautionary.

### Q2 (discipline_version) — clarify per-artifact-type independence with version-bump procedure
When discipline bumps to 1.1: change `constants.py.CURRENT_DISCIPLINE_VERSION`, write migration to update existing artifacts, bump `app_meta.schema_version` if structural, run smoke tests.

### Section 1 / 3b.7 — watcher debounce sharpening
Current behavior: hash on every event. For browser PNG downloads (small + fast), no issue. For Kling MP4s (large + slow connections), risk that on_moved during partial-write captures partial-content hash as canonical identity. Phase 2 hardening: 2s debounce after on_moved before re-hashing.

---

## Real-world findings worth surfacing in spec

- **84% of canonical files classify as `unknown_image`** in walker output. Original tool attribution lost when router renames files post-routing. Phase 2 cross-references `tools/router_log.md` for recovery (Day 3 §4.1 / Day 5-9 §6.2).

- **21 `_unclassified/` GPT renders already exist** in canonical structure from earlier router runs. Need Phase 2 audit-viewer triage to specific Phase 1 directions.

- **65 stray Downloads files routed in Days 5-9 side excursion** (4/8 - 5/4 backlog). Operational tool at `_data/_inbox_review/` with executor + ledger. If pattern recurs (e.g., post-pivot batch), promote to first-class "Triage workspace" feature.

- **Coexistence smoke test contract under §2-A:** now catches both tracked changes (per gitignore) AND any future un-ignored carve-out additions. Tighter os.walk-based mode no longer needed because gitignore is now correctly scoped.

---

## Section to amend: §1 / 3a.4 Timeout — auto-retry deviation

Build-Claude landed a behavior on Day 12 that diverges from the v0.3
spec text. Surfaced explicitly in Days 11-15 cross-Claude review.

**Current spec text (v0.3 §1, 3a.4):**

> **3a.4 Timeout.** Anthropic 120s, OpenAI 180s, ElevenLabs 60s short
> / 300s long. Mark prompt failed. No auto-retry. UI offers "retry"
> action.

**What actually shipped:**

- `dispatcher._classify_llm_failure` returns `"timeout"` for
  `APITimeoutError`.
- `retry_queue.is_retryable("timeout")` returns `True`.
- The prompt's status is set to `awaiting_retry` (not `failed`).
- `retry_queue.compute_backoff("timeout", ...)` → `(60, 1)`: a single
  auto-retry after 60s, then status flips to `failed` and the UI
  manual-retry path takes over.

**Deviation rationale (banked, not in v0.3 doc):**

The "no auto-retry" rule in the spec was inherited from a stricter
draft where every failure required Joseph's attention. Day 12 review
+ build observed that a flat-out "no auto-retry" rule on timeouts
makes the system unnecessarily fragile in the common case (one slow
network roundtrip), without preventing the rare case (provider
genuinely down). One free retry costs at most one extra failed call
worth of cost; it does not loop indefinitely; and it preserves the
"manual retry" path verbatim once the auto-retry exhausts.

**v0.4 amendment text:**

> **3a.4 Timeout.** Anthropic 120s, OpenAI 180s, ElevenLabs 60s short
> / 300s long. Mark prompt status `awaiting_retry` and enqueue a
> single auto-retry after 60s. If the retry also times out, set
> status to `failed` and surface the manual "retry" action in the UI.
> Rationale: a single timeout is most often a transient network blip;
> a single auto-retry preserves user attention for the genuinely
> stuck case. Cost ceiling: one extra failed call.

**Rule pattern for future deviations:**

When a Phase 1 build-time decision diverges from the spec, the
deviation gets:
1. Captured in this doc as an amendment with explicit rationale.
2. Reflected in code comments at the deviation point (so a reader
   diving into the code sees both the spec it was written against
   and the change).
3. Folded into the next spec revision rather than left as
   undocumented drift.

`dispatcher.py` and `retry_queue.py` already carry inline references
to `3a.4`; they should be updated to reference the v0.4 amendment
once Joseph folds this in.

---

## Items NOT to fold into spec (operational ephemera)

- Specific test file naming (test_d9_ prefix etc.)
- Bug-fix commits during build (those live in git log)
- Cross-Claude review summaries themselves (separate review-record stream)
