# F5 — Hero promotion confirmation modal UX (DRAFT)

**Date:** 2026-05-09
**Status:** v1.0 DRAFT — preparatory spec for Wave 1 Day 4-5 implementation. NOT the actual `hero_promote_endpoint` + modal template (lands when Phase 2 acceptance bridges cross + Wave 1 Day 1-3 unblocks). Surfaces modal UX decisions now so implementation is mechanical transcription, not 8 invented UI calls under deadline pressure.
**Source:** `phase3_design_notes.md` v0.2 §"F5 — Hero promotion atomic action" + Q1 settle + §"F5 hero promotion failure modes" 5.1-5.5; `PHASE_3_E2E_PLAN.md` Step 3 (forward-flow) + Step 9b (un-promotion); spec § channel staple #12 (un-hero requires reason); existing audit-viewer modal patterns (none yet — F5 modal is the first modal in tool_build).

---

## Scope

F5 is the audit viewer's hero-promotion atomic action. Per v0.2 Q1 settle: button next to the verdict-marking buttons; click opens a confirmation modal exposing the multi-step action; Joseph confirms before commit; avoids accidental clicks committing irreversible state.

This doc specs the modal UX for both forward (promote-to-hero) and reverse (un-promote-from-hero) flows: layout, sub-component preview content, confirmation interaction, dismiss behavior, error display, async behavior, accessibility hooks. Failure-mode rollback semantics are addressed in `F5_MODAL_UX_DRAFT.md` §"Atomic-transaction failure semantics" (item 3 of v0.4 amendments — separate landing).

Out of scope for this draft:
- Underlying `hero_promote()` business-logic implementation (Wave 1 Day 4-5 code).
- F6 NOTES.md prompt content itself (covered by `F6_DRAFT_PROMPT_DRAFT.md`).
- Doc-update coordination implementation (F9 calibration); this draft only specs how the modal *surfaces* it.
- Render-group compare-and-rank view (Phase 3.5+ extension banked separately).

---

## Trigger + entry context

**Forward flow (promote to hero).** Modal triggered by clicking "Promote to hero" button in the audit viewer's serial-view sidebar. Button placement: directly below the 4 verdict-marking buttons + flag row + reasoning textarea, in the same Verdict section. Visible only when:
- A current (non-superseded) verdict exists for the render
- The verdict is `hero_zone` OR `strong` (weak/reject promotion is blocked at the button level — surface tooltip "promote requires verdict ≥ strong")
- The render isn't already in a `winners/` path (button shows "Already promoted" state if so)

**Reverse flow (un-promote).** Modal triggered by clicking "Un-promote" button. Visible only when the render IS already in a `winners/` path. Same sidebar location.

**Keyboard shortcut:** [OPEN: need Joseph decision] — recommend `H` for promote (mnemonic: "hero"), `Shift+H` for un-promote (modifier matches the destructive direction). Not part of the existing 1-4/F/C verdict-marking shortcut block; both verdicts confirm on key-press, but F5 always opens a modal — the keyboard shortcut would just open the modal, not bypass it.

---

## Modal layout — forward flow (promote to hero)

The modal is a **single-column dialog**, ~520px wide, centered overlay over a translucent backdrop. Sub-components render top-to-bottom in execution order (matches the four atomic-action steps so Joseph reads it as a transaction sequence):

```
┌─ Promote to hero ──────────────────────────────────── × ┐
│                                                          │
│  Section: h3_skinner                                     │
│  Render: H3_lab_wide_continuation_mj_e3f1cff6_3.png      │
│  Current verdict: strong (by human, 2026-05-09T10:33)    │
│                                                          │
│  ─── 1. File move ───                                    │
│  ep1/h3_skinner/reference/<old>/<filename>               │
│      → ep1/h3_skinner/winners/<filename>                 │
│                                                          │
│  ─── 2. hero_promotions row ───                          │
│  verdict_id:    <16-char hex>                            │
│  hero_filepath: ep1/h3_skinner/winners/<filename>        │
│  promoted_at:   <ISO timestamp at submit>                │
│  promoted_by:   joseph (from session)                    │
│                                                          │
│  ─── 3. NOTES.md update prompt (queued) ───              │
│  Section h3_skinner has new hero render.                 │
│  F6 prompt will fire post-commit; queued for review at   │
│  /audit/notes-md/h3_skinner once F6 ships.               │
│  [graceful degradation per failure mode 5.3 if F6 N/A]   │
│                                                          │
│  ─── 4. Doc-update coordination ───                      │
│  Promotion may surface in:                               │
│    • ep1/h3_skinner/NOTES.md (F6 prompt above)           │
│    • [OPEN: need Joseph decision] additional doc list    │
│  Read-only summary; F9 calibration handles actual updates│
│                                                          │
│  [ Cancel ]                          [ Promote to hero ] │
└──────────────────────────────────────────────────────────┘
```

