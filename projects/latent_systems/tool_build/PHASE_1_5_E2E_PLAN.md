# Phase 1.5 — End-to-end test plan

**Purpose.** Phase 1 acceptance is green against synthetic seeded
graphs (`tests/test_acceptance.py`). That tells us nothing about
whether the system actually behaves under your hands with a real
Claude API draft + a real Midjourney generation + a real Downloads
file landing. This plan is the smallest test that exercises every
real-world path Phase 1 promises to support.

**Outcome.** A single concept whose lineage you can hand-trace from
its row in `concepts` all the way to a real `.png` in the canonical
`projects/latent_systems/ep1/` tree, with F1 (render→prompt query
< 2s) and F4 (lineage layers 1, 2, 3 answerable) verified against
your data — not seed data.

**Time budget.** 30-45 minutes (plus generation wait time).

**Cost.** ~$0.05-0.15 (one Opus 4.7 prompt-drafting call) plus your
Midjourney subscription's standard generation cost.

---

## Pre-flight

| Check | Command | Pass condition |
|---|---|---|
| Server is running | `python tool_build/serve.py --status` | reports `running on port 7890` |
| Schema is at head | `python tool_build/serve.py --migrate-schema` | reports `migrate verified: journal_mode=wal`, no migration applied |
| API key present | `python -c "import os, dotenv; dotenv.load_dotenv('.env'); print('OK' if os.environ.get('ANTHROPIC_API_KEY') else 'MISSING')"` | prints `OK` |
| Browser ready | Open Midjourney in Chrome; sign in if needed | discord/web app loaded |

If any check fails, stop and fix before continuing — this test is not
a debugging session.

---

## Step 1 — Create a concept

Pick any concept from your real ep1 backlog. Don't invent a synthetic
one; that defeats the point. Example values below; substitute your own.

```bash
curl -X POST http://localhost:7890/concepts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "h5_skinner_box_lever_pull",
    "ep": "ep1",
    "section": "h5_slot_machine",
    "subject": "rat at slot machine lever",
    "register": "schematic_apparatus"
  }'
```

**Capture from response:** `concept_id` (16-char hex). Write it down.
You'll need it three more times.

**Verify in UI:** open `http://localhost:7890/`, scroll to the
concepts panel, confirm the new concept appears with status
`drafting`.

---

## Step 2 — Draft a prompt via Claude API

This is the only billed call in this plan.

```bash
curl -X POST http://localhost:7890/prompts/draft_via_api \
  -H "Content-Type: application/json" \
  -d '{
    "concept_text": "Schematic apparatus illustration: a rat in a Skinner box pulling a slot-machine lever, viewed from a 3/4 angle. Educational diagram aesthetic, technical precision, neutral palette.",
    "tool": "midjourney",
    "concept_id": "<paste concept_id from step 1>"
  }'
```

**Capture from response:** `prompt_id`, `cost_usd_estimate`,
`latency_ms`. Write them down.

**Pass conditions:**
- `latency_ms` is between 5000 and 60000 (Opus 4.7 with adaptive
  thinking; if it's < 1000, something didn't actually call the API).
- `cost_usd_estimate` is > 0 and < 0.50.
- `text` field contains a Midjourney-style prompt string with
  parameters (aspect ratio, style refs, etc.) — not a generic
  description.

**Verify cost tracking:**
```bash
curl http://localhost:7890/api_status
```
Should show one new entry under `recent` with the right `cost_usd`
and your `prompt_id`.

---

## Step 3 — Dispatch the prompt

```bash
curl -X POST http://localhost:7890/prompts/<prompt_id>/dispatch
```

**What this does:**
- Creates a `generation_attempts` row with status `in_flight`.
- Copies the prompt text to your clipboard.
- Opens `https://www.midjourney.com/imagine` in your default browser.

**Verify:**
- Browser tab opens.
- Paste (Ctrl-V) into the Midjourney prompt field — your drafted
  text appears verbatim.

---

## Step 4 — Generate in Midjourney

Submit the prompt in Midjourney. Wait for the 2x2 grid (or single
upscale, your call).

Pick one variant, **Save Image** to `~/Downloads/` with whatever
filename Midjourney suggests. Don't rename it — the watcher's hash-
stable identity (3b.7) handles renames, but for a clean baseline
test, leave the filename alone.

---

## Step 5 — Watcher detects the file

