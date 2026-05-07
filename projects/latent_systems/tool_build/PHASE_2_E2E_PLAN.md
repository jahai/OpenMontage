# Phase 2 — End-to-end test plan

**Purpose.** Phase 2 acceptance is green against synthetic seeded
graphs (`tests/test_audit*.py`). That tells us nothing about whether
the system actually behaves under your hands with a real audit
session + real Anthropic vision API consultation + real verdict
capture flowing through the audit viewer UI. This plan is the
smallest test that exercises every real-world path Phase 2 promises
to support.

**Outcome.** A single render audited end-to-end: marked with a
verdict via the UI, consulted via the AI, both events captured to
`_data/verdicts/<id>.yaml` + `_data/ai_consultations/<id>.yaml`, with
F8 success criterion 5 verified (verdict durable from moment of
marking, recoverable after session close + reopen).

**Time budget.** 30-45 minutes (plus the rubric authoring; that's a
prerequisite).

**Cost.** Wave A path: $0 (no AI calls). Wave B path: ~$0.30 per
vision consultation against `claude-opus-4-7` per design notes §1
4.2 placeholder.

---

## Pre-flight

| Check | Command | Pass condition |
|---|---|---|
| Server is running | `python tool_build/serve.py --status` | `running on port 7890` |
| Schema is at head | `python tool_build/serve.py --migrate-schema` | `migrate verified`, no migration applied |
| API key present | `python -c "import os, dotenv; dotenv.load_dotenv('.env'); print('OK' if os.environ.get('ANTHROPIC_API_KEY') else 'MISSING')"` | prints `OK` |
| Rubric authored | `ls projects/latent_systems/docs/AUDIT_RUBRICS_v*.md` | at least one match |
| Browser ready | Open `http://localhost:7890/audit/grid` in Chrome | grid page renders |

If the rubric is missing, Wave A path runs but Wave B (steps 6-8)
fails with `400 "no audit rubric available"`. Author at least one
rubric file before continuing the full plan.

---

## Step 1 — Pick a real render to audit

Open `http://localhost:7890/audit/grid?tool=midjourney&only_unverdicted=1`
(or any filter that surfaces a render you actually want a verdict on).

**Capture:** the `render_id` of the first thumbnail (hover; URL ends
`render_id=<16-char-hex>`). Write it down.

**Pass conditions:**
- Thumbnail loads (`/audit/thumbnail/<id>` returns JPEG within ~1s
  on cache miss; instant on cache hit)
- No verdict badge in the corner (since `only_unverdicted=1` filter)

---

## Step 2 — Start an audit session

Click **▶ start (quick)** in the header. Page reloads with
`?session_id=<sid>` appended.

**Pass conditions:**
- Header shows `session <sid_prefix>… mode: quick_pass | rubric v1.0`
- `■ end` link visible

**Verify session row in db:**
```
curl -s http://localhost:7890/audit/sessions | python -m json.tool
```
Should include the new session with `started` timestamp, `ended: null`,
`mode: quick_pass`, `total_consultations: 0`, `total_cost_usd: 0.0`.

---

## Step 3 — Click into serial view

Click the thumbnail you picked in step 1. Page navigates to
`/audit?render_id=<id>&session_id=<sid>` with serial view.

**Pass conditions:**
- Image loads at native resolution (`/audit/render/<id>/file`)
- Right sidebar shows: render meta (filename + tool), concept (if
  bound), lineage (if any edges), verdict marking buttons, AI
  consultation section (empty initially), prev/next nav
- Queue position pill: `1 / N` (or wherever you are in the filtered queue)

---

## Step 4 — Mark a verdict (Wave A: no AI)

Press `2` (or click the **strong** button). The button highlights
blue. Toast confirms `verdict: strong`.

**Pass conditions:**
- Active button updates to `strong`
- Existing-verdict chip appears below: `existing: strong by human at <ts>`
- F8 instant write per 4.9: a verdict YAML appears at
  `_data/verdicts/<verdict_id>.yaml` within milliseconds

**Verify YAML:**
```bash
ls -la projects/latent_systems/tool_build/_data/verdicts/ | tail -3
cat projects/latent_systems/tool_build/_data/verdicts/<id>.yaml
```
Should show the new verdict YAML with `verdict: strong`,
`audit_session_id: <sid>`, `audited_by: human`.

---

## Step 5 — Toggle the flag