### 4.1. File-move target preview

**Decision: path-only display, not full-tree visualization.**

Rationale: full-tree visualization of `ep1/<section>/` would render dozens of sibling files (reference/, sources/, _DEPRECATED_*/, etc.) for visual context Joseph already knows. Path-only with old → new arrow is the minimum-cognitive-load shape and matches Joseph's mental model ("this file goes there").

Display format:
```
<from-path-relative-to-ep1>
    → <to-path-relative-to-ep1>
```

If old path is in `_DEPRECATED_<reason>/` (rare but possible — re-promoting a previously un-promoted render), show the reason in parentheses next to the from-path so Joseph sees the un-promote → re-promote transition explicitly.

If `winners/` doesn't exist for that section (failure mode 5.2), show inline:
```
ep1/h3_skinner/winners/  (will be created)
```
with a subtle visual distinction (italic + warning icon) so Joseph notes the directory creation. No separate confirmation step; the modal's main "Promote" button covers it.

### 4.2. hero_promotions row preview

**[OPEN: need Joseph decision] — which fields shown, in what shape.** Recommendation: 4 fields, key:value left-aligned, monospace font:
- `verdict_id` (16-char hex, abbreviated to 8+`…` for visual scan)
- `hero_filepath` (canonical path, same as Step 1's to-path)
- `promoted_at` (ISO timestamp computed at modal-submit time, displayed in viewer-local timezone with timezone abbreviation)
- `promoted_by` (pulled from the active audit session's user; defaults to `joseph` if no session)

Skipped from preview by default (visible if Joseph wants — could expand a "details" toggle in v2): `id`, `created`, internal columns, `reversed_at`/`reversed_reason` (NULL on forward flow), `rubric_version` if present.

### 4.3. NOTES.md update prompt content (queued)

**Decision: queued message, not blocking.**

Rationale per v0.2 §F5 failure mode 5.3: "NOTES.md update prompt fires but F6 isn't ready (graceful degradation: surface as 'needs follow-up' without blocking promotion)." So the modal's Section 3 is INFORMATIONAL — explains what F6 will do once it fires, doesn't actually fire it inline.

When F6 ISN'T yet shipped (current state): show graceful-degradation copy explicitly:
> Section h3_skinner has new hero render. F6 NOTES.md authorship not yet shipped — promotion records in audit trail; NOTES.md update queued for manual revisit.

When F6 IS shipped: show the queued-message copy:
> Section h3_skinner has new hero render. F6 prompt will fire post-commit; queued for review at /audit/notes-md/h3_skinner once you're ready to author.

The link to `/audit/notes-md/<section>` is clickable but doesn't navigate from the modal — copies to clipboard with a small "copied" toast so Joseph can paste it after closing the modal.

### 4.4. Doc-update coordination summary

**[OPEN: need Joseph decision] — which docs surface, presentation, dismissable or read-only.**

Recommendations:

**Which docs:** F9 calibration is the source-of-truth for "which docs reference this render's section." Until F9 is implemented, the modal can't compute this dynamically. v0.4 amendment recommendation: list 1-3 known canonical docs that always coordinate with hero promotions — at minimum `ep1/<section>/NOTES.md`, plus any `EP1_STRUCTURAL_ARCHITECTURE_v*.md` reference if section is at SHIPPED state. If the list is empty/unknown, show: "No coordinated doc updates known for this section yet (F9 calibration pending)."

**Presentation:** read-only bullet list. NOT actionable; the modal doesn't open these docs for editing. Joseph reviews + acknowledges by confirming the modal.

**Dismissable:** [OPEN: need Joseph decision] — recommend NOT-dismissable within the modal (it's part of the review surface). Joseph can dismiss the WHOLE modal via Cancel; no per-section dismissal. Rationale: making sub-sections dismissable creates a "what did I dismiss / can I get it back" UX problem; whole-modal cancel + retry is simpler.

---

## Modal layout — reverse flow (un-promote)

Similar single-column structure, BUT with one critical addition: a **REQUIRED reason field** per channel staple #12. Modal refuses to proceed if reason is empty.

```
┌─ Un-promote from hero ─────────────────────────────── × ┐
│                                                          │
│  Section: h3_skinner                                     │
│  Render: <filename>                                      │
│  Currently promoted: <hero_filepath>                     │
│  Promoted at: <iso, by promoted_by>                      │
│                                                          │
│  ─── Reason for un-promotion (REQUIRED) ───              │
│  [ textarea for reason, min 5 chars, refuses empty ]     │
│  Per channel staple #12: un-hero requires reason.        │
│  Reason becomes the _DEPRECATED_<reason>/ subdir name.   │
│                                                          │
│  ─── 1. File move ───                                    │
│  ep1/h3_skinner/winners/<filename>                       │
│      → ep1/h3_skinner/_work/<context>/_DEPRECATED_<r>/   │
│                                                          │
│  ─── 2. hero_promotions row update ───                   │
│  reversed_at:     <ISO at submit>                        │
│  reversed_reason: <from textarea above>                  │
│                                                          │
│  ─── 3. NOTES.md update prompt (queued) ───              │
│  Same pattern as forward flow; F6 update for             │
│  un-promotion event.                                     │
│                                                          │
│  [ Cancel ]                       [ Un-promote ]         │
└──────────────────────────────────────────────────────────┘
```

The **Un-promote** confirmation button is disabled (greyed out) until reason field has ≥5 chars. Hover tooltip on disabled button: "Enter a reason for un-promotion (required per channel staple #12)."

The reason text is sanitized for filesystem use (lowercase, replace whitespace with `_`, strip non-alphanumeric except `_-`) and used as the `_DEPRECATED_<reason>/` subdir name. Sanitized version is shown beneath the textarea in real-time as `Will create directory: _DEPRECATED_<sanitized>/` so Joseph sees what filename will result before submit.

---

## Modal sizing, dismiss, focus management

**[OPEN: need Joseph decision] — modal sizing.** Recommendations:

- **Width:** 520px fixed (not full-screen; not viewport-percentage). Rationale: file paths (the longest text) fit comfortably at 520px without wrapping; sidebar verdict-marking is ~380px so the modal is meaningfully bigger but not overwhelming.
- **Height:** auto, max 80vh. If content exceeds 80vh (rare but possible if doc-update list is long), scroll inside the modal with the action buttons sticky at bottom.
- **Z-index:** above all audit-viewer content, including consultation cards.

**Dismiss behavior:**
- Esc key: dismiss (treats as Cancel)
- Click outside modal (on backdrop): dismiss (treats as Cancel)
- Cancel button: dismiss
- × close icon (top-right): dismiss
- All four routes are equivalent — Cancel does NOT confirm anything

**Focus management:**
- On open: focus moves to the modal (not the Cancel button — would be too easy to accidentally Esc + Enter and dismiss). Focus the **modal title** so screen readers announce it; tab order goes Cancel → Promote/Un-promote.
- On close: focus returns to the trigger button (Promote-to-hero / Un-promote in the sidebar).
- Reverse flow textarea: autofocus on the textarea on open (Joseph needs to type reason; first action is always type-in-textarea).

---

## Confirmation interaction

**Decision: single confirm button + cancel; no typed confirmation.**

Rationale: typed confirmation ("type 'PROMOTE' to confirm") is a heavy pattern for high-stakes destructive operations (DROP TABLE, force-push). Hero promotion is reversible via un-promote per channel staple #12, so typed confirmation is over-engineered. The modal review surface (sub-components 1-4) is the friction; the confirmation button is the commit.

**Button behavior:**
- Forward: button text is "Promote to hero", color matches `hero_zone` button (green `#059669`)
- Reverse: button text is "Un-promote", color is amber/warning (`#d97706`) — destructive but not catastrophic
- Disabled state: greyed (`#9ca3af`), cursor `not-allowed`, tooltip explains why
- Loading state (after click, before response): button text changes to "Promoting…" / "Un-promoting…" with spinner; both buttons disabled to prevent double-fire (per the consult-double-fire bug we banked 2026-05-08 — same pattern)
- After successful response: modal shows brief success state (~500ms — "Promoted ✓"), then closes; sidebar refreshes with new state

---

## Async behavior across the 4 sub-components

Per Joseph's brief item 1 spec:

| Step | Sync/Async | Reason |
|---|---|---|
| 1. File move | Sync (in transaction) | Filesystem write; must succeed before Step 2 commits |
| 2. hero_promotions row insert | Sync (in transaction) | Atomic with Step 1; rollback Step 1 if fails |
| 3. NOTES.md update prompt fire | **Async, post-commit** | F6 prompt fire is best-effort; failure shouldn't roll back successful promotion |
| 4. Doc-update coordination summary | **Read-only display, no actual update fires** | Modal shows summary; F9 calibration handles actual updates separately |

The modal returns immediately after Step 2 commits (sync part). Step 3 fires in the background — UI shows a small "F6 prompt queued" indicator in the next page render but doesn't block the modal close.

If Step 3 fails (F6 endpoint down, etc.), the failure is logged + queued for retry per failure mode 5.4 (per-doc retry queue parallel to api_calls retry pattern). Joseph sees a non-blocking notification on next page load: "1 NOTES.md update prompt failed to queue — see /retry_queue."

---

## Error states (handoff to atomic-transaction failure semantics)

Detailed error handling is in §"Atomic-transaction failure semantics" below. Brief overview here:

- **Step 1 fails (file move)**: file source missing OR destination not writable. Modal stays open; surface error inline ("File move failed: <reason>"); Promote button re-enabled. No db write happened.
- **Step 1 succeeds, Step 2 fails (db row)**: rollback Step 1 (delete file from `winners/`); surface error inline ("Failed to commit promotion record; file move rolled back"); Promote button re-enabled.
- **Step 3 fails (F6 prompt fire)**: Steps 1+2 already committed (transaction succeeded); Step 3 fires async post-commit and is best-effort. Modal already closed at this point; failure surfaces in retry queue + non-blocking notification.

See §"Atomic-transaction failure semantics" for the explicit Python try/except shape.

---

## Atomic-transaction failure semantics

**Transaction boundary:** Steps 1 (file move) + 2 (hero_promotions row insert) are inside a single try/except block with mutual rollback. Step 3 (F6 prompt fire) is OUTSIDE the transaction — fires post-commit, best-effort, queued for retry on failure. Step 4 (doc-update coordination summary) is read-only display in the modal; no failure mode (nothing to fail).

This shape mirrors `audit_consult.consult_render`'s pattern (verdict find-or-create is sync; F6 prompt-fire equivalent is the async post-commit callback). Reusing the established pattern keeps audit-trail discipline consistent across F5 + F6 + Wave 1's other atomic actions.

### Per-step rollback table

| Step | Operation | Failure mode | Rollback path | UI surface |
|---|---|---|---|---|
| 1 | shutil.copy2 (or .move) source → winners/ | source missing, dest not writable, disk full | None needed (no prior step to undo) | Modal stays open; inline error; Promote button re-enabled |
| 2 | INSERT INTO hero_promotions | UNIQUE constraint, FK fail, db locked | Delete file at winners/ destination (Step 1 undo) | Modal stays open; inline error noting "file move rolled back"; Promote button re-enabled |
| 3 | F6 NOTES.md prompt fire (Claude API call queued or fired) | F6 not yet shipped, API down, rate-limit, timeout | None — Steps 1+2 stay committed; Step 3 enters retry queue per failure mode 5.4 | Modal already closed; non-blocking notification on next page render: "1 NOTES.md update queued for retry — see /retry_queue" |
| 4 | n/a (read-only display) | n/a | n/a | n/a |

### Explicit Python shape (Wave 1 Day 4-5 implementation transcribes)

```python
# dispatcher.py — F5 hero_promote() atomic transaction

def hero_promote(*, render_id: str, audit_session_id: Optional[str] = None) -> dict:
    """F5 forward flow per F5_MODAL_UX_DRAFT.md.

    Atomic boundary: Steps 1+2 (file move + db insert) commit together
    or roll back together. Step 3 (F6 prompt fire) fires post-commit,
    best-effort; failure queued for retry, doesn't roll back Steps 1+2.
    """
    # Pre-validation (raises HeroPromotionError before any state change)
    detail = audit.get_render_detail(render_id)
    if detail is None:
        raise HeroPromotionError(f"render {render_id!r} not found")
    verdict = detail.get("verdict")
    if verdict is None:
        raise HeroPromotionError(
            f"render {render_id!r} has no current verdict; mark a verdict first"
        )
    if verdict["verdict"] not in ("hero_zone", "strong"):
        raise HeroPromotionError(
            f"verdict {verdict['verdict']!r} ineligible for promotion; "
            "requires hero_zone or strong"
        )

    src_path = repo_root() / detail["filepath"]
    section = _resolve_section_from_render(detail)  # via concept lookup
    winners_dir = repo_root() / "projects/latent_systems/ep1" / section / "winners"
    winners_dir.mkdir(parents=True, exist_ok=True)  # 5.2: auto-create OK
    dest_path = winners_dir / src_path.name

    # === ATOMIC BOUNDARY (Steps 1 + 2) ===
    file_moved = False
    try:
        # Step 1: file move
        shutil.copy2(src_path, dest_path)
        file_moved = True

        # Step 2: hero_promotions row insert
        promotion_id = _hashed_id(verdict["id"], dest_path.as_posix())
        conn = db.connect()
        try:
            with conn:
                conn.execute(
                    """INSERT INTO hero_promotions
                       (id, render_id, verdict_id, hero_filepath,
                        promoted_at, promoted_by, audit_session_id, yaml_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (promotion_id, render_id, verdict["id"],
                     str(dest_path.relative_to(repo_root()).as_posix()),
                     _iso_now(), _resolve_promoted_by(audit_session_id),
                     audit_session_id, _yaml_path_for(promotion_id)),
                )
        finally:
            conn.close()
        # YAML write after db commit (mirrors verdict-capture YAML-after-row pattern)
        _write_promotion_yaml(promotion_id, ...)

    except Exception as e:
        # Rollback Step 1 if it landed
        if file_moved and dest_path.exists():
            try:
                dest_path.unlink()
            except OSError as rollback_err:
                # Rare: file moved but rollback failed (permissions changed
                # mid-transaction). Surface both errors so Joseph can manually
                # reconcile via filesystem inspection.
                raise HeroPromotionError(
                    f"transaction failed AND rollback failed; manual cleanup "
                    f"needed at {dest_path}. original error: {e}; "
                    f"rollback error: {rollback_err}"
                )
        raise HeroPromotionError(f"hero promotion failed: {e}")
    # === END ATOMIC BOUNDARY ===

    # Step 3: F6 NOTES.md prompt fire (POST-COMMIT, best-effort)
    f6_status = "deferred"
    try:
        if _f6_endpoint_available():
            # Async fire — don't block the response on F6 latency
            f6_status = _enqueue_f6_notes_md_update(
                section=section,
                trigger="hero_promotion",
                render_id=render_id,
                hero_promotion_id=promotion_id,
            )
        else:
            # F6 not yet shipped (current state)
            f6_status = "deferred_f6_not_shipped"
    except Exception as e:
        # F6 fire failed — Steps 1+2 stay committed; queue for retry per 5.4
        retry_queue.enqueue(
            kind="f6_notes_md_update",
            payload={"section": section, "trigger": "hero_promotion",
                     "render_id": render_id, "hero_promotion_id": promotion_id},
            error=str(e),
        )
        f6_status = "failed_queued_for_retry"

    return {
        "ok": True,
        "hero_promotion_id": promotion_id,
        "hero_filepath": str(dest_path.relative_to(repo_root()).as_posix()),
        "f6_prompt_status": f6_status,  # 'fired' | 'queued' | 'deferred*' | 'failed_queued_for_retry'
    }
```

### Reverse flow analog

`hero_un_promote()` follows the same atomic shape but with destinations swapped:

- Step 1: file move from `winners/<filename>` → `_work/<context>/_DEPRECATED_<sanitized_reason>/<filename>`
- Step 2: UPDATE hero_promotions SET reversed_at = ?, reversed_reason = ? WHERE id = ?
- Step 3: F6 prompt fire (NOTES.md update for un-promotion event; same async/best-effort shape)

Rollback for un-promote: if Step 2 fails after Step 1 lands, move the file BACK from `_DEPRECATED_*/` to `winners/`. Same try/except pattern, swap the rollback move direction.

### Failure-mode coverage map

Maps the failure-mode taxonomy in `phase3_design_notes.md` v0.2 §F5 to specific exception/branch in the shape above:

| Failure mode | Code location | Caller-facing surface |
|---|---|---|
| 5.1 Render file missing at promotion time | Step 1 try → FileNotFoundError | inline modal error; HeroPromotionError raised |
| 5.2 Hero `winners/` directory doesn't exist | `winners_dir.mkdir(parents=True, exist_ok=True)` (auto-create) | Modal preview shows directory-creation notice; no error |
| 5.3 NOTES.md update prompt fires but F6 isn't ready | `_f6_endpoint_available()` False branch → `f6_status = "deferred_f6_not_shipped"` | Modal already closed; non-blocking notification "F6 prompt deferred" |
| 5.4 Doc-update coordination fails mid-loop | F9 calibration's responsibility (this layer just queues); same retry-queue pattern as F6 above | Non-blocking notification on next page render |
| 5.5 Un-hero (reverse promotion) reason missing | Modal-level guard (textarea ≥5 chars) + endpoint-level revalidation | Submit button disabled; endpoint returns 400 |

### Why post-commit async for Step 3

Three reasons:

1. **F6 latency.** F6 NOTES.md authorship is a Claude API text call; per F6_DRAFT_PROMPT_DRAFT.md cost section v1.1, expect 5-15s server-side. Blocking the modal close on a 10s+ async call would feel hung.
2. **F6 not always shipped.** During Wave 1 (when F5 lands but F6 hasn't), Step 3 has nothing to call into; graceful degradation per failure mode 5.3 needs a non-blocking codepath. Wrapping Step 3 in the atomic boundary would force F5 to wait for F6 — wrong dependency direction.
3. **Hero promotion is editorial commitment; F6 prompt is downstream artifact.** The promotion itself is the user's decision; the F6 prompt is the system suggesting "now go author the NOTES.md update." Joseph might want to defer that to a later session. Best-effort fire matches user mental model.

---

## Open questions for Joseph decision

These items have [OPEN] markers in the body above; consolidating here for review:

1. **Keyboard shortcut for promote/un-promote.** Recommend `H` (promote) + `Shift+H` (un-promote). Joseph's call: stick with this, or different keys, or no shortcut?
2. **hero_promotions row preview fields.** Recommend 4 fields: `verdict_id`, `hero_filepath`, `promoted_at`, `promoted_by`. Add or remove?
3. **Doc-update coordination — which docs surface.** Until F9 calibration is implemented, the modal can't compute this dynamically. Acceptable to show a static "no coordinated docs known yet (F9 pending)" message, or do you want a hardcoded short list?
4. **Doc-update coordination — dismissable per-section?** Recommend NOT (whole-modal Cancel only). Confirm or override?
5. **Modal width sizing.** Recommend 520px fixed. Joseph use a different display width that would benefit from a different default?
6. **Reverse flow reason min-char threshold.** Recommend 5 chars min. Trivial to change; Joseph's threshold preference?
7. **Reverse flow `_DEPRECATED_<reason>/` sanitization rules.** Recommend lowercase + whitespace→underscore + strip non-alphanumeric except `_-`. Sound, or different convention?
8. **Modal opens on keyboard shortcut, or only on mouse click?** Recommend keyboard shortcut opens modal (modal still requires explicit Confirm — keyboard shortcut is just modal-open shortcut, not action shortcut). Confirm.

---

## Implementation hooks (Wave 1 Day 4-5)

```python
# dispatcher.py — Wave 1 Day 4-5 extension

def hero_promote(
    *,
    render_id: str,
    audit_session_id: Optional[str] = None,
) -> dict:
    """F5 forward flow: file move + hero_promotions row insert
    (atomic, sync) + NOTES.md update prompt fire (async, best-effort).

    Returns dict:
      ok=True, hero_promotion_id=<id>, hero_filepath=<path>,
      f6_prompt_status='queued'|'fired'|'deferred'|'failed'

    Raises HeroPromotionError (caller-facing setup error) on:
      - render not found
      - verdict missing or weak/reject (refuses promotion)
      - winners/ directory not writable
    Raises atomic-transaction errors on Step 1+2 failure (see
    §Atomic-transaction failure semantics for shape).
    """
    pass


def hero_un_promote(
    *,
    render_id: str,
    reason: str,
    audit_session_id: Optional[str] = None,
) -> dict:
    """F5 reverse flow: file move from winners/ to
    _work/<context>/_DEPRECATED_<sanitized_reason>/, hero_promotions
    row update (reversed_at + reversed_reason), F6 NOTES.md update
    prompt fire.

    Reason is required and validated upstream by the modal; this
    function still validates (reason.strip() >= 5 chars).
    """
    pass
```

Endpoint pair:
- `POST /audit/render/<render_id>/promote` → returns hero_promotion record + F6 status
- `POST /audit/render/<render_id>/un_promote` → body includes reason; returns updated hero_promotion record + F6 status

Modal template lives at `templates/hero_promotion_modal.html` — included into `audit.html` via Jinja `{% include %}` and shown/hidden via JS triggered from the sidebar buttons.

---

## Test fixtures (Pattern #8 mandatory third bucket)

**Positive cases:**
- Promote a render with verdict `hero_zone` from h3_skinner reference/ → modal renders all 4 sub-components → confirm → file moves to winners/, hero_promotions row inserted, F6 prompt fires (or gracefully degrades if F6 not yet shipped)
- Un-promote a hero render with reason "register drift on second look" → modal renders reason textarea → submit → file moves to _DEPRECATED_register_drift_on_second_look/, hero_promotions row updated with reversed_at + reversed_reason

**Project-specific looks-like-target-but-isn't:**
- Promote a render with verdict `weak` → button is disabled with tooltip; modal cannot open
- Promote a render whose `winners/` directory doesn't exist → modal shows directory-creation notice; submit auto-creates and proceeds
- Un-promote with reason field empty → submit button stays disabled; modal cannot proceed
- Un-promote with reason "../etc/passwd" → sanitized to `etc_passwd` (no path traversal possible)

**Negative cases:**
- Promote a render that doesn't exist → 404 on endpoint, error toast in modal
- Promote during F6 outage → Steps 1+2 succeed, Step 3 fires async + fails + queues for retry; Joseph sees non-blocking notification, not a blocked promotion
- Promote a render that's already in winners/ → button shows "Already promoted" state; modal cannot open
- Concurrent promote (Joseph double-clicks before modal opens) → JS guard at button level; only one modal opens

---

## Document maintenance

- **v1.1 DRAFT (2026-05-09; v0.4 amendment 3):** Atomic-transaction
  failure semantics section added. Per-step rollback table; explicit
  Python try/except shape for hero_promote() + reverse-flow analog;
  failure-mode coverage map linking phase3_design_notes.md v0.2 §F5
  taxonomy to specific code locations; rationale for post-commit async
  on Step 3. Body of doc unchanged; section inserted between Error
  states (handoff) and Open questions.
- **v1.0 DRAFT (2026-05-09):** Phase 3 Wave 1 Day 4-5 preparatory spec for the F5 hero-promotion confirmation modal. Forward + reverse flow modals specified. Sub-components 1-4 (file move, hero_promotions row, NOTES.md prompt, doc-update coordination) each have presentation + content rules. Modal sizing/dismiss/focus management specified. Confirmation interaction = single button + cancel; typed confirmation rejected as over-engineered for reversible action. Async behavior: Steps 1+2 sync atomic, Step 3 async post-commit, Step 4 read-only display. Error-state overview hands off to §"Atomic-transaction failure semantics" (added per v0.4 amendments item 3 — separate commit). 8 [OPEN: need Joseph decision] items consolidated. Implementation hooks for `hero_promote()` + `hero_un_promote()` + endpoint pair sketched. Test fixtures specified including channel-staple-#12 reason-required + path-traversal sanitization. Lives at `tool_build/F5_MODAL_UX_DRAFT.md` (sibling to F6_DRAFT_PROMPT_DRAFT.md + Migration 0004 + filepath heuristics drafts + e2e plans). Implementation transcribes from this when Wave 1 Day 4-5 unblocks.
