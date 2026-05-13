"""Centralized constants for tool_build v1.

Single source of truth for values that must evolve together (e.g.,
discipline_version across walker + router_tail + dispatcher). Avoids the
"hardcoded in two files, will silently drift at first version bump"
failure mode flagged in the Days 5-9 review §4.4.
"""

from __future__ import annotations


# --- Discipline version (per spec Q2: 1.0 baseline; future 1.1, 1.2, ...) ---
# Walker writes DISCIPLINE_PRE_V1 for enumerated existing material.
# Router_tail and dispatcher write CURRENT_DISCIPLINE_VERSION for new
# post-v1 artifacts. When bumping discipline: change CURRENT_DISCIPLINE_VERSION
# here only; both modules import.
CURRENT_DISCIPLINE_VERSION = "1.0"
DISCIPLINE_PRE_V1 = "pre_v1"


# --- Schema version (state.db structure, NOT discipline_version above) ---
# When migrations 0005+ land, ADD them to this set. Walker + future
# schema_version-checking components read this to decide whether to
# refuse-to-run on unrecognized schema versions.
# Pattern from Day 3 review §4.2 (was deferred; landed with 0002 migration).
# 0003 added 2026-05-06 for Phase 2 Wave A audit consultation schema
# (audit_sessions, ai_consultations, audit_thumbnails + verdicts rebuild).
# 0004 added 2026-05-14 for Phase 3 substrate: notes_md_state (F6),
# cross_ai_captures expansion (F7), hero_promotions ALTER (F5 atomic
# action), audio_assets (rough-cut player Days 4-5).
SUPPORTED_SCHEMA_VERSIONS = frozenset({"0001", "0002", "0003", "0004"})