Press `F`. Toast confirms `flag set` (or `flag will be captured with
next verdict` if you didn't already mark one). The checkbox in the
sidebar updates.

**Verify state.db:**
```bash
python -c "
import db
conn = db.connect()
row = conn.execute('SELECT id, verdict, flags_needs_second_look FROM verdicts WHERE id = ?', ('<verdict_id>',)).fetchone()
print(row)
conn.close()
"
```
Should return `(<id>, 'strong', 1)`.

---

## Step 6 — Consult AI (Wave B; gated on rubric)

Press `C` (or click **consult again** since you just marked a
verdict). Sidebar shows `consulting AI… (this can take 10-30s for
vision)`.

**Pass conditions:**
- POST `/audit/render/<id>/consult` returns `201` within ~30s
- Result card appears: provider `anthropic`, status `completed` (or
  `safety_refused` / `parse_failed` if AI didn't produce structured
  output for some reason)
- For `completed` status: `verdict_inference` color-coded,
  `criteria_match` grid, `key_observations` bullets, cost line
  showing `$0.X · claude-opus-4-7 · <ts>`

**Verify state.db rows:**
```bash
python -c "
import db
conn = db.connect()
row = conn.execute('SELECT provider, status, cost_usd FROM ai_consultations WHERE verdict_id = ?', ('<verdict_id>',)).fetchone()
print(row)
conn.close()
"
```
Should return `('anthropic', '<status>', <cost>)`.

**Verify YAML at `_data/ai_consultations/<consult_id>.yaml`:**
should contain the full raw response + parsed JSON.

---

## Step 7 — Reload to see existing-consultation persistence

Hit refresh. The page reloads with the consultation rendered server-
side in the AI consultation panel.

**Pass conditions:**
- Section heading: `AI consultation (1)` (or N if you ran multiple)
- Consultation card visible without pressing C
- Button label: `consult again`

This verifies the Phase 2.5 enhancement (audit.get_render_detail
includes ai_consultations).

---

## Step 8 — End the session

Click **■ end**. Page reloads without `session_id` query param.

**Pass conditions:**
- Header shows `no session ▶ start (quick) ▶ start (deep)` again
- Verdicts marked under the now-ended session remain visible per-render
- The session itself is queryable via:
  ```
  curl http://localhost:7890/audit/cost?session_id=<sid>
  ```
  Should return `total_consultations: 1, total_cost_usd: 0.X,
  ended: <ts>` reflecting the consultation cost rollup.

---

## Step 9 — F8 verdict-durability check

Close the browser tab. Wait 30 seconds. Reopen
`http://localhost:7890/audit?render_id=<id>`.

**Pass conditions:**
- Existing-verdict chip still shows `strong`
- Existing AI consultation still rendered in the consultation panel
- Both round-trip from filesystem (state.db is cache; YAMLs are
  source-of-truth per AD-5)

This is the F8 success criterion 5: "Audit verdicts durable from
moment of marking. Mark a render as hero-zone. Close the chat.
Reopen the app a day later. Verdict still present, with reasoning,
with audit-rubric used, with AI consultations logged."

---

## Step 10 — Discipline-version drift check (cross-cut F10)

```
curl -s http://localhost:7890/discipline_drift | python -m json.tool
```

The verdict + ai_consultations rows you just created should appear
in the `1.0` bucket of `totals_by_version`. Pre_v1 renders (1707 of
them) appear in the `pre_v1` bucket as expected.

This verifies Phase 2 didn't break Feature 9.

---

## Cleanup (or don't)

The artifacts created here are real audit data, not test data.
Don't `cascading_delete` them — they're part of your audit trail.

If you want to redo the run, supersede the verdict via
`POST /audit/render/<id>/verdict` with `supersedes_verdict_id: <prior>`
in the body. The old verdict stays in the audit-trail; the
supersession surfaces in the existing-verdict chip.

The thumbnail cache at `_data/_audit_thumbnails/<id>.jpg` can be
deleted manually if you ever want to force regeneration; it auto-
regenerates on next access.

---

## What this catches that test_audit*.py can't

| Failure mode | Synthetic test | E2E plan |
|---|---|---|
| Real Anthropic vision latency / token cost vs estimate | mocked | real |
| Real safety-filter behavior on actual render content | not exercised | exercised |
| Real downscale via Pillow on actual canonical PNG sizes | exercised tiny | exercised native |
| Browser keyboard-shortcut interception across textareas | not exercised | exercised |
| Page-reload state recovery (F8 success criterion 5) | not exercised | exercised |
| Real session cost rollup with real cost values | mocked | real |
| Real lineage chain rendering in sidebar (edge counts > 0) | trivial | exercised |
| HTML template rendering against Jinja2 syntax errors | not exercised | exercised |

If any step above fails in a way the synthetic tests didn't catch,
that failure mode goes into `AUDIT_PATTERNS.md` as a new rule (per
the "every operational task is also a spec audit pass" banking
principle from Phase 1).

---

## Banking after the run

Whether the run passes or finds a bug, write a one-paragraph result
in `banked_items.md` under a "Phase 2 e2e run YYYY-MM-DD" heading:

- What render was audited.
- Total wall-clock time (start session → consultation → reload).
- Total cost (Wave B path actually fires).
- Any deviations from the steps above.
- Any bugs surfaced (and whether they got patched same-session or
  banked).

Phase 3 plans the next iteration on top of this evidence, not on top
of synthetic acceptance results.
