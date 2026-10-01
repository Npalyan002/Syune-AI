# SYUNE Phase 07 validation

`PHASE_07_STATUS = PASS`

## Scope and files

Created `src/syune/learning/{__init__,model,errors,policy,store,service}.py`, its README, Phase 07 unit/integration/architecture tests, `scripts/benchmark_phase07.py`, this report, and `docs/PHASE_07_LEARNING_CONSOLIDATION.md`. Modified typed core IDs, Retrieval's narrow plasticity contract/scoring, architecture checks, and current documentation. The supplied root `SYUNE_PHASE_07_LEARNING_CONSOLIDATION.md` is included unchanged except removal of Markdown trailing spaces if required by `git diff --check`.

No dependency was added. SQLite, JSON, hashing, UUID5, timing, and statistics use the Python standard library. No ADR was created or modified.

## Demonstrations

- **Positive:** explicit positive outcome produced positive visible `learned_utility` and `learned_salience`; canonical Observation was unchanged.
- **Negative:** explicit negative outcome produced negative learned factors; the entity and provenance remained available.
- **Co-activation:** an explicit two-target signal strengthened only an existing canonical association and exposed positive `learned_association` during traversal.
- **Human feedback:** explicit HUMAN/USEFUL feedback mapped to bounded contextual utility/salience; no confidence changed.
- **Recall alone:** 100 recalls left overlay snapshots and ledger signal count byte-for-value identical.
- **Restart/idempotency:** store reopen preserved four signals and overlay; consolidation after restart applied zero proposals.
- **Rollback:** the selected batch returned overlay state to its pre-batch snapshot; signals remained and rollback audit was appended.
- **Retraction:** the notice reduced/flagged all provenance-linked derived entities while canonical records and extraction confidence remained intact.
- **Audit:** overlay targets trace to proposal ID, signal ID, batch ID, status, correlation/source/provenance carried by the immutable signal, and policy version in proposal/batch records.
- **Crash safety:** overlay writes, proposals, processed markers, batch, and audit commit in one SQLite transaction; failures roll back the transaction.

## Gates

- Full locked test suite: PASS (`.venv\Scripts\uv.exe run --locked pytest -q`: 93 tests).
- Phase 07 architecture boundary check: PASS.
- `git diff --check`: PASS.
- Benchmark: PASS for 100 / 1,000 / 10,000 signals.
- ART-DEP-AI files touched: none.
- MCP tools added or changed for learning: none.
- Remote/push: none.

## Benchmark results

| Signals | Append/s | Append p50/p95 ms | Consolidation p50/p95 ms | Lookup p95 ms | Retrieval overhead p50 ms |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 4,252 | 0.203 / 0.320 | 14.31 / 14.56 | 0.014 | 0.036 |
| 1,000 | 3,507 | 0.188 / 0.270 | 130.71 / 131.09 | 0.014 | 0.035 |
| 10,000 | 2,771 | 0.193 / 0.277 | 1,901.17 / 1,931.05 | 0.014 | 0.035 |

The benchmark environment was the local Windows host with Python 3.12.10. Proposal/audit persistence dominates large consolidation runs. No release threshold is claimed.

## Decisions, deviations, and limits

Decay and generated replay remain deferred. Co-activation v1 requires a canonical edge rather than inventing a learned semantic edge. Study lifecycle is not advanced to CONSOLIDATED because the Phase 07 overlay pass is not semantic truth verification. Rollback is an administrative Python API and is not exposed over MCP. No unresolved design decision or execution deviation blocks Phase 07.

## Exit checklist

- [x] Typed LearningSignal, LearningProposal, PlasticityState, and ConsolidationBatch contracts.
- [x] Durable versioned ledger and overlay with idempotency and restart persistence.
- [x] Deterministic bounded positive, negative, co-activation, human feedback, and retraction policy.
- [x] Canonical memory and factual confidence remain unchanged.
- [x] Atomic idempotent consolidation, audit, and rollback.
- [x] Narrow read-only Retrieval integration with visible learned factors.
- [x] Recall alone does not learn.
- [x] Resource bounds and performance instrumentation.
- [x] Benchmark at 100, 1,000, and 10,000 signals.
- [x] No provider/LLM, neural training, embedding/vector/graph DB, daemon, MCP learning tool, domain profile, Council, agent dispatch, Control Core, ART-DEP-AI, Executive, or Phase 08 work.
- [x] Tests, architecture check, documentation, local commit, clean tree, and no remote/push.
