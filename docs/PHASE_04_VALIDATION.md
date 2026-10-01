# SYUNE Phase 04 validation

**Status:** PASS after final gates and local commit.

## Changes

Created: `src/syune/retrieval/{__init__,model,index,service}.py`, `tests/unit/test_retrieval.py`, `tests/integration/test_retrieval_restart.py`, `tests/architecture/test_phase04_boundaries.py`, `scripts/benchmark_phase04.py`, `docs/PHASE_04_RETRIEVAL_ASSOCIATIVE_ACTIVATION.md`, and this report. The supplied root `SYUNE_PHASE_04_RETRIEVAL_ASSOCIATIVE_ACTIVATION.md` was preexisting untracked input, committed unchanged.

Modified: `src/syune/memory/repository.py`, `src/syune/memory/sqlite_repository.py`, `src/syune/retrieval/README.md`, `tests/architecture/test_phase02_boundaries.py`, and `scripts/check_architecture.ps1`. `iter_entities()` is structural read-only enumeration for derivative index rebuilds. No new dependency, ADR, domain silo, or architecture deviation.

## Tests and demonstrations

- Full `uv run pytest`: 80 passed.
- Static architecture check: PASS.
- Lexical Observation seed activates associated Concept and Procedure with path/score/provenance explanation.
- Context-supported candidate outranks a strong lexical Claim distractor under documented weights.
- Two independent seed roots promote an existing neighbor through pattern completion; one root does not meet the threshold.
- Cycle and resource-limit tests terminate deterministically with edge/fanout truncation metadata.
- SQLite memory reopen plus index rebuild gives the same ordered IDs and scores; explicit sync indexes newly added memory.
- Repeated recall leaves durable entity and Association rows byte-for-byte unchanged.
- Injected degraded materialization produces an explicit error.

## Reproducible synthetic benchmark

Command: `uv run python scripts/benchmark_phase04.py` (five repeats; Windows 11 build 26200, Python 3.12.10). Values in milliseconds:

| Concepts | Index build | Exact p50/p95 | Lexical p50/p95 | Association p50/p95 | Full p50/p95 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 0.706 | 0.325/0.339 | 0.352/0.354 | 0.566/0.568 | 0.694/0.708 |
| 1,000 | 6.768 | 1.639/1.762 | 1.652/1.662 | 3.163/3.190 | 4.159/4.161 |
| 10,000 | 73.165 | 14.748/14.924 | 14.819/14.970 | 29.527/29.929 | 41.554/53.192 |

Dataset: one Source, N Concepts containing unique topic tokens, and N-1 chain Associations. No external corpus. In-memory direct-edge scanning is the likely scaling bottleneck; no arbitrary latency PASS threshold is claimed.

## Decisions, limits, and exit criteria

No ADR created or modified. Unresolved tuning choices include calibrated weights, production index/storage, broader relevance evaluations, and source materialization integration policy. These are deferred; none blocks the v1 baseline. Retrieval remains read-only and transient. ART-DEP-AI was untouched; Phase 05 was not started.

- [x] Typed cue/request/candidate/result and deterministic exact-ID, source/provenance, and lexical seeds.
- [x] Rebuildable versioned derivative index, explicit sync, and association graph view.
- [x] Bounded transient spreading activation, cycle protection, and depth/fanout/edge/candidate controls.
- [x] Salience, context, confidence, recency, provenance, and score decomposition.
- [x] Existing-only pattern completion and bounded working-memory selection.
- [x] Entity types and provenance preserved; Observation remains non-epistemic.
- [x] Degraded materialization surfaced when the injected checker reports it.
- [x] Deterministic order/score, restart/rebuild, no durable mutation, and performance instrumentation.
- [x] Synthetic benchmark baseline recorded; no forbidden provider, embedding, vector/graph DB, MCP, agent, Executive, or long-term learning behavior.
- [x] Tests, architecture check, required docs, local commit, clean tree, and no remote/push.
- [x] ART-DEP-AI untouched; Phase 05 not started.
