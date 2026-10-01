> Historical baseline applicability (Phase 14): This v001 document preserves its original decisions. Current implementation status and superseding phase decisions are recorded in [Phase 14](PHASE_14_SYSTEM_HARDENING_E2E.md) and [release readiness](SYUNE_RELEASE_READINESS_v1.md). Phase 13 authorizes externally approved L3 local sandbox execution; MCP remains L1. The old roadmap label for Phase 14 is superseded by standalone system hardening. Legacy migration remains deferred. All shared-memory, epistemic and authority invariants remain binding.

# SYUNE — Evals

Version: v001 / Baseline 0.1. Status: Phase 00 architecture freeze.
Authority: [Blueprint](SYUNE_BLUEPRINT_v001.md), [Constitution](SYUNE_CONSTITUTION_v001.md), and root Phase 00 specification.
Current mode: L1 ADVISORY.

## Evaluation contract

Every future major subsystem requires objective reproducible benchmarks with datasets, expected outcomes, observed measures, and release thresholds before release. Phase 00 freezes families, not thresholds or tests. A subjective “smartness score” is insufficient.

- Study: duplicate detection accuracy, resume correctness, changed-section detection, extraction completeness, provenance completeness.
- Memory: identity integrity, association integrity, duplicate memory rate, source traceability, contradiction preservation.
- Retrieval: relevance, completeness, latency, evidence/provenance coverage, legacy RAG comparison.
- Learning/Consolidation: update correctness, unwanted forgetting/regression, provenance retention, confidence recalculation correctness.
- Future Executive: plan validity, policy compliance, unnecessary action rate, recovery/replanning, outcome learning.

Legacy retirement additionally requires equivalent/better retrieval quality, measured latency and token/compute cost, validated provenance quality, tested failure/rollback, and explicit production-owner approval. Shadow evaluation must preserve the existing production path.
