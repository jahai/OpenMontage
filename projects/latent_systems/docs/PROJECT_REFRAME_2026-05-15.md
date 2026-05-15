# Project Reframe — 2026-05-15

**Decision banked**: EP1 reframed from production sprint to prototype/standard-building exercise. Architectural locks lifted. Ship-when-ready replaces ship-by-date.

## What changed

### Previous framing (pre-2026-05-15)
- May 23 ship date as gate (later: "completion criteria as gate" but May 23 still anchoring)
- Architecture v1.4 LOCKED
- EP1 architecture v1.4 LOCKED
- Project Briefing v1.3 LOCKED
- Script v3 RELEASED
- Sub-session C (B-roll planning) CLOSED
- Hero shots H#1-H#9 + K1 architected at single-block hero-shot scale (~20s blocks)
- Production model: assemble hero shots + sections, ship EP1 at current craft level

### New framing (2026-05-15)
- **EP1 is the prototype episode where the channel's production standard gets built.**
- Ship when the pipeline produces work to Joseph's craft standard — not before.
- May 23 ship date is released. No external deadline pressure.
- Architecture v1.4 is *living*, not locked. Same for EP1 architecture, script v3, B-roll plans.
- Hero shots can expand from single ~20s blocks to multi-minute mini-sequences if the editorial work justifies it.
- "Nolan / Oppenheimer level of detail and storytelling" is the target — every hero treated as its own short film with primary-source-grounded period accuracy.
- First test case: §3 Skinner sequence, treated as a 3-8 minute dramatized arc covering the documented 1928-1936 apparatus evolution (8 stages per Skinner's 1956 paper "A Case History in Scientific Method").

## Why this is the right call (editorial argument banked)

1. **Channel positioning depends on standard-setting.** Latent Systems' differentiator is documentary integrity + intellectual register. If the channel's first episode ships at "good enough" craft level, the channel's reference standard is "good enough" forever. Shipping at the standard Joseph actually wants establishes what the channel IS.

2. **The Perplexity 2026-05-15 research dossier opened up real narrative material.** The 8 documented stages of Skinner's apparatus evolution — pneumatic release box, runway-with-tilting-floor, accidental cumulative-recording discovery via spindle, final four-box configuration — read as a story arc. Pearl barley pellets bought from grocery stores. Brass pill machine for homemade pellets. The "discarded wooden disk" that became the food magazine. Crozier's physiology lab (not Emerson Hall psychology dept — outsider-in-wrong-building setup). Primary-source-grounded detail that no AI prompt-template would produce. Treating this material at hero-shot scale wastes the discovery.

3. **Pipeline learning compounds across episodes.** Building the Nolan-level workflow for EP1's heroes pays off for EP2-EP10. The investment isn't waste; it's the production capacity Joseph needs to deliver the channel he's actually trying to build.

4. **No ship-date dependency.** Joseph has no contractual launch obligation. The May 23 date was self-imposed momentum, not external commitment. Releasing it costs nothing externally.

## Real consequences (eyes-open)

1. **No first-week launch momentum.** First-week views are a real factor in YouTube algorithmic distribution. Shipping later than the audience window expects has real cost. Joseph has decided this cost is acceptable in exchange for craft standard.

2. **No calendar discipline forcing closure.** Without a ship date, perfectionism becomes a structural risk. Mitigation: explicit "completion criteria" document defining what "pipeline meets standard" means concretely, so closure is criterion-driven not date-driven. This document gets written after the Skinner sequence is complete (so the criteria are informed by actual production experience, not pre-production speculation).

3. **Indefinite sprint mode.** Joseph has stated "endless energy" and 72-hour window blocked for current push. Sustainability of this pace across what could be a months-long production is its own risk. Worth periodic honest check-ins (not by Joseph self-asking, but by AI partner asking) about pace and fatigue.

4. **Channel-level precedent set by H#3 propagates to all future heroes.** K1, H#5, H#9, all subsequent EP2-EP10 hero work inherits this standard. The decision isn't just about §3 — it's about the channel's production identity.

## What survives the reframe (still useful)

The Phase 3 sprint work that landed 2026-05-14 → 2026-05-15 remains valuable:
- `tool_build/` engineering substrate — audit pipeline, rubric system, rough-cut player, side-by-side comparison (when built), section sidecar
- `section_structure.yaml` v1.0 — still the canonical structural document (beats can expand from current ~5 per section to many per section, but the framework holds)
- Audit rubric v1.1 with sharpened Documentary integrity criterion — applies to every render at every level of ambition
- AD-5 Claude-identity commit-prevention discipline — still operative
- All committed sprint work pushed to jahai/OpenMontage durable

The work isn't waste under the new framing — it's infrastructure for the higher-standard production now planned.

## What gets reopened

Documents that were treated as locked and may now need amendment as Skinner sequence work progresses:
- `docs/EP1_STRUCTURAL_ARCHITECTURE_v1_4.md` — may need v1.5 amendment if §3 becomes multi-minute sequence
- `docs/CHANNEL_STRUCTURAL_ARCHITECTURE_v1_5.md` — may need amendment if "Nolan-level production model" becomes a channel staple
- `docs/LATENT_SYSTEMS_EP1_FINAL_SCRIPT_v3.md` — likely needs §3 rewrite with extended sequence + possibly dialogue
- `docs/EP1_BROLL_PLAN_v1.md` — §3 plan needs expansion to cover the 8 apparatus stages
- `docs/EP1_PROJECT_HANDOFF_v10.md` — likely needs v11 reflecting reframe
- Channel staple #10 (toolchain) — Higgsfield adoption already noted; may need formal amendment

These don't get amended pre-emptively. They get amended as the Skinner sequence work surfaces specific changes needed.

## First concrete next step (post-this-document)

Skinner sequence structure document — shot-by-shot lay-out of the 8-stage apparatus evolution as a dramatized arc. This is editorial work, not generation work. Output: a shot list / scene breakdown describing the sequence beat-by-beat with running time estimates, dramatic emphasis points, narration plan, and dialogue plan (if any).

Once that's drafted and Joseph approves, production design document, then reference acquisition, then Soul Character training, then generation.

## Reference dossier from Perplexity (banked)

The Perplexity Deep Research output landed 2026-05-15 (file uploaded to chat: `skinner-harvard-1928-1936-visual-dossier.md`) is the primary-source reference for the Skinner sequence. Key findings:
- Skinner 1928-1936: ~24-32 years old, dark hair parted side, no glasses confirmed for this era
- Likely business attire (shirt, tie, trousers) — lab coat NOT confirmed for physiology lab work
- Worked under W.J. Crozier in physiology, not in Emerson Hall psychology dept
- Pre-1932: predecessor biology buildings; post-1932: Biological Laboratories at 16 Divinity Avenue
- 8 documented apparatus stages (Skinner 1956 paper) → narrative arc material
- Recording instrument: Harvard Instruments Company kymograph (1928-1932), modified for cumulative recording 1930; NOT Esterline-Angus
- Food: pearl barley → homemade pellets via brass pill machine
- Early box (1930-1936) had NO: shock grid, signal lights, speaker, water bottle (these are post-1936 additions)
- Photographic record: B.F. Skinner Foundation, Harvard Archives, Smithsonian, Bjork 1993 biography (with photos), Lattal 2004 paper (Figure 9 = earliest widely reproduced lab photo, 1948 Indiana)

This dossier gets copied into the canonical project tree (likely `docs/reference/skinner_harvard_1928-1936_dossier.md`) for permanence.

## Decision authority

This reframe is Joseph's editorial call, made 2026-05-15 after Perplexity Deep Research dossier review and explicit consideration of A/B/C scope options (Joseph chose C: full Nolan production model). Banked as legitimate production-emerging discovery trigger per the operating framework's refinement-stop discipline (architectural changes allowed on discovery triggers; this qualifies).

Documentation discipline maintained per the operating framework's decision-deferral patterns: channel-aesthetic-shift consequential and mid-production major structural changes were appropriately surfaced for explicit consideration before commitment, not just executed on momentum.