Within 1-2 seconds of the file landing in Downloads, the
filesystem watcher hashes it and the dispatcher classifies it as
`midjourney_image` (filename pattern match).

**Verify:**
```bash
curl http://localhost:7890/pending_downloads
```
The new file should appear under `pending` with status `awaiting_route`.

---

## Step 6 — Run the router

The router is invoked manually for now (Phase 2 promotes to auto):

```bash
python projects/latent_systems/tools/downloads_router.py
```

**Pass conditions:**
- Router reports `routed: 1` and the destination path under
  `projects/latent_systems/ep1/h5_slot_machine/<discipline-prefix>/`
  or wherever your section lives.
- Router log line gets appended to `tools/router_log.md`.

The `router_tail` task picks up the new log line within 2-3 seconds
and inserts a `renders` row.

---

## Step 7 — Auto-bind verifies

Within 5 seconds of step 6, the dispatcher's auto-bind logic should
match the new render to the in-flight attempt (single in-flight
attempt + tool match = automatic).

**Verify in UI:** unbound renders panel should be empty. The new
render shows up under the prompt row.

**Or via API:**
```bash
curl http://localhost:7890/unbound_renders
```
should return `[]`.

```bash
curl http://localhost:7890/prompts/awaiting
```
should NOT contain your `prompt_id` anymore (attempt is now
`completed`, not `in_flight`).

---

## Step 8 — F1 query (render → prompt < 2s)

Get the `render_id` from step 6's router output (or query
`/inbox_renders`/`/renders/{render_id}` paths).

```bash
time curl http://localhost:7890/lineage/render/<render_id>
```

**Pass conditions:**
- Wall-clock time < 2s (target: < 100ms; budget: 2s).
- Response includes the original prompt_id.
- Response includes the original concept_id.

This is the discipline contract from spec F1: any render is
recoverable to its origin prompt in under 2s.

---

## Step 9 — F4 lineage layers

The render currently has layer-1 lineage (concept → prompt → render)
implicit through FKs. F4 asks for explicit cross-layer edges. Seed
one:

```bash
curl -X POST http://localhost:7890/lineage_edges \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "render",
    "source_id": "<render_id>",
    "target_type": "concept",
    "target_id": "<concept_id>",
    "layer": 2,
    "valid_from_version": "1.0"
  }'
```

Then query lineage for the render:

```bash
curl http://localhost:7890/lineage/render/<render_id>
```

**Pass conditions:**
- Response includes the layer-1 edges (FK-derived).
- Response includes the layer-2 edge you just created.
- The query returns in < 200ms.

---

## Step 10 — Discipline-drift visibility

```bash
curl http://localhost:7890/discipline_drift
```

**Pass conditions:**
- Your concept (created at `discipline_version=1.0`, the current
  baseline) does NOT appear in drift output (correct: no drift).
- The walker's pre-v1 markers DO appear in the `pre_v1` bucket
  (correct: those are baseline drift, by design).

---

## Cleanup (or don't)

The artifacts created here are real production data, not test data.
Don't `cascading_delete` them. If the concept ends up unused, archive
it via `POST /concepts/{id}/archive`.

The `~/Downloads/` source file can be deleted manually — the canonical
copy is now under `projects/latent_systems/ep1/...`.

---

## What this catches that test_acceptance.py can't

| Failure mode | Synthetic test | E2E plan |
|---|---|---|
| Watcher race on partial-write large MP4 | not exercised | exercised |
| Real Claude latency / token cost vs. estimate | mocked | real |
| Browser auto-open on Joseph's actual Chrome profile | not exercised | exercised |
| Clipboard handoff round-trip on Joseph's actual machine | not exercised | exercised |
| Router-log → router_tail event ordering under real timing | seeded | real |
| YAML write atomicity under real load | trivially exercised | exercised |
| FastAPI lifespan startup against real schema_version | tested at server start | already passing |

If any step above fails in a way the synthetic tests didn't catch,
that failure mode goes into `AUDIT_PATTERNS.md` as a new rule.

---

## Banking after the run

Whether the run passes or finds a bug, write a one-paragraph result
in `banked_items.md` under a "Phase 1.5 e2e run YYYY-MM-DD" heading:

- What concept was used.
- Total wall-clock time.
- Total cost.
- Any deviations from the steps above.
- Any bugs surfaced (and whether they got patched same-session or
  banked).

Phase 2 plans the next iteration on top of this evidence, not on top
of the synthetic acceptance result.
