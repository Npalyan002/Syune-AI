> Historical baseline applicability (Phase 14): This v001 document preserves its original decisions. Current implementation status and superseding phase decisions are recorded in [Phase 14](PHASE_14_SYSTEM_HARDENING_E2E.md) and [release readiness](SYUNE_RELEASE_READINESS_v1.md). Phase 13 authorizes externally approved L3 local sandbox execution; MCP remains L1. The old roadmap label for Phase 14 is superseded by standalone system hardening. Legacy migration remains deferred. All shared-memory, epistemic and authority invariants remain binding.

# SYUNE — Contracts

Version: v001 / Baseline 0.1. Status: Phase 00 architecture freeze.
Authority: [Blueprint](SYUNE_BLUEPRINT_v001.md), [Constitution](SYUNE_CONSTITUTION_v001.md), and root Phase 00 specification.
Current mode: L1 ADVISORY.

## Identity and version

All persistent objects use immutable opaque stable IDs, never path/title/name as primary identity. All persisted records carry schema_version. Important outputs carry created_at/updated_at where applicable. Derived records link to provenance/evidence. Migrations are explicit/versioned.

Required logical IDs: source_id, source_version_id, study_job_id, content_block_id, concept_id, episode_id, procedure_id, claim_id, evidence_id, association_id, memory_trace_id, provenance_id, cognitive_session_id, working_memory_id, retrieval_run_id, activation_run_id, learning_event_id, consolidation_run_id, world_model_revision_id, domain_profile_id. Future-only: plan_id, intention_id, action_proposal_id, outcome_id.

## Initial MCP semantics

- brain.health: report availability, version, and L1 ADVISORY mode.
- brain.recall: request memory-oriented retrieval; return stable references, provenance/evidence, uncertainty, and traceable retrieval context.
- brain.observe: accept/reject a policy-governed observation for later encoding with a traceable reference.
- brain.feedback: accept/reject traceable feedback associated with prior cognition/action context.
- brain.source_status: report known source/version lifecycle or explicit unknown.
- brain.study_status: report study job progress, checkpoints, errors, and consolidation state.

These are semantic contracts, not wire schemas or runtime. Errors are explicit. None grants agent dispatch or production mutation. Exact serialization/authentication is deferred.

## Provider gateway

Conceptual capabilities: text_reasoning, structured_extraction, embedding, vision_understanding, audio_transcription, multimodal_reasoning, reranking. Providers are replaceable processors, not SYUNE. Cognitive contracts cannot depend on a provider API shape. Adapters receive minimum required content.
