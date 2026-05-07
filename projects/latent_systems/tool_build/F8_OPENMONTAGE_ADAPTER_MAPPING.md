# F8 — OpenMontage `asset_manifest` adapter mapping

**Date:** 2026-05-07
**Status:** v1.0 — Wave 1 Day 1 deliverable. Schema-read complete; mapping settled. F8 implementation in Wave 4 reads from this doc.
**Source:** `OpenMontage/schemas/artifacts/asset_manifest.schema.json` (read directly Wave 1 Day 1 per `phase3_design_notes.md` v0.2 §6 Revision 1).
**Scope:** `asset_manifest` only. `edit_decisions` is OpenMontage's edit agent's responsibility per AD-2 boundary + Phase 3 v0.2 F8 scope decision.

---

## Field-by-field mapping

### Required fields

OpenMontage `asset_manifest.assets[]` requires: `id`, `type`, `path`, `source_tool`, `scene_id`.

| OpenMontage field | tool_build source | Notes |
|---|---|---|
| `id` | `renders.id` (16-char hex) | direct copy. Phase 1 sha256-derived IDs collide-resistant per Day 5-9 §5 bug 5 banking. |
| `type` | derived from `renders.tool` per mapping table below | OpenMontage enum: image / video / audio / narration / music / sfx / diagram / animation / code_snippet / subtitle / font / lut. |
| `path` | `renders.filepath` (repo-relative) | **Finding J:** OpenMontage spec says "Relative path within the pipeline project directory." F8 serialization MUST resolve relative-to-pipeline-project at handoff time, NOT at insert time. Banked as runtime concern in §"Open architectural questions." |
| `source_tool` | `renders.tool` (raw value) | direct copy. e.g., "midjourney", "frame_extract", "flux". |
| `scene_id` | derived: `concept.section` via `renders.prompt_id → prompts.concept_id → concepts.section`; `'unscoped'` fallback | Per v0.2 amendment: scene_id derived at serialization time, NOT a stored column. Migration 0004 unaffected. |

### `renders.tool` → `asset_manifest.type` mapping

| `renders.tool` value | `asset_manifest.type` | Optional `subtype` | Notes |
|---|---|---|---|
| `midjourney` | `image` | `ai_generated_via_midjourney` | Generated still |
| `gpt_image_2` | `image` | `ai_generated_via_gpt_image_2` | Generated still |
| `flux` | `image` | `ai_generated_via_flux` | Generated still (Flux + Kontext family) |
| `frame_extract` | `image` | `frame_extract` | Derived from video; not generated |
| `kling` | `video` | `ai_generated_via_kling` | Generated motion |
| `video` | `video` | `unspecified_video` | Tool-build's bucket for non-Kling video; rare in practice |
| `audio` | `audio` | `unspecified_audio` | **Finding F warning** — see §"Audio subtype distinction" below |
| `unknown_image` | `image` | `recovery_pending` | Tool attribution recovery still in progress (Phase 1 walker filename pattern misses) |
| `unknown_image_terminal` | `image` | `recovery_terminal` | Phase 3 Wave 1 Migration 0004 adds this value. Render couldn't be attributed; recovery exhausted. |
| `unknown` | `image` (fallback) | `unknown_type` | Last-resort fallback; rare enough to accept the imprecision. |

### Optional fields populated when available

| OpenMontage field | tool_build source | When populated |
|---|---|---|
| `prompt` | `prompts.text_preview` (200-char preview) via `renders.prompt_id → prompts.id` | Render bound to a prompt (post-v1 only per AD-3) |
| `seed` | NOT TRACKED | Banked as Phase 3.5+ if seed-tracking becomes valuable |
| `model` | `api_calls.provider + api_calls.endpoint` if AI-generated | Render produced via `dispatcher.draft_via_api` flow (Phase 1 Day 11+) |
| `cost_usd` | `api_calls.cost_usd_estimate` summed over render's api_calls | Cost tracking from Phase 1 Q11; sum across render's prompt-drafting + verdict-consultation costs |
| `duration_seconds` | NOT TRACKED for stills; for videos may need ffprobe at serialization | Phase 1 walker doesn't capture duration. Phase 3 Wave 4 adds ffprobe-on-demand if F8 deliverable requires it. |
| `resolution` | NOT TRACKED at insert; could derive from Pillow/ffprobe at serialization | Same as duration: derive on-demand at F8 trigger. |
| `format` | derived from `renders.filename` extension | trivial: `.png` → "png", `.mp4` → "mp4", etc. |
| `quality_score` | derived from `verdicts.verdict` per mapping below | Latest non-superseded verdict (per existing audit.get_render_detail logic) |
| `subtype` | per type-mapping table above | "Sub-classification" per OpenMontage spec. |
| `generation_summary` | NOT TRACKED | Banked as Phase 3.5+ if needed; could derive from prompts.text_preview + concepts.subject |
| `provider` | `api_calls.provider` | only when AI-generated |
| `license` | NOT TRACKED | Phase 1 didn't model licensing. Default to `"all_rights_reserved"` for Latent Systems work. Banked as Phase 3.5+ for stock-asset workflows. |
| `original_url` | NOT TRACKED | Same as license. |

