> Historical baseline applicability (Phase 14): This v001 document preserves its original decisions. Current implementation status and superseding phase decisions are recorded in [Phase 14](PHASE_14_SYSTEM_HARDENING_E2E.md) and [release readiness](SYUNE_RELEASE_READINESS_v1.md). Phase 13 authorizes externally approved L3 local sandbox execution; MCP remains L1. The old roadmap label for Phase 14 is superseded by standalone system hardening. Legacy migration remains deferred. All shared-memory, epistemic and authority invariants remain binding.

# SYUNE — Event Model

Version: v001 / Baseline 0.1. Status: Phase 00 architecture freeze.
Authority: [Blueprint](SYUNE_BLUEPRINT_v001.md), [Constitution](SYUNE_CONSTITUTION_v001.md), and root Phase 00 specification.
Current mode: L1 ADVISORY.

## Envelope

Events describe factual transitions, never hidden commands. Required envelope fields: event_id, event_type, event_version, occurred_at, producer, correlation_id, causation_id, entity_refs, payload. Important transitions are auditable/checkpointed. Serialization and transport are deferred.

## Namespaces

source.*, study.*, memory.*, retrieval.*, activation.*, learning.*, consolidation.*, world_model.*, domain.*, cognition.*, feedback.*, executive.* (future reserved), governance.* (reserved/limited initially), system.*.

## Frozen initial names

source.discovered, source.registered, source.duplicate_detected, source.version_detected, source.retracted.
study.started, study.checkpointed, study.parsed, study.perceived, study.understood, study.encoded, study.consolidation_started, study.consolidated, study.verified, study.failed.
memory.trace_created, memory.association_created, memory.trace_updated, memory.confidence_changed, memory.invalidated.
retrieval.started, retrieval.candidates_generated, retrieval.activation_completed, retrieval.completed, retrieval.failed.
learning.feedback_received, learning.update_proposed, learning.update_applied.
consolidation.started, consolidation.completed, consolidation.failed.
system.started, system.ready, system.degraded, system.stopped.

The names freeze vocabulary, not producers or an event bus. Executive events are not active in v001.
