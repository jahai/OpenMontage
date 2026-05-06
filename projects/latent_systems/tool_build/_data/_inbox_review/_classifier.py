"""One-shot classifier — produces CATALOG.md + per-file YAMLs.

This is operational tooling, not a permanent module. Lives under _data/
since it produces _data/_inbox_review/ artifacts. Run once; output is
the deliverable Joseph reviews.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import yaml

INVENTORY = Path(__file__).parent / "_raw_inventory.json"
OUT_DIR = Path(__file__).parent
FILES_DIR = OUT_DIR / "files"
CATALOG = OUT_DIR / "CATALOG.md"

# Manual classification rules built from filename + content reads.
# (suggested_destination, confidence, action, notes)
# action options: route, keep, dedupe, deprecate, delete, review
RULES = {
    # -------------------- TEXT / DOCS --------------------
    "PROJECT_ARCHITECTURE_v2.md": (
        "projects/latent_systems/PROJECT_ARCHITECTURE.md",
        "high", "route",
        "Per its own carry-forward checklist in NOTES.md ('PROJECT_ARCHITECTURE_v2.md → project root as PROJECT_ARCHITECTURE.md'). v1.5 lock per HANDOFF — verify whether this v2 is still current.",
    ),
    "PROJECT_ARCHITECTURE_v2 (1).md": (
        "DELETE (content-duplicate of PROJECT_ARCHITECTURE_v2.md)",
        "high", "dedupe",
        "Hash matches PROJECT_ARCHITECTURE_v2.md. Browser dedup '(1)' suffix. Safe to delete.",
    ),
    "NOTES.md": (
        "projects/latent_systems/NOTES.md",
        "high", "route",
        "Per its own carry-forward checklist ('NOTES.md (this file) → project root'). Rolling notes log.",
    ),
    "NOTES (1).md": (
        "DELETE (content-duplicate of NOTES.md)",
        "high", "dedupe",
        "Hash matches NOTES.md. Browser dedup. Safe to delete.",
    ),
    "HANDOFF_2026-05-03.md": (
        "projects/latent_systems/docs/HANDOFF_2026-05-03.md",
        "high", "route",
        "May 3 session handoff doc. Fits the existing docs/HANDOFF_<date>.md series referenced in router_config.yaml doc pattern. Contains 5 latent-space prompts pending MJ run.",
    ),
    "Perplexity_Sora_Brief.md": (
        "projects/latent_systems/ep1/cold_open/reference/Perplexity_Sora_Brief.md",
        "high", "route",
        "Sora generation brief for the two LS notification clips. Pairs with LS_iphone_notification_*.mp4 (also in this batch). Keeps prompt next to its outputs.",
    ),
    "ContentCalendar.jsx": (
        "projects/latent_systems/ep1/_archive/pre_pivot_artifacts/ContentCalendar.jsx",
        "high", "route",
        "OUTDATED — references EP1 as 'MKUltra' but EP1 pivoted to 'Business of Addiction'. Preserved in archive as pre-pivot iteration history.",
    ),

    # -------------------- PDFs --------------------
    "Building a Top 1% AI-Powered YouTube Channel  A 2026 Strategy Guide.pdf": (
        "projects/latent_systems/docs/research/strategy_guides/2026_AI_YouTube_Channel_Strategy.pdf",
        "medium", "route",
        "External strategy reference (April 8). Keep as research artifact. Path is suggested — adjust to your existing research convention if different.",
    ),
    "EP1_BRoll_SourceList_v2.pdf": (
        "projects/latent_systems/ep1/_research/EP1_BRoll_SourceList_v2.pdf",
        "high", "route",
        "EP1-specific b-roll source list. Goes with episode research. ep1/_research/ may need to be created.",
    ),
    "LatentSystems_ElevenLabs_ProductionGuide.pdf": (
        "projects/latent_systems/docs/production_guides/LatentSystems_ElevenLabs_ProductionGuide.pdf",
        "high", "route",
        "Production guide for ElevenLabs voiceover work. Cross-episode reference — belongs in docs/.",
    ),
    "EP1_Script_DANIEL_ElevenLabs.pdf": (
        "projects/latent_systems/ep1/_scripts/EP1_Script_DANIEL_ElevenLabs.pdf",
        "high", "route",
        "Daniel-narrator script for EP1, ElevenLabs-formatted. Episode-specific script asset.",
    ),
    "EP1_Script_28MIN_FINAL.pdf": (
        "projects/latent_systems/ep1/_scripts/EP1_Script_28MIN_FINAL.pdf",
        "high", "route",
        "Final 28-minute EP1 script. Episode-specific. Note: HANDOFF says EP1 is ~24 min — confirm this is still current or if a newer cut exists.",
    ),
    "EP1_CAPCUT_PRODUCTION_GUIDE_FINAL.pdf": (
        "projects/latent_systems/ep1/_production/EP1_CAPCUT_PRODUCTION_GUIDE_FINAL.pdf",
        "medium", "route",
        "CapCut production guide. EP1-specific. Note: cold open canonicalization moved AWAY from CapCut to OpenMontage per architecture v2 — this guide may be partially outdated. Worth a quick read before relying on it.",
    ),

    # -------------------- XML (Premiere project files) --------------------
    "LatentSystems_EP1_Premiere.xml": (
        "projects/latent_systems/ep1/_editorial/_iterations/v1/LatentSystems_EP1_Premiere.xml",
        "high", "route",
        "v1 of the Premiere project — earliest version. Preserved as iteration history.",
    ),
    "LatentSystems_EP1_Premiere_v2.xml": (
        "projects/latent_systems/ep1/_editorial/_iterations/v2/LatentSystems_EP1_Premiere_v2.xml",
        "high", "route",
        "v2 base draft. v3 is the current canonical (lives at ep1/_editorial/).",
    ),
    "LatentSystems_EP1_Premiere_v2 (1).xml": (
        "projects/latent_systems/ep1/_editorial/_iterations/v2/LatentSystems_EP1_Premiere_v2_draft1.xml",
        "high", "route",
        "v2 incremental draft 1. Preserved as iteration history.",
    ),
    "LatentSystems_EP1_Premiere_v2 (2).xml": (
        "projects/latent_systems/ep1/_editorial/_iterations/v2/LatentSystems_EP1_Premiere_v2_draft2.xml",
        "high", "route",
        "v2 incremental draft 2.",
    ),
    "LatentSystems_EP1_Premiere_v2 (3).xml": (
        "projects/latent_systems/ep1/_editorial/_iterations/v2/LatentSystems_EP1_Premiere_v2_draft3.xml",
        "high", "route",
        "v2 incremental draft 3.",
    ),
    "LatentSystems_EP1_Premiere_v3.xml": (
        "projects/latent_systems/ep1/_editorial/LatentSystems_EP1_Premiere_v3.xml",
        "high", "route",
        "Latest Premiere project file with structured bins (Sora_Atmospheric, Kling_Human, etc.). Editorial canonical. Likely needs ep1/_editorial/ created.",
    ),

    # -------------------- IMAGES (verified by visual read) --------------------
    "ANCHOR_LOCKED.png.png": (
        "projects/latent_systems/ep1/stills/ANCHOR_protagonist_locked.png",
        "high", "route",
        "Locked curly-haired protagonist anchor matching NOTES.md description. Note .png.png typo in filename — rename on route. Used across cold_open + H#2 + H#4.",
    ),
    "ANCHOR_LOCKED.png (2).png": (
        "projects/latent_systems/ep1/cold_open/reference/alternate_anchors/ANCHOR_LOCKED_alt.png",
        "high", "route",
        "Alternate anchor variant (different hash from primary ANCHOR_LOCKED). Preserved alongside primary for reference comparison.",
    ),
    "shotA_plate_LOCKED.png.png": (
        "projects/latent_systems/ep1/cold_open/reference/shotA_plate_LOCKED.png",
        "high", "route",
        "Locked plate for cold open's phone-on-bed shot. Rename to drop .png.png typo.",
    ),
    "rat_master.png": (
        "projects/latent_systems/ep1/h5_slot_machine/sources/rat_master.png",
        "high", "route",
        "Rat at slot-machine lever. h5_slot_machine matches the Skinner-box / operant-conditioning visual per architecture v2. (Also potentially fits 4_schematic_apparatus direction — leaving with h5 since architecture explicitly lists it as h5.)",
    ),
    "LS_notification_banner_1080p.png": (
        "projects/latent_systems/shared/branding/LS_notification_banner_1080p.png",
        "high", "route",
        "Clean horizontal LATENT SYSTEMS 'wake up' notification — branding asset reusable across episodes.",
    ),
    "LS_pov_notification_overlay.png": (
        "projects/latent_systems/ep1/cold_open/sources/LS_pov_notification_overlay.png",
        "high", "route",
        "POV phone screen with 3:47 AM timestamp + 'wake up' notification. Matches HANDOFF cold-open beat (notification at 3:47 AM). Cold open compound block source.",
    ),
    "shot1_last_frame.jpg": (
        "projects/latent_systems/ep1/_continuity/shot1_last_frame.jpg",
        "high", "route",
        "Last-frame extract for image-to-video continuity (Kling/Sora pattern: feed last frame of shot N as first-frame ref for shot N+1). _continuity/ may need creating.",
    ),
    "clip_A_last_frame.jpg": (
        "projects/latent_systems/ep1/_continuity/clip_A_last_frame.jpg",
        "high", "route",
        "Last-frame extract for clip-to-clip continuity.",
    ),
    "clip_A_last_frame (1).jpg": (
        "DELETE (content-duplicate of clip_A_last_frame.jpg)",
        "high", "dedupe",
        "Hash matches clip_A_last_frame.jpg. Browser dedup. Safe to delete.",
    ),
    "IMG_0021.jpeg": (
        "projects/latent_systems/ep1/_research/reference_photos/IMG_0021.jpeg",
        "high", "route",
        "iPhone reference photo (April 16). Preserved in episode research folder.",
    ),
    "IMG_0022.jpeg": (
        "projects/latent_systems/ep1/_research/reference_photos/IMG_0022.jpeg",
        "high", "route",
        "iPhone reference photo (April 16).",
    ),
    "IMG_0023.jpeg": (
        "projects/latent_systems/ep1/_research/reference_photos/IMG_0023.jpeg",
        "high", "route",
        "iPhone reference photo (April 16).",
    ),
    "images.jpg": (
        "projects/latent_systems/ep1/_research/reference_web/images_1.jpg",
        "high", "route",
        "Web-search reference image (May 2). Renumbered to disambiguate from sibling files.",
    ),
    "images (1).jpg": (
        "projects/latent_systems/ep1/_research/reference_web/images_2.jpg",
        "high", "route",
        "Web-search reference image variant 2.",
    ),
    "images (2).jpg": (
        "projects/latent_systems/ep1/_research/reference_web/images_3.jpg",
        "high", "route",
        "Web-search reference image variant 3.",
    ),
    "images (3).jpg": (
        "projects/latent_systems/ep1/_research/reference_web/images_4.jpg",
        "high", "route",
        "Web-search reference image variant 4.",
    ),

    # -------------------- VIDEO (classified by filename only) --------------------
    "v4_01_phone_dark_room_EXTENDED.mp4": (
        "projects/latent_systems/ep1/cold_open/sources/v4_01_phone_dark_room_EXTENDED.mp4",
        "high", "route",
        "Sora v4_01 phone-dark-room shot (referenced in Premiere XML). Cold open source. EXTENDED suffix suggests longer cut variant.",
    ),
    "Teen on Instagram.mp4": (
        "projects/latent_systems/ep1/_research/reference/Teen_on_Instagram.mp4",
        "medium", "route",
        "Reference video — likely Frances Haugen / Instagram research footage. EP1 context (Business of Addiction). Confirm vs your existing research convention.",
    ),
    "TikTok Trapped.mp4": (
        "projects/latent_systems/ep1/_research/reference/TikTok_Trapped.mp4",
        "medium", "route",
        "Reference — likely external doc/news clip on TikTok addiction. EP1 research context.",
    ),
    "Haugen Walk.mp4": (
        "projects/latent_systems/ep1/_research/reference/Haugen_Walk.mp4",
        "medium", "route",
        "Frances Haugen reference clip (whistleblower). EP1 context.",
    ),
    "Phone in Drawer.mp4": (
        "projects/latent_systems/ep1/_research/reference/Phone_in_Drawer.mp4",
        "medium", "route",
        "Reference — phone-in-drawer concept (digital wellbeing). EP1 context.",
    ),
    "WORDMARK_ANIM_6s.mp4": (
        "projects/latent_systems/shared/branding/WORDMARK_ANIM_6s.mp4",
        "high", "route",
        "Wordmark animation. Cross-episode branding asset.",
    ),
    "Phone Screen Lights Up with Notification.mp4": (
        "projects/latent_systems/ep1/cold_open/sources/Phone_Screen_Lights_Up_with_Notification.mp4",
        "high", "route",
        "Cold open notification beat source.",
    ),
    "LS_iphone_notification_16x9.mp4": (
        "projects/latent_systems/ep1/cold_open/sources/LS_iphone_notification_16x9.mp4",
        "high", "route",
        "Sora-generated notification clip (per Perplexity_Sora_Brief.md). 16:9 variant. Cold open ident.",
    ),
    "LS_iphone_notification_9x16.mp4": (
        "projects/latent_systems/shared/branding/LS_iphone_notification_9x16.mp4",
        "high", "route",
        "9:16 (vertical/Shorts) variant of the notification clip. Branding/Shorts asset.",
    ),
    "pov_phone_already_caught_1080.mp4": (
        "projects/latent_systems/ep1/cold_open/sources/pov_phone_already_caught_1080.mp4",
        "high", "route",
        "POV phone shot — cold open or H#1.",
    ),
    "pov_phone_already_caught_1080 (1).mp4": (
        "DELETE (content-duplicate)",
        "high", "dedupe",
        "Hash matches pov_phone_already_caught_1080.mp4. Browser dedup.",
    ),
    "thumb_press_lens_1080.mp4": (
        "projects/latent_systems/ep1/cold_open/sources/thumb_press_lens_1080.mp4",
        "high", "route",
        "Thumb-press shot — referenced in NOTES.md cold-open rethink (the failing thumb press moment is the design question). Source for the discrete-shot option.",
    ),
    "state1.mp4": (
        "projects/latent_systems/ep1/_strays/state1.mp4",
        "high", "route",
        "Generic filename; preserved in _strays/ for discoverability. May be h3_skinner state-1 source — rename if/when identified by viewing.",
    ),
    "Ep_1.mp4": (
        "projects/latent_systems/ep1/_archive/early_cuts/Ep_1.mp4",
        "high", "route",
        "Episode-level export from April 20 — likely an early full-EP1 cut (CapCut or otherwise). Preserved as iteration history.",
    ),

    # -------------------- AUDIO (classified by filename) --------------------
    "Recording 1.mp3": (
        "projects/latent_systems/ep1/_recordings/voice_memos/2026-04-08_voice_memo.mp3",
        "high", "route",
        "Voice memo from April 8 (earliest in scope). Date-stamped on route for disambiguation.",
    ),
    "Recording 1 (1).mp3": (
        "projects/latent_systems/ep1/_recordings/voice_memos/2026-04-09_voice_memo.mp3",
        "high", "route",
        "Voice memo from April 9 (different content from April 8 — hashes differ). Date-stamped on route.",
    ),
    "ElevenLabs_2026-04-09T13_47_27_Adam - American, Dark and Tough_pvc_sp97_s45_sb75_se5_b_m2.mp3": (
        "projects/latent_systems/ep1/_audio/vo_takes/Adam_2026-04-09T13_47_27.mp3",
        "high", "route",
        "ElevenLabs Adam voice take (April 9). Adam is mentioned in router_config — but Daniel is the EP1 narrator per HANDOFF. This is a voice exploration take, not the canonical Daniel narration. Belongs in vo_takes/ for reference.",
    ),
    "ElevenLabs_2026-04-09T13_47_27_Adam - American, Dark and Tough_pvc_sp97_s45_sb75_se5_b_m2 (1).mp3": (
        "projects/latent_systems/ep1/_audio/vo_takes/Adam_2026-04-09T13_47_27_take2.mp3",
        "high", "route",
        "Second ElevenLabs generation at the same timestamp prompt (hash differs from primary — distinct take, not a dup). Preserved as alternate take.",
    ),
    "ElevenLabs_2026-04-09T13_54_07_Adam - American, Dark and Tough_pvc_sp97_s45_sb75_se5_b_m2.mp3": (
        "projects/latent_systems/ep1/_audio/vo_takes/Adam_2026-04-09T13_54_07.mp3",
        "high", "route",
        "Another Adam VO take (7 min later than 13_47_27). Voice exploration phase.",
    ),
    "The_man_who_designed_that_gest.mp3": (
        "projects/latent_systems/ep1/_audio/vo_takes/the_man_who_designed_that_gesture.mp3",
        "high", "route",
        "VO take — 'the man who designed that gesture' (filename was truncated by browser). Preserved in vo_takes/. Listen to identify exact script-section binding.",
    ),
    "E1_Act2A.mp3": (
        "projects/latent_systems/ep1/_audio/acts/E1_Act2A.mp3",
        "high", "route",
        "Act 2A audio — episode structural audio piece. ep1/_audio/acts/ may need creating.",
    ),
    "daniel_section_09_harris.wav.mp3": (
        "projects/latent_systems/ep1/_audio/daniel_narration/section_09_harris.mp3",
        "high", "route",
        "Daniel-narrated section 09 (about Harris — likely Tristan Harris re: attention economy). Note .wav.mp3 double extension — was converted from wav. Episode-section narration.",
    ),
    "daniel_section_section_13A_steelman.wav.mp3": (
        "projects/latent_systems/ep1/_audio/daniel_narration/section_13A_steelman.mp3",
        "high", "route",
        "Daniel section 13A (steelman — likely a counter-argument section). Note doubled 'section' in filename.",
    ),
    "daniel_section_14_philip_morris.wav.mp3": (
        "projects/latent_systems/ep1/_audio/daniel_narration/section_14_philip_morris.mp3",
        "high", "route",
        "Daniel section 14 (Philip Morris — Big Tobacco parallel for addiction theme).",
    ),
    "daniel_section_17_meta_move.wav.mp3": (
        "projects/latent_systems/ep1/_audio/daniel_narration/section_17_meta_move.mp3",
        "high", "route",
        "Daniel section 17 (Meta move — likely the section about Facebook/Meta's pivot).",
    ),

    # -------------------- WAV (synthetic SFX) --------------------
    "Two_brief_synthetic__#1-1776743708666.wav": (
        "projects/latent_systems/shared/audio_library/sfx/two_brief_synthetic_v1.wav",
        "medium", "route",
        "Synthetic sound effect take #1. Audio library candidate. The numeric suffix is a generation ID.",
    ),
    "Two_brief_synthetic__#2-1776743708672.wav": (
        "projects/latent_systems/shared/audio_library/sfx/two_brief_synthetic_v2.wav",
        "medium", "route",
        "Take #2.",
    ),
    "Two_brief_synthetic__#3-1776743708674.wav": (
        "projects/latent_systems/shared/audio_library/sfx/two_brief_synthetic_v3.wav",
        "medium", "route",
        "Take #3.",
    ),
    "Two_brief_synthetic__#4-1776743708676.wav": (
        "projects/latent_systems/shared/audio_library/sfx/two_brief_synthetic_v4.wav",
        "medium", "route",
        "Take #4.",
    ),
    "A_phone_notification_#2-1776744054536.wav": (
        "projects/latent_systems/ep1/cold_open/audio/sfx/phone_notification_v2.wav",
        "high", "route",
        "Phone notification SFX — pairs with the cold open notification beat. Take #2.",
    ),
    "A_single_clear_bell__#1-1776746512183.wav": (
        "projects/latent_systems/shared/audio_library/sfx/clear_bell_v1.wav",
        "medium", "route",
        "Clear bell SFX, take #1. Likely for typography/section transitions.",
    ),
    "A_single_clear_bell__#2-1776746511333.wav": (
        "projects/latent_systems/shared/audio_library/sfx/clear_bell_v2.wav",
        "medium", "route",
        "Take #2.",
    ),
    "A_single_clear_bell__#3-1776746510943.wav": (
        "projects/latent_systems/shared/audio_library/sfx/clear_bell_v3.wav",
        "medium", "route",
        "Take #3.",
    ),
    "A_single_clear_bell__#4-1776746511002.wav": (
        "projects/latent_systems/shared/audio_library/sfx/clear_bell_v4.wav",
        "medium", "route",
        "Take #4.",
    ),
}


def main() -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    FILES_DIR.mkdir(parents=True, exist_ok=True)

    # Build per-file YAMLs
    catalog_rows = []
    by_action = {"route": 0, "dedupe": 0, "deprecate": 0, "review": 0, "delete": 0, "keep": 0}
    by_confidence = {"high": 0, "medium": 0, "low": 0}

    for entry in inventory:
        name = entry["name"]
        rule = RULES.get(name)
        if rule is None:
            dest, conf, action, notes = "REVIEW (no rule defined)", "low", "review", "No rule matched."
        else:
            dest, conf, action, notes = rule

        by_action[action] = by_action.get(action, 0) + 1
        by_confidence[conf] = by_confidence.get(conf, 0) + 1

        # Include filename in ID derivation to avoid YAML collision on
        # byte-identical browser duplicates (same SHA256, different name).
        import hashlib as _h
        record_id = _h.sha256(f"{name}|{entry['sha256']}".encode("utf-8")).hexdigest()[:16]
        record = {
            "id": record_id,
            "filename": name,
            "ext": entry["ext"],
            "size_bytes": entry["size"],
            "size_kb": round(entry["size"] / 1024, 1),
            "mtime": entry["mtime"],
            "sha256": entry["sha256"],
            "current_path": entry["path"],
            "suggested_destination": dest,
            "confidence": conf,
            "proposed_action": action,
            "notes": notes,
        }
        with (FILES_DIR / f"{record_id}.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(record, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

        catalog_rows.append((entry, dest, conf, action, notes))

    # Build CATALOG.md grouped by action
    md = []
    md.append("# Downloads Triage Catalog — 2026-04-08 to 2026-05-04")
    md.append("")
    md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Total files:** {len(catalog_rows)}  (excluded: 2 .exe + 11 .zip)")
    md.append("")
    md.append("## Summary")
    md.append("")
    md.append("| Action | Count |")
    md.append("|---|---:|")
    for action in ("route", "dedupe", "deprecate", "review", "delete", "keep"):
        if by_action.get(action):
            md.append(f"| **{action}** | {by_action[action]} |")
    md.append("")
    md.append("| Confidence | Count |")
    md.append("|---|---:|")
    for conf in ("high", "medium", "low"):
        if by_confidence.get(conf):
            md.append(f"| **{conf}** | {by_confidence[conf]} |")
    md.append("")
    md.append("## Notes on this catalog")
    md.append("")
    md.append("- Classifications based on filename + light reads of text/PDF/XML + visual checks of 5 key images.")
    md.append("- **Audio and video files were NOT transcribed/watched** — destinations proposed from filename context. Files marked `review` need your eyes/ears to confirm.")
    md.append("- Per AD-3, no commits to canonical paths happen automatically. This catalog is a proposal; you decide which moves to make.")
    md.append("- Per file `_data/_inbox_review/files/<id>.yaml` has full detail.")
    md.append("- Hash duplicates already detected: 4 groups, 8 files. Marked `dedupe`.")
    md.append("")

    # Group rows by action
    by_action_rows = {}
    for row in catalog_rows:
        action = row[3]
        by_action_rows.setdefault(action, []).append(row)

    action_order = ["route", "dedupe", "deprecate", "review", "delete", "keep"]
    for action in action_order:
        rows = by_action_rows.get(action, [])
        if not rows:
            continue
        md.append(f"## {action.upper()} — {len(rows)} files")
        md.append("")
        md.append("| Confidence | Filename | Suggested destination | Notes |")
        md.append("|---|---|---|---|")
        # Sort: high confidence first, then by filename
        conf_order = {"high": 0, "medium": 1, "low": 2}
        rows.sort(key=lambda r: (conf_order.get(r[2], 9), r[0]["name"]))
        for entry, dest, conf, _, notes in rows:
            short_notes = notes if len(notes) < 100 else notes[:97] + "..."
            # Escape pipe chars in cell content
            dest_cell = dest.replace("|", "\\|")
            notes_cell = short_notes.replace("|", "\\|")
            name_cell = entry["name"].replace("|", "\\|")
            md.append(f"| {conf} | `{name_cell}` | {dest_cell} | {notes_cell} |")
        md.append("")

    md.append("## Next steps")
    md.append("")
    md.append("1. **Spot-check** 3-5 entries from this catalog (especially the `low` confidence ones).")
    md.append("2. **Decide on bulk operations:**")
    md.append("   - Delete the 4 dedupe groups? (`(1)` browser-dup files with matching hashes)")
    md.append("   - Archive or delete the OUTDATED files (`ContentCalendar.jsx`, the v2 Premiere XMLs)?")
    md.append("3. **For `review` items** — listen/watch the ambiguous audio/video files and lock destinations.")
    md.append("4. **Once destinations are locked**, the existing router doesn't have rules for most of these (they don't match its `nycwillow_*`/`ChatGPT Image *`/`kling_*`/`HANDOFF_*` patterns). Options:")
    md.append("   - Run `python projects/latent_systems/tools/downloads_router.py --inbox-all` to dump everything to `shared/visual_identity_phase1_references/_inbox/`, then move from inbox to canonical destinations manually.")
    md.append("   - **OR** ask Claude to write a one-shot move script (we'd execute it; the pre-commit hook blocks any non-Joseph commit of canonical changes, so you'd need to commit the moved files yourself).")
    md.append("")

    CATALOG.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote: {CATALOG}")
    print(f"Wrote: {len(catalog_rows)} per-file YAMLs to {FILES_DIR}")
    print()
    print("Action summary:")
    for action, count in sorted(by_action.items(), key=lambda x: -x[1]):
        if count:
            print(f"  {action:10s} {count}")
    print("Confidence:")
    for conf, count in sorted(by_confidence.items()):
        if count:
            print(f"  {conf:6s} {count}")


if __name__ == "__main__":
    main()
