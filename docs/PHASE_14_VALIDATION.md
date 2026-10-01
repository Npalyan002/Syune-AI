# Phase 14 validation

**Result: PASS within the standalone local reference scope. Release readiness: READY_WITH_LIMITATIONS.**

Baseline: main at d69b2c9; initial working tree clean. Locked baseline suite: 138 passed. Final full suite: **203 passed**, zero failures/skips. All 15 typed eval categories pass. Architecture checker: PASS. Diff whitespace check: PASS. The enclosing local commit and clean working tree are closing postconditions checked after commit; no push or remote creation.

## Correctness and failure evidence

| Area | Result and evidence |
| --- | --- |
| Golden E2E | PASS: real Study, shared memory, Retrieval, Cognitive Core, Council, explicit goal, L2 draft, external test-host sandbox binding/approval, verified L3 receipt. `tests/phase14/test_e2e.py`. No hidden LearningSignal. |
| Failure E2E | PASS: exact APR-004 version mismatch, zero adapter calls; subsequent valid execution healthy. |
| Provenance | PASS: versioned `evals/phase14_e2e_proof_v1.json` links receipt/proposal/step/goal/Cognitive/Council evidence/Observation/PerceivedSegment/revision/SHA-256. Two source-relative text ranges are distinct. |
| Memory | PASS: audit of five canonical entities, one relation, one revision, two segments, zero overlays and one execution record; references/materialization/schema checked. Restart and corrupted indexed identity regressions pass. |
| Duplicate ingestion | PASS: same/renamed text, image, audio, video and PDF; changed source revisions retain lineage. No duplicate canonical observations/traces on idempotent paths. Repeated identical paragraphs retain distinct locators. |
| Retrieval quality | PASS: three curated cues (Amber, safety, verification), two relevant observations, unrelated distractor and absent cue. Recall@2=1, Precision@2=1, MRR=1, coverage=1, false-positive rate=0; absent cue empty. Alternatives are the two supported observations, no semantic equivalence outside this fixture is claimed. |
| Learning | PASS: 1,000 explicit positive updates, diminishing increments bounded at 0.5; negative, source-retraction and rollback produce 1,002 audited signals. Canonical state unchanged, retrieval stable. Out-of-order overlapping rollback rejected. |
| Cognition | PASS: direct/multihop/convergent support, conflicts, missing links, insufficient evidence, source overlap, uncertainty and supported IDs; deterministic semantic result. Existing integration/unit cases plus Phase 14 checks. |
| Profiles | PASS: all six profiles share canonical memory/provenance; at least three distinct inference/attention structures on the same fixture. Differences measured structurally, not by profile names. |
| Multimodal | PASS: PDF/image/audio/video/text coexist in one memory; textual bridge query recalls each source, with distinct locators/provenance. Fake provider unavailable/partial failures preserve explicit component state. |
| Council | PASS: convergence, evidence/profile disagreement, minority-supported findings, common gaps, member attribution and single-member PARTIAL failure; no truth winner or synthetic replacement. `tests/integration/test_council.py`. |
| Planning | PASS: goal/constraint/dependency/cycle/checkpoint/risk/budget/approval/gap checks; contradictory/impossible/ambiguous/prerequisite/high-risk/unknown-capability/disagreement cases preserve blockers and zero effects. Executive unit/integration suites retained. |
| Approval and L2/L3 | PASS: missing, stale, revoked, future, version/parameter/target/scope/risk/budget drift block. Blocked plan rejected. No runtime token minting; authority supplied externally. |
| Idempotency and recovery | PASS: one invocation on repeated approval; invalid approval cannot replay. Generic post-effect errors remain UNKNOWN_OUTCOME; failed-final work cannot repeat. Corrupted persisted keys cannot hide an existing execution identity. |
| Crash injection | PASS: after gate, after effect, before verification, after verification, after receipt commit. New store/adapter reconciles without invocation; absent/unverified state remains uncertain. Test-only interrupted-control-flow model. |
| Stop and circuit | PASS: emergency stop after first step prevents second; repeated capability failures open circuit and later actions block. |
| Corruption/schema | PASS: malformed memory row, missing entity, invalid registry/hash/perception run/execution data, overlay and index identity; explicit failure, unaffected state retained. Supported current schemas and exact prior Study/Execution version-0 adoption tested; no semantic repair. |
| Restart | PASS: two fresh processes reproduce identical structured semantic cognition; current stores round-trip. Providers with nondeterministic outputs are outside this guarantee. |
| Stress/concurrency | PASS: 160 concurrent read operations; 100 reads with 20 explicit Learning writes; 100 reads with three Study writes and explicit index sync; duplicate execution-claim rejection and repeated Council/planning/metadata writes. Separate connections only. |
| Resource limits | PASS: source bytes, PDF pages, WAV duration, parser/provider segments/derived bytes/cooperative deadline; existing retrieval/Council/plan budgets; execution action/retry/write/wall caps; sandbox file/aggregate storage ceilings. Unknown compressed duration and noncooperative callbacks remain limitations. |
| Security | PASS: runtime AST/dependency checks for generic eval/exec/process/network authority, forbidden legacy coupling and runtime approval minting; traversal/ADS checks, scoped approval and exception-message redaction regressions. Explicit benchmark subprocesses are test orchestration only. |
| Health and regression | PASS: typed HEALTHY/DEGRADED/UNHEALTHY distinct from release readiness, fail-closed case runner, versioned baseline with platform-aware coarse tolerances and strict error/test-count flags. |