### `verdicts.verdict` → `quality_score` mapping

OpenMontage `quality_score` is `number 0-1`. tool_build's 4-bucket enum maps:

| `verdicts.verdict` | `quality_score` | Reasoning |
|---|---|---|
| `hero_zone` | `1.0` | Best-in-set; canonical-quality |
| `strong` | `0.8` | Near-canonical; usable in primary placement |
| `weak` | `0.5` | Usable as alternate or placeholder |
| `reject` | `0.0` | Excluded from manifest by default — see §"Filtering" |

**Filtering:** `reject` verdicts default to *excluded* from the asset_manifest. F8 trigger config should expose an `include_rejects: false` default; Joseph can override per serialization run if needed for archival completeness.

### Top-level fields

| OpenMontage field | tool_build source |
|---|---|
| `version` | const `"1.0"` (per schema) |
| `assets[]` | array built via the per-render mapping above |
| `total_cost_usd` | sum of `cost_usd` across all included assets |
| `metadata` | tool_build-specific data per Finding G — see §"Metadata escape hatch" |

---

## Five additional findings from schema-read (F-J; supplements v0.1 review's A-E)

### Finding F — Audio subtype distinction

OpenMontage's type enum has 4 audio values: `audio`, `narration`, `music`, `sfx`. tool_build's `audio` tool value is generic — covers all four.

**Implication for Wave 4:** when F8 serializes audio renders, it needs to distinguish narration/music/sfx from generic audio. Options:

1. **Defer:** ship F8 with all `audio` renders typed as `audio`. Sufficient for Phase 3 since canonical audio is rare (32 renders per state.db). Add narration/music/sfx distinction in Phase 3.5+ when audio workflow expands.
2. **Filename heuristic:** `_narr_` / `_music_` / `_sfx_` prefix conventions in filenames; map at serialization.
3. **Render YAML extension:** add `audio_subtype` field to renders YAMLs; populate at insert time. Migration 0005 territory.

**Recommendation: option 1 (defer).** 32 audio renders is small enough scale that misclassification doesn't dominate F8 utility. Revisit if audio asset count grows or OpenMontage's edit agent needs the distinction for narration timing.

### Finding G — `additionalProperties: false` at all object levels

`asset_manifest.assets[]` items have `additionalProperties: false`. tool_build can NOT add custom fields inline on each asset. Top-level `metadata` is open (untyped object) — that's the escape hatch.

**Implication:** tool_build-specific metadata (verdict reasoning, lineage chain, audit session ID, ai_consultation_ids) must live at the top-level `metadata` dict, NOT inline on each asset. Suggested structure:

```json
{
  "version": "1.0",
  "assets": [...],
  "total_cost_usd": 0.0,
  "metadata": {
    "tool_build_version": "phase_3_v0.2",
    "discipline_version": "1.0",
    "serialized_at": "<iso>",
    "audit_session_id": "<id_or_null>",
    "section": "h5_slot_machine",
    "rubric_version": "1.0",
    "per_asset": {
      "<asset_id>": {
        "verdict_reasoning": "...",
        "lineage_edges": [...],
        "ai_consultation_ids": [...],
        "flags": {"needs_second_look": false}
      }
    }
  }
}
```

The `metadata.per_asset` keyed sub-dict carries tool_build internals without violating the strict per-asset schema. OpenMontage's edit agent can ignore it; tool_build round-tripping (serialize → re-deserialize) preserves the audit trail.

### Finding H — `quality_score` is optional but informative

OpenMontage's `quality_score` (0-1, optional) is the cleanest place to surface tool_build's verdict commitment. The 4-bucket → 0-1 mapping (1.0/0.8/0.5/0.0) gives OpenMontage's edit agent a usable signal for asset selection without exposing tool_build's enum.

**Implication:** populate `quality_score` for every asset that has a non-superseded verdict. Renders without a verdict get the field omitted — OpenMontage treats absence as "unknown quality" which is the honest signal.

### Finding I — `subtype` is a useful escape valve

`subtype` is "Sub-classification (e.g. 'background', 'stock', 'generated')." tool_build can use it to encode tool-attribution sub-info that doesn't fit `source_tool` cleanly:

- `frame_extract` (derived from video, not generated)
- `ai_generated_via_midjourney` / `ai_generated_via_gpt_image_2` etc.
- `recovery_pending` for `unknown_image`
- `recovery_terminal` for `unknown_image_terminal`

