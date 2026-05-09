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

Detailed error handling is in this file's §"Atomic-transaction failure semantics" section (added per v0.4 amendments item 3 — separate commit). Brief overview here:

- **Step 1 fails (file move)**: file source missing OR destination not writable. Modal stays open; surface error inline ("File move failed: <reason>"); Promote button re-enabled. No db write happened.
- **Step 1 succeeds, Step 2 fails (db row)**: rollback Step 1 (delete file from `winners/`); surface error inline ("Failed to commit promotion record; file move rolled back"); Promote button re-enabled.
- **Step 3 fails (F6 prompt fire)**: Steps 1+2 already committed (transaction succeeded); Step 3 fires async post-commit and is best-effort. Modal already closed at this point; failure surfaces in retry queue + non-blocking notification.

See §"Atomic-transaction failure semantics" for the explicit Python try/except shape.

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

- **v1.0 DRAFT (2026-05-09):** Phase 3 Wave 1 Day 4-5 preparatory spec for the F5 hero-promotion confirmation modal. Forward + reverse flow modals specified. Sub-components 1-4 (file move, hero_promotions row, NOTES.md prompt, doc-update coordination) each have presentation + content rules. Modal sizing/dismiss/focus management specified. Confirmation interaction = single button + cancel; typed confirmation rejected as over-engineered for reversible action. Async behavior: Steps 1+2 sync atomic, Step 3 async post-commit, Step 4 read-only display. Error-state overview hands off to §"Atomic-transaction failure semantics" (added per v0.4 amendments item 3 — separate commit). 8 [OPEN: need Joseph decision] items consolidated. Implementation hooks for `hero_promote()` + `hero_un_promote()` + endpoint pair sketched. Test fixtures specified including channel-staple-#12 reason-required + path-traversal sanitization. Lives at `tool_build/F5_MODAL_UX_DRAFT.md` (sibling to F6_DRAFT_PROMPT_DRAFT.md + Migration 0004 + filepath heuristics drafts + e2e plans). Implementation transcribes from this when Wave 1 Day 4-5 unblocks.
