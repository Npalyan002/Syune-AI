> Historical baseline applicability (Phase 14): This v001 document preserves its original decisions. Current implementation status and superseding phase decisions are recorded in [Phase 14](PHASE_14_SYSTEM_HARDENING_E2E.md) and [release readiness](SYUNE_RELEASE_READINESS_v1.md). Phase 13 authorizes externally approved L3 local sandbox execution; MCP remains L1. The old roadmap label for Phase 14 is superseded by standalone system hardening. Legacy migration remains deferred. All shared-memory, epistemic and authority invariants remain binding.

# SYUNE — Study System

Version: v001 / Baseline 0.1. Status: Phase 00 architecture freeze.
Authority: [Blueprint](SYUNE_BLUEPRINT_v001.md), [Constitution](SYUNE_CONSTITUTION_v001.md), and root Phase 00 specification.
Current mode: L1 ADVISORY.

## Lifecycle

DISCOVERED → REGISTERED → PARSING → PERCEIVED → UNDERSTOOD → ENCODED → CONSOLIDATING → CONSOLIDATED → VERIFIED. Exceptional/side states: FAILED, REJECTED, RETRACTED.

Blueprint verbs DISCOVER, REGISTER, FINGERPRINT, PERCEIVE/PARSE, UNDERSTAND, ENCODE, BUILD ASSOCIATIONS, CONSOLIDATE, VERIFY describe operations. FINGERPRINT and BUILD ASSOCIATIONS are not additional registry states.

Whole-source hash detects exact duplicate content; section/block fingerprints identify changes. Stable source_id and source_version_id preserve identity/history across rename, move, and revision. Checkpointed study_job_id permits resume. Retry must not duplicate durable memories. Status and errors are queryable and auditable. New versions do not erase old history. Derived provenance remains traceable after consolidation or source retraction. SYUNE-LIBRARY is read-only from Study's perspective; ingestion never implicitly deletes raw sources. Parser/runtime design is deferred. See [Event Model](SYUNE_EVENT_MODEL_v001.md) and [Evals](SYUNE_EVALS_v001.md).