## Consolidated benchmark matrix

Environment: Python 3.12.10; Windows-11-10.0.26200-SP0. Values below are milliseconds. Synthetic local fixtures; 20 observations per small-pipeline operation. E2E service sum excludes host review delay and fixture setup. Execution overhead includes durable metadata and verification, excludes adapter invocation; verification is also displayed separately, so do not add it twice.

| Subsystem / operation | Scale | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: |
| Study_duplicate | 20 samples | 179.3249 | 330.6079 | 407.1921 |
| Retrieval | 20 samples | 1.5299 | 2.2856 | 2.8972 |
| Cognition | 20 samples | 3.4256 | 5.2203 | 5.3960 |
| Council | 20 samples | 11.6711 | 16.5677 | 18.2839 |
| Planning | 20 samples | 0.6435 | 0.8446 | 0.8957 |
| Execution_gate | 20 samples | 0.0129 | 0.0169 | 0.0223 |
| Capability | 20 samples | 5.0243 | 6.1855 | 6.2559 |
| Execution_overhead | 20 samples | 404.7010 | 779.5916 | 885.4227 |
| Verification | 20 samples | 4.2583 | 5.9018 | 12.2435 |
| E2E_service_sum | 20 samples | 426.3678 | 803.8159 | 907.2082 |
| Learning consolidation | 100 signals, 3 samples | 20.40 | 23.12 | not separately recorded |
| Learning consolidation | 1,000 signals, 3 samples | 137.83 | 176.90 | not separately recorded |
| Learning consolidation | 10,000 signals, 3 samples | 2029.64 | 2115.63 | not separately recorded |

Subsystem-process RSS: 43,454,464 to 60,911,616 bytes; peak 146,296,832. CPU delta 21.92s. Per-operation heap/DB allocations were not independently instrumented. Sandbox artifacts are capped at 1 MB/file and 10 MB/root.

## Memory growth and retrieval scaling

| Entities | Build ms | Index ms | Warm p50/p95/p99 ms | DB bytes | Index text bytes | RSS bytes | Open/rebuild ms |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 100 | 783.17 | 4.28 | 0.6375/0.6766/0.6910 | 147,456 | 1,212 | 45,113,344 | 18.81/4.47 |
| 1,000 | 778.36 | 35.35 | 0.6325/0.6751/0.6999 | 1,126,400 | 12,912 | 48,111,616 | 16.71/52.43 |
| 10,000 | 3354.17 | 440.87 | 0.6252/0.7044/0.8010 | 10,964,992 | 138,912 | 61,030,400 | 28.15/525.85 |
| 50,000 | 20977.65 | 2774.22 | 0.6831/0.8541/0.8697 | 54,685,696 | 738,912 | 113,917,952 | 33.17/2989.03 |
| 100,000 | 55429.76 | 5980.86 | 0.7667/0.8006/0.8049 | 109,379,584 | 1,488,912 | 180,215,808 | 19.15/6368.24 |

Index text bytes measure indexed text only, not full Python index/cache heap size. RSS is the Windows process working set. Full raw CPU/peak/handle samples are in the scale JSON. Query is deliberately selective; flat warm recall does not imply broad-query constant time.

| Entities | Cognition p50 ms | Council p50 ms | Planning p50 ms |
| ---: | ---: | ---: | ---: |
| 100 | 3.002 | 35.763 | 0.423 |
| 1,000 | 3.064 | 303.612 | 0.430 |
| 10,000 | 3.480 | 2998.180 | 0.544 |

First meaningful degradation: Council snapshots grow from ~36 ms at 100 to ~304 ms at 1,000 and ~3,000 ms at 10,000. Cognition/Council/planning were completed through 10,000; 50,000/100,000 measure memory/index/retrieval/restart only. Three Council and five cognitive samples are coarse observations. Learning consolidation increases from ~20 ms at 100 to ~2,030 ms at 10,000 explicit signals.

## Cold and warm paths

Five fresh interpreters open the same small persisted source fixture. Cold measurements include imports and process startup; the warm subsystem matrix excludes those costs. These cold values do not represent 100,000-entity startup (see rebuild column above).

