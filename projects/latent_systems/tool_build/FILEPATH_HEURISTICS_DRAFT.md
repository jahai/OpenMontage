# Filepath heuristics — DRAFT (Phase 3 Wave 1 Day 2-3 implementation spec)

**Date:** 2026-05-07
**Status:** v1.0 DRAFT — preparatory spec for Wave 1 Day 2-3 walker filepath-heuristics pass. Surfaces per-heuristic recovery estimates + genuinely-irrecoverable cohort sizing now so implementation is mechanical transcription. NOT the actual `walker.reclassify_by_filepath` function (that lands when Phase 2 acceptance bridges cross + Wave 1 Day 2-3 unblocks).
**Source:** `phase3_design_notes.md` v0.2 §"Phase 2 carryovers" + `MIGRATION_0004_DRAFT.md` open question 4 + actual state.db inspection of 407 truly-opaque renders.

---

## Scope

Phase 2 Day 1 filename-pattern recovery resolved 1027 of 1434 unknown_image renders (71.6%). The remaining 407 ("truly opaque" per Phase 2 Day 1 banking) are where filepath heuristics enter.

Per AUDIT_PATTERNS Pattern #8: filepath-pattern specifications must include project-content test cases. This draft scopes patterns + names false-positive surfaces explicitly.

**Heuristics resolved here surface to Wave 1 Day 2-3 walker pass via** `walker.reclassify_by_filepath()` function (analog to existing `walker.reclassify_unknowns()` filename pass).

**Pattern #8 guardrail:** the new `unknown_image_terminal` value (Migration 0004 Step 4 application-level extension) marks the genuinely-irrecoverable cohort after this pass exhausts. Stops indefinite recovery work.

---

## Empirical filepath distribution (state.db inspection 2026-05-07)

407 unknown_image rows clustered into 46 distinct parent buckets. Top-25 buckets cover 95%+ of population:

| Count | Filepath bucket | Recovery class |
|---|---|---|
| 55 | `ep1/_work/round5_section4e_explore` | mixed — see Heuristic D |
| 45 | `ep1/h4_match_cut/_work` | mixed — see Heuristic D |
| 35 | `shared/visual_identity_phase1_references/3_composite_subject` | A → midjourney |
| 32 | `shared/visual_identity_phase1_references/2_architectural_inhabitant` | A → midjourney |
| 29 | `shared/visual_identity_phase2_evaluations/5_surreal_subject` | A → midjourney |
| 24 | `ep1/_legacy/_renders` | B → frame_extract |
| 23 | `ep1/k1_compulsion_choice/_work` | mixed — see Heuristic D |
| 22 | `ep1/_work/gg_register_experiment_2026_05_02` | mixed — see Heuristic D |
| 21 | `shared/visual_identity_phase2_evaluations/4_schematic_apparatus` | A → midjourney |
| 20 | `shared/visual_identity_phase1_references/4_schematic_apparatus` | A → midjourney |
| 14 | `ep1/h9_ep2_tease/_work` | mixed — Heuristic D |
| 14 | `ep1/cold_open/assembled` | partial → frame_extract via Heuristic B |
| 12 | `shared/remotion_project/out` | C → remotion (NEW taxonomy value) |
| 7 | `ep1/h7_system_works/_work` | mixed — Heuristic D |
| 7 | `ep1/h6_streak/_work` | mixed — Heuristic D |
| 4 | `ep1/h4_match_cut/sources` | likely B + manual |
| 4 | `ep1/cold_open/sources` | likely B + manual |
| 3 | `ep1/h5_slot_machine/sources` | partial |
| 3 | `ep1/card2_doom_scrolling/_work` | Heuristic D |
| 2 | `shared/ident_remotion/out` | C → remotion |
| ... (smaller buckets summing to ~30 files) | various | mixed |

---

## Heuristic A — Visual identity direction folders → midjourney

**Pattern.** Filepath matches `shared/visual_identity_phase[12]_<references|evaluations>/<direction>/` where `<direction>` is one of the 5 named directions (`1_latent_space`, `2_architectural_inhabitant`, `3_composite_subject`, `4_schematic_apparatus`, `5_surreal_subject`).