This makes the mapping table above use `subtype` consistently rather than overloading `source_tool` with mixed concerns.

### Finding J — `path` is "relative to pipeline project directory"

OpenMontage's `path` field comment: "Relative path within the pipeline project directory." This is NOT the same as tool_build's `renders.filepath` which is repo-root-relative.

**Implication:** F8 serialization must translate path at handoff time. Two approaches:

1. **Pipeline-project relative at serialization:** F8 trigger writes `path` as relative to wherever OpenMontage's pipeline project root is. Requires Joseph to specify the target pipeline project dir at serialization time.
2. **Repo-root relative + metadata flag:** F8 writes `path` as repo-root-relative; metadata field flags it. OpenMontage's edit agent does the translation at consumption.

**Recommendation: option 1.** OpenMontage's spec says path is pipeline-project-relative; respecting the spec at serialization is cleaner than off-loading translation downstream. F8 trigger config exposes a `pipeline_project_root` parameter; default could be a sibling directory like `OpenMontage/pipelines/<latent_systems_episode>/`.

---

## Open architectural questions

These don't block Wave 1 Day 1 mapping work but need resolution before Wave 4 F8 implementation:

1. **`pipeline_project_root` default.** Where does F8's pipeline-project target dir live? Per Finding J option 1, F8 needs a target. Suggested: `OpenMontage/pipelines/latent_systems/<episode>/` as a Phase 3 convention. Joseph confirms or proposes alternative.

2. **Asset path translation.** When F8 generates `path = "<asset>.png"` relative to `pipeline_project_root`, does the actual canonical render need to be COPIED into the pipeline project, or can OpenMontage's edit agent resolve the path through a symlink / virtual mount? Phase 3 Wave 4 implementation decision.

3. **`renderer_family` placement.** OpenMontage `edit_decisions.renderer_family` is required at proposal stage and locks Remotion composition. tool_build doesn't capture this. Two options:
   - Joseph specifies at F8 trigger time (default for Latent Systems channel: `documentary-montage` per channel character).
   - Bank as F8 trigger param; F8 doesn't decide.
   
   **Recommendation:** trigger param with `documentary-montage` default. Honors AD-2 boundary (tool_build doesn't make editorial/renderer decisions; surfaces the choice as the trigger user's call).

4. **Single-section vs multi-section serialization.** Per spec Q6 v0.2: per-section trigger (NOTES.md-completion event). Each F8 firing produces ONE asset_manifest covering ONE section's renders. Joseph confirms or proposes multi-section batching for efficiency.

5. **Re-serialization after verdict supersession.** When Joseph supersedes a verdict (e.g., revises hero_zone → strong), should F8 auto-regenerate the asset_manifest for the affected section? Or require explicit re-trigger? **Recommendation:** explicit re-trigger to avoid silent state-rewrites; F8 trigger surface in audit viewer surfaces "section X has updated verdicts; regenerate manifest?" prompt.

---

## Migration 0004 confirmation

Per v0.2 design notes §"Migration 0004 schema sketch": no schema changes required for F8 specifically. The mapping above derives all required + optional fields from existing tables (`renders`, `prompts`, `concepts`, `verdicts`, `api_calls`) joined at serialization time.

Migration 0004 carries:
- `notes_md_state` (new — F6)
- `cross_ai_captures` 7-column expansion (F7)
- `idx_verdicts_flagged` partial index (Phase 2 carryover)
- `unknown_image_terminal` value in renders.tool taxonomy (no schema change; application-level)

None of these are F8-specific. F8 reads from the substrate.

---

## Summary

F8 schema-read complete. Mapping is mostly clean — tool_build's existing schema joins produce 4 of 5 required fields directly (`id`, `type` via mapping, `source_tool`, `path`); `scene_id` derives from `concept.section` per v0.2 settled. Optional fields populate from existing data where tracked.

Five non-blocking architectural questions surfaced (pipeline_project_root, asset path translation, renderer_family placement, single vs multi-section trigger, re-serialization-after-supersession). Resolution before Wave 4 implementation; none affect Wave 1 Migration 0004 design.

Wave 1 Day 1 deliverable complete. Subsequent Wave 1 days (Migration 0004 SQL, F6 code, F5 atomic action) remain gated on Phase 2 acceptance bridge crossing per phase3_design_notes.md v0.2.

---

## Document maintenance

- **v1.0 (2026-05-07):** Wave 1 Day 1 schema-read deliverable. Mapping table for required + optional asset_manifest fields. Five additional findings (F-J) supplementing v0.1 review's A-E. Five open architectural questions surfaced for Wave 4 resolution. Migration 0004 confirmed no F8-specific schema changes needed.
