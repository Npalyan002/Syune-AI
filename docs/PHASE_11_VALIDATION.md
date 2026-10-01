# SYUNE Phase 11 validation

`PHASE_11_STATUS = PASS`

## Implementation

Added the typed `syune.council` contracts, snapshot identity, sequential Council service, structural analyzer, advisory synthesizer, typed errors, tests, benchmark, documentation, and architecture rules. No dependency, provider, database, migration, external tool, or ADR was added.

## Demonstrations

- Explicit CREATIVE, GENERAL, and RESEARCH members run through the same `CognitiveService` over one base request.
- Stable input and state reproduce member evidence, agreements, disagreements, gaps, minority insights, synthesis, and typed IDs; runtime timings are diagnostic only.
- Profile overlays produce visible evidence selection and response emphasis differences while overlapping evidence and sources produce explicit convergence records.
- Evidence selected by only one profile remains visible as a minority insight.
- The same unresolved missing canonical link reported by multiple members becomes a common gap.
- Conflicting canonical relations remain a substantive evidence-driven disagreement with no winner, and canonical confidence is unchanged.
- Caption, transcript, and text Observations retain source IDs and exact region/time locators in shared memory; Council evidence preserves their canonical entity and source references.
- A synthetic member failure remains explicit while other results are retained.
- Unknown profiles fail with a typed invalid-profile error; incompatible profiles retain the distinct typed incompatibility error.
- Mutation injected during a member run is detected by before/after snapshot comparison and fails with `SHARED_STATE_MISMATCH`.
- Aggregate budget exhaustion marks remaining members `NOT_RUN` and returns LIMIT_REACHED. Request limits above the Council ceilings are clipped and reported.
- Memory entities/associations, retrieval entries, learned overlay rows, and profile fingerprints are byte-for-byte structurally equal before and after Council execution. No LearningSignal is emitted.

## Benchmark

Five deterministic sequential runs per case on Windows/Python 3.12. Memory sizes include 100, 1,000, and 10,000 entities; Council sizes include 2, 3, and 6 profiles. Times are milliseconds.

| Entities | Members | Total p50 | Total p95 | Member execution p50 | Analysis p50 | Synthesis p50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 2 | 23.24 | 24.01 | 18.57 | 0.69 | 0.03 |
| 100 | 3 | 32.98 | 34.60 | 28.08 | 0.94 | 0.03 |
| 100 | 6 | 58.70 | 59.45 | 53.64 | 1.20 | 0.03 |
| 1,000 | 2 | 104.46 | 105.63 | 72.59 | 0.63 | 0.03 |
| 1,000 | 3 | 140.25 | 141.94 | 108.49 | 0.94 | 0.03 |
| 1,000 | 6 | 247.25 | 250.24 | 214.94 | 1.34 | 0.03 |
| 10,000 | 2 | 953.26 | 978.33 | 632.38 | 0.67 | 0.03 |
| 10,000 | 3 | 1,261.46 | 1,285.98 | 954.32 | 1.04 | 0.03 |
| 10,000 | 6 | 2,180.05 | 2,233.25 | 1,870.04 | 1.30 | 0.03 |

Council analysis and synthesis remain small relative to member cognition. Full structural snapshot hashing is intentionally visible in total time and dominates non-member overhead at 10,000 entities. Measurements establish a local baseline rather than a release SLA.

## Gates

- Focused Council tests: PASS (`5 passed`).
- Full locked pytest suite: PASS (`116 passed in 16.31s`).
- Phase 11 architecture check: PASS.
- `git diff --check`: PASS.
- Full diff review: PASS.
- Local commit and clean worktree: PASS.
- Remote/push: none.

## Deviations and decisions

V1 executes members sequentially as permitted by the brief. The repositories do not expose one source materialization generation, so the snapshot marks that field `NOT_EXPOSED` while fingerprinting every available shared-state surface. Council results are intentionally transient and advisory. No unresolved decision blocks the phase.

## Exit checklist

- [x] Typed contracts, IDs, explicit distinct membership, lifecycle, and typed failures.
- [x] Shared Memory/Retrieval/Learning/Profile snapshot and drift detection.
- [x] Deterministic evidence map, agreement, disagreement, minority, common-gap, and synthesis logic.
- [x] No truth voting, confidence rewrite, Study, Learning, action, agent, Control Core, provider, or ART-DEP-AI integration.
- [x] Multimodal canonical evidence and provenance preservation.
- [x] Failure isolation and global Council budgets.
- [x] Determinism, neutrality, benchmark, tests, docs, and architecture enforcement.
