# Phase 14 system hardening

## Preflight (before implementation)

Baseline: `main`, `d69b2c9`; `git status --short` empty. The execution brief is locally excluded. Baseline locked suite: 138 passed in 21.60 seconds. The existing interpreter requires execution outside the filesystem sandbox; no dependency change is required.

Read: canonical architecture, contracts, governance, constitution, blueprint, memory, Study, retrieval, events, roadmap and eval documents; accepted ADRs 0001–0010; Phase 02–13 implementation/validation reports; test suite; benchmark scripts; architecture checker; persisted Memory, Study/perception, Learning and Execution definitions.

### Initial drift and unused-contract audit

| Subsystem | Classification | Finding |
| --- | --- | --- |
| Shared memory, retrieval, explicit learning | MATCH | One canonical store and separate operational overlays; no automatic learning path. |
| Cognition, profiles, Council | MATCH | Advisory structural inference; shared state; no majority truth authority. |
| Canonical current-mode prose | DRIFT | Frozen Phase 00 prose still says L1; later phase records authorize bounded L3. MCP itself remains L1. |
| Roadmap Phase 14 | DEPRECATED | Legacy consolidation label superseded by the supplied hardening brief. Migration remains deferred. |
| Execution approval/replay | DRIFT | Completed idempotency shortcut precedes approval verification. Needs revoked/missing-approval replay regression. |
| Rollback authorization | DRIFT | Only allow_rollback is checked; exact token/receipt binding requires regression and hardening. |
| Persisted state | DRIFT | Study/Execution lack explicit database versions; some decoded rows lack semantic validation. |
| Resource limits | DRIFT | Study reads entire bytes before size check; provider output collection is not incrementally bounded. |
| Execution faults | DRIFT | Generic post-effect exceptions become FAILED_FINAL and can be reattempted. Uncertainty must remain fail-closed. |
| Providers/domains/storage placeholder modules | UNUSED | Intentional boundaries; no runtime adapters to remove. |
| Artifact policy, compressed duration, provider deadlines | UNUSED | Typed obligations exceed available local implementation. Must distinguish limitations from tested enforcement. |
| Legacy shadow probe | DEPRECATED | Historical Phase 06 tool; excluded from this phase's commands. |

These findings were recorded before runtime changes. No constitutional invariant is being relaxed. No legacy repository was inspected or modified. No migration, production integration or Phase 15 work is authorized.

## Validation design

Use deterministic local fixtures, real runtime services, separate operational databases, explicit test-host approval, and a fixed file sandbox. Fault injection belongs in tests. Eval records must carry expectations, measured observations, safe evidence references, runtime metadata and correlation IDs. Runtime health is separate from release readiness. All exit gates remain mandatory; incomplete gates cannot be reported as passing.

## Implemented hardening

The eval package is a separate, explicit observer: typed cases, expectations, observations, failures, run metadata, reports, coarse regression comparison and a read-only system audit. It calls real services through test fixtures; runtime packages do not import evals. All 15 required categories are represented. Missing metrics, missing evidence, skipped cases and callback failures fail closed. Exception messages are reduced to class names in the eval runner, Council, capability error handling and verification.

Execution now verifies approval before replay, rejects future/expired/revoked/version/parameter/scope/risk/budget drift, rejects blocked plans, and binds rollback to a freshly valid original approval and receipt. Durable claims are atomic. Completed and uncertain claims cannot be overwritten; failed-final work cannot be reexecuted. Generic post-invocation exceptions preserve UNKNOWN_OUTCOME. Recovery verifies an existing attempt without invoking its capability. Gate/approval/goal/evidence/correlation metadata is committed before invocation and retained during reconciliation. Stored invocation fingerprints, indexed identities, versions and terminal receipt consistency are validated.

Memory validates decoded/indexed entity and association identities, current schema and missing tables. Study/Execution explicitly adopt the exact prior unversioned table layout as database version 1; unsupported schemas fail without guessing or record rewriting. Study validates hashes, counters and perception state. Learning rejects malformed/nonfinite overlay values and refuses rollback across a later overlapping batch; canonical confidence remains immutable. There is no general migration or repair framework.

Study reads at most the configured source ceiling plus one byte. Parser segments and incremental provider output are bounded. Provider identity/model/location participate in configuration fingerprints. Text perception locators now use absolute Unicode character offsets in the BOM-stripped source instead of block-relative offsets: identical paragraphs at different positions cannot collide. The new producer fingerprint is `study-parser-locators-v2`; existing records are preserved and idempotent historical ingestions are not silently rewritten. PDF locators remain page-based.

The file sandbox rejects absolute paths, traversal and Windows alternate data stream syntax, rechecks confinement on rollback, caps each file at 1 MB and aggregate storage at 10 MB, and bounds rollback preimages. Runtime budgets cap actions at 64, retries at 3, writes at 64 and cooperative wall time at 60 seconds. Per-operation gates may impose lower limits.

## E2E authority and provenance

`tests/phase14/scenario.py` performs real Study into one SQLite memory and registry, reads explicit Learning overlays, retrieves, runs Cognition and Council, then accepts an explicit test goal and creates an L2 draft. The external test host reviews that generic draft, records a version-2 sandbox plan, narrows its capability to a local UPDATE, removes explicitly completed prerequisites, adds the approval checkpoint and supplies a TEST-source token. This binding is fixture/host work, not autonomous runtime planning or approval. L2 alone remains unable to execute. An explicit synthetic support relation is fixture data, not an automatic factual assertion by Study.