**Why it works.** Visual-identity Phase 1 was the original MJ exploration session per `shared/visual_identity_phase1_references/README.md` ("Phase 1 reference collection per project handoff narrative... generated 2026-05-02 by Joseph"). Files in these directories are predominantly MJ outputs.

**Recovery estimate.** 35 + 32 + 29 + 21 + 20 = **~137 files** in the top-5 visual-identity buckets, plus ~10-20 more in smaller direction buckets. **Total: ~150 files.**

**Confidence guard (per AUDIT_PATTERNS Pattern #8 — false-positive surface).** Apply this heuristic ONLY when the filename ALSO contains a UUID-style 8-char hex pattern (e.g., `_cdf6dda4_`, `_e4c36ca3_`). MJ outputs carry hash-derived job IDs as part of filename convention; non-MJ files in the same directory (rare but possible — Joseph might have dropped Kontext or Flux explorations into a visual-identity direction folder) lack this pattern.

**Test fixture requirement.** Test must include `shared/visual_identity_phase1_references/3_composite_subject/manual_edit_no_uuid.png` (synthetic — represents a non-MJ file in MJ-shaped directory) and assert it stays `unknown_image_terminal`, not reclassified to `midjourney`.

**Pseudocode:**
```python
VISUAL_IDENTITY_DIR_RE = re.compile(
    r"shared/visual_identity_phase[12]_(references|evaluations)/[^/]+/", re.I
)
UUID8_HEX_RE = re.compile(r"_[a-f0-9]{8}_", re.I)

def heuristic_a(filepath: str, filename: str) -> Optional[str]:
    """Returns 'midjourney' if filepath + filename match, else None."""
    if VISUAL_IDENTITY_DIR_RE.search(filepath) and UUID8_HEX_RE.search(filename):
        return "midjourney"
    return None
```

---

## Heuristic B — Timecode-named legacy renders → frame_extract

**Pattern.** Filename matches `^v\d+_\d+s\.png$` (e.g., `v1_60s.png`, `v1_63s.png`) OR `^tc_\d+s\.png$` (e.g., `tc_0s.png`). Filepath typically `ep1/_legacy/_renders/` or section's `assembled/`.

**Why it works.** These are frame extracts at specific timecodes from video — `v1_60s.png` = "version 1 at 60 seconds", `tc_0s.png` = "timecode 0 seconds". Phase 2 Day 1's `FRAME_RE` (`frame_NNNN.png` / `fNN_NN.png` / `t_X.X.png` / `_final_tX.X.png`) didn't include these patterns; v0.6 review caught it during reading but didn't ship.

**Recovery estimate.** ~24 files in `ep1/_legacy/_renders/` + ~6-8 in `ep1/cold_open/assembled/` (e.g., `cold_open_v3_check_60s.png`, `shotA_glow_t4s.png`) + scattered in other section assemblies. **Total: ~30-35 files.**

**Confidence guard.** Pattern is unambiguous. Test fixture: positive cases (`v1_60s.png`, `tc_0s.png`, `shotA_glow_t4s.png` — note the timecode suffix); negative case: `v1_typography_check.png` (version-prefix without timecode → does NOT match).

**Pseudocode:**
```python
FRAME_RE_EXTENDED = re.compile(
    r"^v\d+_\d+s\.png$|"
    r"^tc_\d+s\.png$|"
    r".*_t\d+s\.png$|"  # e.g., shotA_glow_t4s.png
    r".*_v\d+_check_\d+s\.png$",  # e.g., cold_open_v3_check_60s.png
    re.I,
)

def heuristic_b(filepath: str, filename: str) -> Optional[str]:
    if FRAME_RE_EXTENDED.match(filename):
        return "frame_extract"
    return None
```

**Note:** could also extend `walker.classify()`'s existing `FRAME_RE` to absorb these patterns. That makes future filename-pattern recovery (e.g., new files arriving with these names) automatic without filepath heuristic. Recommend integrating into `FRAME_RE` rather than keeping as filepath-only heuristic.

---

## Heuristic C — Remotion output directories → remotion (NEW tool taxonomy value)

**Pattern.** Filepath contains `remotion_project/out/` OR `ident_remotion/out/` OR matches `^.*/(?:remotion|render)_(?:project|out)/.*$`.

**Why it works.** These are Remotion-rendered output frames per project Remotion pipeline. Files like `loss_aversion_mid_hold.png`, `architects_hold.png`, `brichter_mid_hold.png` are Remotion compositions exported as stills (mid-hold = mid-animation freeze frame for use as reference / asset).

**Recovery estimate.** 12 (`shared/remotion_project/out/`) + 2 (`shared/ident_remotion/out/`) + ~3-5 in other Remotion paths. **Total: ~17-20 files.**

**Taxonomy extension required.** Add `remotion` to `renders.tool` valid values. **Application-level extension, no schema change** (same precedent as `frame_extract` in Phase 2 Day 1; bank in Migration 0004 §Step 4 alongside `unknown_image_terminal`).

**Confidence guard.** Pattern is unambiguous if applied to `remotion_project/out/` or `ident_remotion/out/`. Beware false positives on hypothetical Joseph filepaths like `shared/remotion_research/refs/` (likely Remotion *references* not *outputs*) — match the `out/` segment specifically, not just `remotion`.

**Test fixture requirement.** Positive: `shared/remotion_project/out/loss_aversion_mid_hold.png`. Negative: `shared/remotion_project/src/composition_test.png` (in remotion project but `src/` not `out/`).

**Pseudocode:**
```python
REMOTION_OUT_RE = re.compile(
    r"^.*/(?:remotion_project|ident_remotion|[\w_]*remotion[\w_]*)/out/", re.I
)

def heuristic_c(filepath: str, filename: str) -> Optional[str]:
    if REMOTION_OUT_RE.search(filepath):
        return "remotion"
    return None
```

---

## Heuristic D — `_work/` subdirs of named EP1 sections (mixed; partial recovery)

**Pattern.** Filepath like `ep1/<section>/_work/` OR `ep1/_work/<exploration_session>/`.

**Why it's mixed.** Files within these directories are heterogeneous:
- Some are MJ-generated explorations
- Some are frame extracts
- Some are Joseph manual edits / annotations / cropped halves
- Some are Kontext / Flux explorations without UUID markers

**Recovery strategy.** Apply Heuristics A, B, C in priority order; what remains is genuinely opaque mixed work.

Sample inspection of `ep1/h4_match_cut/_work/` (45 files):
- `f_09.png`, `f_12.png` → frame_extract via Heuristic B integration into FRAME_RE
- `protag_match_annotated.png`, `rat_right_half.png` → manual edit / derived; no tool fit
- `protag_frames_v2_peak_window.png` → likely frame extract or manual crop

**Estimated recovery within `_work/` buckets (combined):** ~20-30 files via heuristics A/B/C; remainder ~150 files genuinely opaque.

**No additional heuristic for `_work/` beyond A/B/C.** These directories are exploration spaces; mixed-tool content is expected. The genuinely-opaque remainder becomes `unknown_image_terminal`.

---

## Heuristic E — Joseph-explicit file moves into wrong-tool buckets

**NOT a heuristic; banking as a real edge case.**

Some files in the truly-opaque cohort are `_DEPRECATED_<reason>.png`-suffixed files representing rejected alternates (per channel staple #12). E.g., `porch_v1_DEPRECATED_real_estate_listing_register.png` in `ep1/_work/round5_section4e_explore/`.

These are MJ-generated (the directory pattern + "register" terminology suggests MJ) but the deprecation suffix complicates filename-pattern matching. Heuristic A's UUID-hex guard would skip them (no `_<8-hex>_` in filename).

**Resolution options:**
1. **Accept as terminal:** these are deprecated alternates; tool attribution doesn't add audit-trail value. Mark `unknown_image_terminal`.
2. **Heuristic E (loose):** in `ep1/_work/<exploration>/` + `_DEPRECATED_<reason>.png` suffix → infer midjourney with low confidence (`subtype: 'inferred_low_confidence'`).
3. **Defer:** ship without; revisit if `unknown_image_terminal` rate of `_DEPRECATED_*` files becomes a query nuisance.

**Recommendation: option 3 (defer).** ~50-60 `_DEPRECATED_` files; their tool attribution doesn't affect F8 serialization (deprecated alternates aren't shipped). Revisit if friction surfaces.

---

## Net recovery summary

| Heuristic | Files recovered | New tool value | Confidence |
|---|---|---|---|
| A — Visual identity dirs + UUID | ~150 → midjourney | (existing) | High (with UUID guard) |
| B — Timecode-named legacy | ~30-35 → frame_extract | (existing) | High |
| C — Remotion output | ~17-20 → remotion | NEW | High |
| D — _work/ subdirs (residual after A/B/C) | ~20-30 to existing categories | (existing) | Mixed |

**Total recovered:** ~217-235 files (~55% of the 407 truly-opaque cohort).

**Genuinely opaque remainder:** ~172-190 files → `unknown_image_terminal`. Includes:
- Joseph manual edits / annotations / crops without tool markers
- Mixed-tool exploration content in `_work/` subdirs without filename patterns
- `_DEPRECATED_` files lacking UUID markers (per Heuristic E option 3 deferral)
- Genuinely orphan files with descriptive names like `architects_hold.png`, `brichter_mid_hold.png` outside `remotion/out/` paths

This recovery rate matches v0.1 review item 7 prediction (filepath heuristics 30-60% of truly-opaque cohort).

---

## Walker integration spec (Wave 1 Day 2-3)

```python
# walker.py — Wave 1 Day 2-3 extension

def reclassify_by_filepath(*, dry_run: bool = False, verbose: bool = False) -> dict:
    """Phase 3 Wave 1 Day 2-3 migration: re-run heuristics A/B/C against
    rows where tool='unknown_image' (i.e., the truly-opaque cohort that
    Phase 2 Day 1 filename-pattern pass left unrecovered).

    Per phase3_design_notes.md v0.2 §"Phase 2 carryovers" +
    FILEPATH_HEURISTICS_DRAFT.md: target recovery ~55% of the 407
    truly-opaque renders (~217-235 reclassified).

    Genuinely-irrecoverable remainder marked tool='unknown_image_terminal'
    per AUDIT_PATTERNS Pattern #8 + Migration 0004 Step 4 application-
    level taxonomy extension. Stops indefinite recovery work.

    Returns summary {walked, reclassified by tool, marked_terminal,
    unchanged, errors}.
    """
    # 1. Query: SELECT FROM renders WHERE tool='unknown_image'
    # 2. For each: try Heuristic A → B → C in priority; if any matches,
    #    update tool + variant + YAML.
    # 3. If none match: update tool='unknown_image_terminal' + YAML
    #    (terminal marker; don't try again unless explicitly invoked).
    # 4. Per-file commit (matching existing reclassify_unknowns pattern).
    # 5. Verbose mode prints per-file decision.
```

CLI flag: `python walker.py --reclassify-by-filepath`. Mirrors existing `--reclassify-unknowns` from Phase 2 Day 1.

**Default execution order (Wave 1 Day 2-3):**
1. Run `--reclassify-by-filepath` against current state
2. Verify recovery rate matches estimate (target: >50%, threshold: <30% triggers heuristic-tightening review)
3. Bank `unknown_image_terminal` count in `banked_items.md` "Phase 3 e2e run" entry

---

## Test fixtures (Pattern #8 mandatory third bucket)

Per AUDIT_PATTERNS Pattern #8: content-matching specs require "looks-like-target-but-isn't" project-specific test cases.

**Heuristic A test cases:**
- ✅ `phase1_composite_subject_visual_vocab_b_cdf6dda4_v1.png` in `shared/visual_identity_phase1_references/3_composite_subject/` → midjourney (positive)
- ✅ `D5_thesis_a1_human-chamber-failed_v2.png` in `shared/visual_identity_phase2_evaluations/5_surreal_subject/` → handled? UUID guard fires off `_a1_` (not 8-hex) — would NOT match. Correct: this is project-content but not the MJ-direction-files class. Bank as: heuristic A's UUID guard correctly excludes it; Joseph manually triages or it stays terminal.
- ❌ `shared/visual_identity_phase1_references/3_composite_subject/manual_edit_no_uuid.png` (synthetic) → should NOT match (no UUID hash). Stays terminal.
- ❌ `ep1/h4_match_cut/_work/protag_match_annotated.png` (no visual-identity dir) → should NOT match.

**Heuristic B test cases:**
- ✅ `v1_60s.png`, `tc_0s.png`, `shotA_glow_t4s.png`, `cold_open_v3_check_60s.png` → frame_extract
- ❌ `v1_typography_check.png` (version-prefix, no timecode) → does NOT match
- ❌ `60s_card.png` (timecode in name but not in v_/tc_/_t pattern) → does NOT match (intentional — too loose otherwise)

**Heuristic C test cases:**
- ✅ `shared/remotion_project/out/loss_aversion_mid_hold.png` → remotion
- ✅ `shared/ident_remotion/out/architects_hold.png` → remotion
- ❌ `shared/remotion_project/src/composition_test.png` (in project but `src/` not `out/`) → does NOT match
- ❌ `shared/remotion_research/refs/example.png` (research not output) → does NOT match

**Existing Pattern #2 cases that should NOT be regressed:**
- `frame_0044.png` → frame_extract (Phase 2 Day 1; should still work after heuristic integration)
- `nycwillow_*_3.png` → midjourney (Phase 2 Day 1 strict pattern; should still match before any heuristic fires)
- `_mj_<hex8>_<variant>.png` infix → midjourney (Phase 2 Day 1 broader pattern)

---

## Open questions for Wave 1 Day 2-3 implementation

1. **Heuristic B integration into walker.classify().** Recommended: integrate `FRAME_RE_EXTENDED` patterns into existing `FRAME_RE` so future files arriving with these names get classified at insert time, not requiring filepath-heuristic pass. Migration 0004 §Step 4 application-level work.

2. **Heuristic C `remotion` taxonomy taxonomy bank location.** New `renders.tool` value via Migration 0004 application-level extension. Walker `classify()` adds matching path. Bank in `phase3_design_notes.md` §"Phase 2 carryovers" alongside `unknown_image_terminal` — both are application-level taxonomy extensions, no SQL.

3. **`_DEPRECATED_` files terminal vs Heuristic E.** Recommend deferral (option 3 in Heuristic E section). Revisit if friction surfaces in F8 serialization queries against deprecated files.

4. **Heuristic firing order vs walker re-walk.** Should `reclassify_by_filepath()` run only against existing `unknown_image` rows (current cohort), OR also as a re-walk pass that re-checks already-classified rows in case a heuristic could improve attribution? Recommend: only against current cohort (per Phase 2 Day 1 precedent). Improvement passes are explicit Joseph-invoked work, not automatic.

5. **Recovery rate threshold for "go-live" decision.** If actual recovery falls below 30% (vs target 55%), heuristics need tightening before declaring Wave 1 Day 2-3 complete. Bank this threshold in PHASE_3_E2E_PLAN.md when authored.

---

## Document maintenance

- **v1.0 DRAFT (2026-05-07):** Phase 3 Wave 1 Day 2-3 preparatory spec. Empirical state.db inspection (407 truly-opaque renders, 46 buckets). Three primary heuristics (A: visual identity dirs → MJ with UUID guard; B: timecode-named → frame_extract; C: Remotion output → remotion NEW taxonomy value) + Heuristic D (residual `_work/` mixed) + Heuristic E (`_DEPRECATED_` deferral). Net recovery ~55% (~217-235 files); ~172-190 files become `unknown_image_terminal`. Test fixtures specified per AUDIT_PATTERNS Pattern #8 third-bucket requirement (project-specific looks-like-target-but-isn't cases). 5 open questions for implementation. Lives at `tool_build/FILEPATH_HEURISTICS_DRAFT.md` (sibling to MIGRATION_0004_DRAFT.md + F8_OPENMONTAGE_ADAPTER_MAPPING.md as design-spec docs). Implementation transcribes from this when Phase 2 acceptance bridges cross + Wave 1 Day 2-3 unblocks.
