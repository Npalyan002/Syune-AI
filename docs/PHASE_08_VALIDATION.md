# SYUNE Phase 08 validation

`PHASE_08_STATUS = PASS`

## Scope and evidence

Phase 08 adds typed cognition contracts, `CognitiveService`/`CognitiveCycle`, structural `InferenceEngine`, bounded attention and WorkingContext, deterministic metacognition, advisory response candidates, instrumentation, benchmark, tests, and architecture checks. No dependency or ADR was added. ART-DEP-AI, MCP routing/tools, agents, Control Core, permissions, and Phase 09 were not changed.

## Required demonstrations

- **READY:** two provenance-linked observations connected through canonical associations produce a READY advisory result.
- **INSUFFICIENT_EVIDENCE:** an absent lexical cue produces an explicit gap and request-for-context response.
- **CONFLICTED:** a canonical `contradicted_by` relation produces a conflict record and conflict response.
- **Metacognitive limits:** focused assessments cover PARTIAL, DEGRADED_MEMORY, and LIMIT_REACHED with structured uncertainty metadata.
- **Learned relevance:** an explicit Phase 07 positive signal is consolidated; Retrieval exposes the learned factors and Attention reports `learned_relevance`. Cognition performs no learning write.
- **Bounded multi-hop:** cycle-safe BFS obeys configured depth, graph/path, and inference-record caps; supporting association IDs are exposed.
- **No learning from cognition:** twenty cycles leave the durable LearningLedger signal count and PlasticityOverlay snapshot unchanged.
- **Restart determinism:** reconstructing RetrievalService and CognitiveService over identical state returns the same semantic result for the same typed request ID. Timings are intentionally excluded.
- **Canonical integrity:** entity, association, confidence, and provenance snapshots are unchanged after cycles.
- **Provenance:** WorkingContext, inference records, response candidates, and result diagnostics retain source IDs.

## Benchmark

The synthetic harness runs simple, associative, conflict, multi-hop, and incomplete scenarios five times at 100, 1,000, and 10,000 memory entities. Results are local Windows/Python 3.12 measurements; no release threshold is claimed.

| Entities | Simple p50/p95 ms | Associative p50/p95 ms | Conflict p50/p95 ms | Multi-hop p50/p95 ms | Incomplete p50/p95 ms |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 4.55 / 20.33 | 1.13 / 1.17 | 1.03 / 1.05 | 1.30 / 1.30 | 0.07 / 0.10 |
| 1,000 | 11.73 / 11.83 | 1.13 / 1.21 | 1.04 / 1.04 | 1.31 / 1.34 | 0.07 / 0.09 |
| 10,000 | 95.18 / 108.72 | 1.11 / 1.14 | 1.01 / 1.02 | 1.31 / 1.34 | 0.07 / 0.09 |

## Gates

- Focused Phase 08 tests: PASS.
- Full locked test suite: PASS.
- Phase 08 architecture boundary check: PASS.
- `git diff --check`: PASS.
- Benchmark: PASS.
- Local commit and clean worktree: PASS.
- Push/remote creation: none.

## Exit checklist

- [x] Typed request/result, inference, assessment, response, and budget contracts.
- [x] Deterministic bounded cycle with existing RetrievalService.
- [x] Explainable attention and transient WorkingContext.
- [x] All required v1 structural inference categories.
- [x] Deterministic uncertainty, gap, conflict, and readiness assessment.
- [x] Advisory provenance-linked response candidates.
- [x] Read-only learned relevance and no-learning-from-cognition proof.
- [x] Canonical memory integrity and Observation non-epistemic boundary.
- [x] Instrumentation, benchmark, tests, documentation, and architecture checks.
- [x] No provider, Council, domain profile, Study, automatic LearningSignal, agent, Control Core, ART-DEP-AI, executive action, or Phase 09 work.
