# Rubric calibration scratch — Documentary integrity sharpening (2026-05-13)

**Workstream 1B output, Day 1 of Phase 3 sprint.** Proposed revision to
the `Documentary integrity` criterion in `docs/AUDIT_RUBRICS_v1_0.md`
adding **apparatus accuracy** and **period authenticity** as explicit
dimensions per Pattern #8 reinforcement #4.

**This is a scratch file for Joseph review** — Claude Code authors here
(tool_build/ subtree allowed by AD-5); Joseph integrates the approved
language into `docs/AUDIT_RUBRICS_v1_0.md` himself before Day 2 morning
F5 work begins.

## Why this calibration

The water-in-rat-anchor case study (H#3 v3, parked 2026-05-13): the
locked rat-anchor render at the rat State 1 stage showed water
mechanisms (water bottle / lapping behavior) instead of food-reward
conditioning apparatus. The actual 1930s Skinner box used food pellets
delivered via lever — water was not part of the canonical operant-
conditioning setup the narration references.

Current `Documentary integrity` criterion (v1.0) catches **register
drift** (movie-trailer color grade, performative lighting, commercial
polish) but not **topical accuracy** (apparatus depicted matches the
narration's actual referent) or **period authenticity** (era-specific
elements hold against the referenced historical period). The water-in-
rat-anchor render scored `strong` on Documentary integrity at the time
of audit because the register was correct — calm-observational, single-
source lighting, restrained palette. The apparatus issue surfaced
later via cross-AI Gemini consult and human craft instinct, not via
the rubric.

The calibration: make apparatus accuracy and period authenticity
first-class grading dimensions inside Documentary integrity. Future
audits of reenactment imagery — H#3 v3 resume post-EP1, future
behavioral-psychology episode reenactments — get apparatus and period
errors flagged at grading time, not after.

## Current Documentary integrity criterion (v1.0 — for reference)

```
### Documentary integrity
The render's coherence with the channel's documentary register —
calm-observational, not movie-trailer drift, not performative-ominous.
References hold against existing canonical content (K1 typography,
H#3 Skinner box hero shot, L1 multi-beat composite).
- pass: Calm-observational register throughout — single-source lighting, restrained palette without contemporary saturated grade, framing reads as observation rather than performance. Holds against H#3 Skinner box hero register.
- partial: Register coherent overall but one element drifts — a single dramatic light source, an unmotivated saturated accent, or a camera angle that tilts toward performance. Recoverable in one prompt iteration without restarting from scratch.
- fail: Register breaks — movie-trailer color grade (teal/orange), performative ominous lighting, decorative lens flares, or commercial-photography polish dominates. Reads as trying to sell rather than observe.
```

## Proposed revised Documentary integrity criterion (v1.1 draft)

```
### Documentary integrity
The render's coherence with the channel's documentary register across
three dimensions: register fidelity (calm-observational, not movie-
trailer drift, not performative-ominous); apparatus accuracy (depicted
apparatus matches the topical reality the narration references);
period authenticity (era-specific elements — clothing, instrumentation,
architecture, lighting style — hold to the referenced historical
period without anachronism). References hold against existing canonical
content (K1 typography, H#3 Skinner box hero shot, L1 multi-beat
composite).

Apparatus-accuracy examples: a 1930s Skinner box must show food-reward
conditioning apparatus (lever + food dispenser + conditioning chamber);
water mechanisms, water bottles, or modern lab equipment not part of
the documented experimental setup are accuracy failures even when
register is otherwise correct. Period-authenticity examples: a 1930s
laboratory scene must avoid post-1930s tooling, post-war architectural
elements, and contemporary clothing/grooming markers.

- pass: All three dimensions hold. Register calm-observational; apparatus accurate to the narration's topical referent; period elements consistent across clothing, instrumentation, architecture, lighting. Holds against H#3 Skinner box hero register.
- partial: Two of three hold; one element drifts — register coherent but one apparatus element doesn't match the topical referent (a water bottle in a food-reward context, a 1960s-era tool in a 1930s lab), OR one anachronistic period element (post-1930s clothing, a single contemporary instrument), OR a single register drift (unmotivated saturated accent, performance-tilted angle). Recoverable in one prompt iteration without restarting.
- fail: Two or more dimensions break — movie-trailer color grade combined with apparatus depiction wrong for the referenced topic; performative lighting combined with period authenticity collapse; OR a single dimension fails so completely that the render reads as unrelated to the narration's topic (apparatus depicts a different experiment entirely, or period shifts decades from the referenced era).
```

## What changed

1. **Definition extended** from one paragraph (~3 sentences) to two paragraphs (~7 sentences). First paragraph names the three dimensions explicitly. Second paragraph anchors apparatus and period accuracy with the water-in-rat-anchor exemplar (without naming it as such — keeps language general for future cases).

2. **Grading bullets restructured** as N-of-3 dimension checks. The water-in-rat-anchor render would now score `partial` at minimum (register fine, apparatus wrong — 2 of 3 hold), possibly `fail` depending on how the apparatus-wrongness was weighted.

3. **Length** — definition ~150 words, each bullet ~50 words. Within the authoring-tip's "longer than ~3 sentences risks dilution" guidance only if you count clauses generously; the bullets are 1-3 sentences each, dense but actionable.

## Open questions for Joseph

1. **Threshold question — single-dimension fail.** Draft says: "OR a single dimension fails so completely that the render reads as unrelated to the narration's topic." This makes apparatus-accuracy fail (water bottle in food-reward context) potentially a `fail` rather than `partial` if the apparatus depicted is *fundamentally* the wrong apparatus. Reasonable? Or should single-dimension failures always be `partial` and only 2+ dimensions get `fail`? The water-in-rat-anchor case is the test — if you'd grade it `fail`, the draft is correct; if you'd grade it `partial`, soften the bullet.

2. **Coverage question — register-drift-only renders.** A render with movie-trailer color grade but correct apparatus and period would currently score `fail` under v1.0 (register breaks). Under the draft, it scores `partial` (2 of 3 hold). Is that the right shift? Or should register breaks alone retain `fail` weight even when apparatus and period are accurate? Two readings: (a) Register is the channel's core documentary commitment, so register break alone = fail; (b) Three dimensions are equal, so it's 2-of-3 = partial. Draft assumes (b); (a) requires asymmetric weighting in the criterion.

3. **Scope question — does this apply to non-reenactment imagery?** Documentary integrity applies to all 5 concept types in front-matter. Apparatus accuracy and period authenticity are meaningful for `schematic_apparatus` and `surreal_subject` (and the rat-with-human-face territory); less clear for `latent_space` (abstract gradients, no apparatus to be accurate about) or `architectural_inhabitant` (period applies, apparatus doesn't). Should the criterion definition note this scoping, or trust the AI to grade "apparatus" as "N/A" when not applicable? Draft leaves it implicit — AI infers from the render content whether apparatus/period are gradable.

## Verification before integration

After Joseph integrates into `docs/AUDIT_RUBRICS_v1_0.md`, the
existing verification command from the rubric's own "How to use"
section catches:
- the 6 criteria still parse cleanly (count unchanged at 6 — this
  amendment doesn't add a new criterion, just extends the existing
  Documentary integrity one);
- all pass/partial/fail bullets still filled (count unchanged);
- footer-pollution check passes (no content after last H3).

```bash
cd projects/latent_systems/tool_build && python -c "
from rubric import load_active_rubric
r = load_active_rubric('../../..')
assert r is not None
print('criteria:', list(r['criteria'].keys()))
print('all bullets filled:', all(c['pass'] and c['partial'] and c['fail'] for c in r['criteria'].values()))
print('Documentary integrity definition length:', len(r['criteria']['Documentary integrity']['definition']))
"
```

Expected: 6 criteria including `Documentary integrity`; all bullets
filled; definition length ~700-1000 chars (up from ~300 chars in
v1.0; still well under the 1000-char footer-pollution sentinel).

## Sequencing

Workstream 1B authoring complete 2026-05-13 Day 1. Joseph review +
integration target: Day 2 morning, before F5 hero promotion work
begins. Per the SESSION_STARTER plan: "Must land before F5 so all
downstream verdict-derived artifacts inherit the sharpened criteria
(causal chain: rubric → verdict grading → hero state → F6 NOTES.md
drafts auto-drafted from verdict state via Claude API on Day 3)."

Post-integration: bank a line in `banked_items.md` "Rubric calibration
observations" section noting the amendment landed + the water-in-rat-
anchor case study + the H#3 v3 resume gating on the sharpened rubric.
