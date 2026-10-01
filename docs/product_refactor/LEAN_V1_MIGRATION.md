# Lean V1 migration

Existing state remains readable. Replace `cognize()` with `context()` plus a host-selected model call. Replace council and planner use with application orchestration unless the research package is intentionally enabled. Deprecated calls still work and warn.

Configuration adds `[features]`: `model_gateway`, `semantic_retrieval`, `learning`, and `research_cognition`. A rollback is the immutable tag `syune-full-cognitive-pre-lean`; state should be backed up before changing versions.