| Run | Process total ms | Imports ms | Store open ms | Index ms | First recall ms | First cognition ms |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1796.59 | 327.88 | 2.68 | 0.59 | 1.46 | 3.70 |
| 2 | 1599.05 | 282.54 | 2.66 | 0.57 | 1.42 | 3.50 |
| 3 | 1519.75 | 254.21 | 2.24 | 0.51 | 1.35 | 2.97 |
| 4 | 1575.48 | 270.22 | 2.73 | 0.60 | 1.47 | 3.46 |
| 5 | 1761.26 | 327.87 | 2.98 | 0.58 | 1.54 | 3.47 |

## Final soak

PASS: 601.88 seconds, 123 full Study-to-verified-execution cycles, 0 errors. Every cycle audits provenance/memory, checks zero automatic learning, and replays without duplicate invocation. Final runtime identity/locator guards are included in this soak.

RSS 44,007,424 -> 47,218,688 bytes; peak 147,255,296; Windows handles 283 -> 282; CPU delta 27.78s. Periodic samples are in the versioned JSON. No accumulating handle/error trend was observed; this bounded connection-churn run is not an unbounded leak proof.

Whole-cycle p50/p95/p99: 4897.05/5165.27/5240.45 ms, including fixture setup/storage/cleanup. First-quarter median 4965.07, last-quarter median 4928.49 ms. Per-service timings are also recorded separately.

## Drift, limitations and deviations

The pre-change MATCH/DRIFT/DEPRECATED/UNUSED audit and final resolutions are in the implementation report. Approval/recovery, indexed identity and bounds drift was fixed; historical v001 prose received applicability banners. Placeholder adapters/contracts were identified rather than aggressively refactored. No dependencies or ADRs changed.

The release-readiness report enumerates unresolved production risks: host plan restoration, process-local circuit/rollback preimages, cooperative provider deadlines, unknown compressed-media duration, trusted sandbox filesystem, unsupported concurrency and limited synthetic quality coverage. These are explicit scope limits, not passed capabilities. No required local release-blocking gate remains failed. Existing prior-phase tests supply Council/planning/stop/budget cases instead of duplicating runtime or tests. The CLI is a script rather than python -m syune.evals. No optional repair framework was created. Performance measurements are local empirical baselines; subsystem/scale capture preceded the last persisted-identity guard, while the final full suite and soak validate the final runtime.

## Exit checklist

- [x] full unit/integration test suite passes
- [x] E2E golden path passes
- [x] E2E failure path passes
- [x] provenance chain verified end-to-end
- [x] memory integrity audit passes
- [x] duplicate ingestion/idempotency passes
- [x] retrieval quality eval exists
- [x] retrieval latency benchmark documented
- [x] large-memory scenario completed
- [x] learning stability eval passes
- [x] cognitive inference evals pass
- [x] profile differentiation evaluated
- [x] multimodal evals pass
- [x] Council agreement/disagreement evals pass
- [x] minority preservation confirmed
- [x] planning quality eval passes
- [x] impossible/blocked planning cases pass
- [x] no-approval execution blocks
- [x] stale/scope-drift approval blocks
- [x] idempotent execution does not duplicate side effect
- [x] UNKNOWN_OUTCOME handling verified
- [x] crash recovery verified
- [x] emergency stop verified
- [x] circuit breaker verified
- [x] corruption handling verified
- [x] schema compatibility checked
- [x] restart determinism checked
- [x] soak test completed
- [x] stress test completed
- [x] resource ceilings verified
- [x] security regression passes
- [x] architecture drift audit completed
- [x] system invariant checker passes
- [x] health/readiness model exists
- [x] regression baseline created
- [x] benchmark matrix created
- [x] `SYUNE_RELEASE_READINESS_v1.md` created
- [x] architecture check passes
- [x] `git diff --check` passes
- [x] ART-DEP-AI untouched
- [x] no migration work performed
- [x] no L4 behavior added
- [x] local commit created (closing postcondition verified after the enclosing commit)
- [x] working tree clean (closing postcondition verified after the enclosing commit)
- [x] no remote/push
- [x] PHASE 15 not started

## Changed files and evidence inventory

The enclosing commit contains only Phase 14 work. Created: eval Python contracts/runner/metrics/reporting/regression/invariant helper; five Phase 14 scripts; Phase 14 architecture and integration tests; three reports; versioned evidence/baseline JSON. Modified: approval/runtime/capability/execution persistence and verification; Memory decoding/schema; Study registry/service/errors; Perception router; Learning validation/rollback; Council error diagnostics; architecture checker and current/historical applicability documentation. Dependencies added: none. ADRs created/modified: none. The exact file list is in the enclosing local commit (`git show --stat HEAD`); its hash is obtained with `git rev-parse HEAD` after completion. No remote operation is part of this phase.
