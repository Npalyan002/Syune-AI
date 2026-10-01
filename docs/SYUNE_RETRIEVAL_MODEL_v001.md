> Historical baseline applicability (Phase 14): This v001 document preserves its original decisions. Current implementation status and superseding phase decisions are recorded in [Phase 14](PHASE_14_SYSTEM_HARDENING_E2E.md) and [release readiness](SYUNE_RELEASE_READINESS_v1.md). Phase 13 authorizes externally approved L3 local sandbox execution; MCP remains L1. The old roadmap label for Phase 14 is superseded by standalone system hardening. Legacy migration remains deferred. All shared-memory, epistemic and authority invariants remain binding.

# SYUNE — Retrieval Model

Version: v001 / Baseline 0.1. Status: Phase 00 architecture freeze.
Authority: [Blueprint](SYUNE_BLUEPRINT_v001.md), [Constitution](SYUNE_CONSTITUTION_v001.md), and root Phase 00 specification.
Current mode: L1 ADVISORY.

## Retrieval contract

Retrieval selects from shared associative memory into working memory. RAG is one mechanism, not memory architecture. Candidate generation may combine lexical, vector, graph neighborhood, episodic, and procedural methods. Activation may combine associative spreading, salience, context, confidence/evidence, recency/temporal weighting, pattern completion, and domain bias. No algorithm, index, database, score, or weight is frozen here.

Creative, finance, systems, and strategy profiles may vary attention, retrieval weighting, spread, evidence threshold, exploration balance, reasoning strategy, evaluation, and uncertainty requirements. They cannot silo facts or hide provenance. Cross-domain activation is expected. Recall exposes provenance/evidence and uncertainty. Telemetry supports relevance, completeness, latency, provenance coverage, and shadow comparison with legacy RAG. See [Contracts](SYUNE_CONTRACTS_v001.md) and [Evals](SYUNE_EVALS_v001.md).
