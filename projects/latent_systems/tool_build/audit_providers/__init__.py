"""Audit-consultation provider adapters (Phase 2 Wave B).

Per phase2_design_notes.md v0.4 §3 + §7 Q1: per-provider adapters
in this directory, each minimal SDK wrapper. Wave B ships Anthropic
baseline; Perplexity (conditional Week 2), ChatGPT (Phase 3),
Gemini (Phase 3) added iteratively only when confirmed-needed.
Grok deferred indefinitely per role calibration.

Each provider exposes a `call_vision(...)` function returning a
VisionConsultationResponse with a uniform shape, so the audit
consultation orchestrator can fan out without provider-specific
branches in its body.
"""