The successful receipt links to the exact proposal, step, plan version, goal, cognitive/Council evidence, observations, perception segments, revision and SHA-256. `docs/evals/phase14_e2e_proof_v1.json` preserves one complete synthetic proof. The mismatched-version request fails APR-004 with zero adapter calls, followed by healthy valid execution. Neither path creates a LearningSignal. Explicit learning and rollback are tested separately.

## Observability and health

Existing service diagnostics expose Study phase/counters and safe error codes; Retrieval candidate/activation counts and timings; Learning batch IDs, counters and audit events; Cognition inference/gap/timing metadata; Council member IDs, failure classes and budget diagnostics; Planning constraint/gate/timing reasons; and Execution gate decisions, status, timings and receipts. The E2E fixture carries a correlation ID through supported request/context fields and the eval/proof envelope. Study and perception retain their own typed run/revision IDs linked by the proof envelope; trace IDs do not replace canonical identity. The project does not claim a distributed tracing backend or automatic private-content telemetry.

The invariant audit checks memory references and decoded identities, source/revision/materialization edges, perception run/segment linkage, overlay bounds, supplied plan/proposal references, execution identities and persisted approval audit fields. It returns HEALTHY/UNHEALTHY with safe diagnostic codes and counts. Health enums also allow DEGRADED. A valid fixture is HEALTHY; unavailable optional providers retain explicit component degradation. Release READY/READY_WITH_LIMITATIONS/BLOCKED is separate from runtime health and cognitive scores.

## Persistence, concurrency and failure model

Current schemas and restart round-trips are tested; compatibility adoption changes only the database version marker. Corruption tests use isolated copies and assert explicit failure and unaffected-data preservation. No semantic repair or deletion is attempted. Crash injection raises a test-only BaseException at gate/effect/metadata/verification/finalization boundaries, then closes/reopens the store with a fresh adapter. This models interrupted control flow, not OS power-loss or torn filesystem writes. Two genuinely fresh Python processes independently reproduce the same semantic cognitive result.

Read/read uses separate SQLite connections; read/explicit-Learning-write and Study-write/retrieval-read are covered. Retrieval refresh remains explicit through index.sync(). Atomic duplicate execution-claim rejection is tested. Shared-connection multithreaded writes, parallel Council writers, distributed workers and multi-process production dispatch are unsupported. Council members remain sequential. Repeated Council/planning/execution writes and explicit learning are exercised by tests, subsystem measurements and the soak.

## Drift resolution and remaining contracts

| Subsystem | Final classification | Resolution |
| --- | --- | --- |
| Shared memory / epistemic boundaries | MATCH | One canonical store; Study observations are not truth; runtime reads do not learn. |
| Retrieval / Learning / Cognition / profiles / Council | MATCH | Bounded explicit overlays and advisory structural inference; minority/gaps preserved. |
| L2 / L3 / approval / recovery | MATCH | Exact external approval, replay and rollback re-gating; uncertain outcomes require reconciliation. |
| Persistence and resource guards | MATCH | Current-schema validation, indexed identity checks, incremental ceilings and corruption failures. |
| Frozen v001 current-mode prose | DEPRECATED | Historical applicability banners link current Phase 13/14 scope; underlying invariants preserved. |
| Historical Phase 14 legacy roadmap label | DEPRECATED | Superseded by the supplied standalone hardening brief; migration deferred. |
| Placeholder provider/domain/storage interfaces | UNUSED | Intentional future boundaries; no unsafe removal/refactor. |
| General artifact policy / remote providers | UNUSED | Only the local sandbox storage ceiling and configured fake providers are proven. |
| Noncooperative provider deadline / compressed duration | UNUSED | Cooperative timing and known WAV duration enforced; hard preemption/unknown compressed duration not claimed. |

No severe unexplained architectural drift remains. No dependency or ADR was added or modified. The checker explicitly permits the eval observer while retaining runtime import/authority boundaries. Historical implementation/validation records remain intact.

## Reproduction and regression policy

See `scripts/README.md` for commands. `pytest` is the ordinary fast/unit/integration/E2E suite; scale and 600-second soak are explicit separate jobs. Full eval reporting additionally requires the completed performance files. All fixtures are local, synthetic and free of paid-provider/production dependencies. The installed Windows interpreter required execution outside the tool filesystem sandbox; the locked environment and dependency versions were unchanged. PowerShell architecture validation uses a process-only ExecutionPolicy Bypass because local script execution is otherwise disabled.

Versioned evidence lives under `docs/evals/`. The regression baseline contains test count, latency, memory/DB size and error count. Compare only equivalent platform/workload/sample settings. Flag a 50% worsening with a 5-unit absolute noise floor for performance/size metrics; test-count decreases and any error-count increase are strict flags. Missing metrics or a different platform require review/new comparable measurements. This is a coarse local regression policy, not a production SLO. Nearest-rank empirical percentiles from 3/5/20 samples are reported honestly; they do not estimate production tail distributions.
