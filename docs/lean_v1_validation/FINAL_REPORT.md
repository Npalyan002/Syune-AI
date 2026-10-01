# SYUNE v1 lean product validation

`SYUNE_LEAN_VALIDATION_STATUS = COMPLETE_WITH_RELEASE_BLOCKERS`

`RELEASE_DECISION = LEAN_V1_NEEDS_FIXES`

## Quality

| Metric | STRONG_RAG | LEAN_SYUNE |
|---|---:|---:|
| Retrieval recall | not established on the frozen lean dataset | not established |
| Retrieval precision | not established | not established |
| Context precision | not established | not established |
| Current equivalent task success | 0.570 (Phase 31, 200 tasks) | no valid lean-only treatment; the 0.550 Phase 31 condition included removed cognition |
| Abstention | not established for the lean-only treatment | not established |

Noninferiority: **FAIL — not established**. Existing Phase 31 model results cannot be relabeled as Lean SYUNE because that treatment included removed cognitive processing. No post-treatment threshold was substituted.

## Governance

- Authorization: **PASS in focused regression**. All principal, agent, organization, project, department, purpose, missing-principal and deny-precedence cases passed; observed violations: 0.
- Provenance: **FAIL**. Model-visible `ContextItem` has record ID and source ID but omits source origin, relevant timestamps and lineage. Required completeness is therefore below 100%.
- Temporal/version: **PASS in deterministic focused regression** for CURRENT, HISTORICAL, AS_OF, valid bounds, supersession and future rejection.
- Lifecycle: **PASS** for ACTIVE, ordinary archive exclusion, explicit archive access, FORGOTTEN, PURGED, tombstone persistence and no resurrection.
- Audit: **FAIL**. Context/authorization audit is process-local and empty after restart. Context events omit principal, purpose, returned IDs/content; there is no unified lifecycle/model/context reconstruction.

## Security

- Permission violations: 0 observed.
- Scope leaks: 0 observed across agent/project/department/organization/purpose cases.
- Secret leaks: 0 in the Phase 29 focused regression.
- Focused governance, retrieval, lifecycle, gateway and lean tests: **38 passed in 36.98s**.

## Performance

Frozen limits are in `PREREGISTRATION.md`.

| Records | Lean selective p50/p95/p99 ms | Lean broad p50/p95/p99 ms | STRONG_RAG selective p95 | STRONG_RAG broad p95 |
|---:|---:|---:|---:|---:|
| 1K | 45.162 / 54.795 / 54.795 | 35.001 / 36.781 / 36.781 | 19.024 | 7.010 |
| 10K | 64.328 / 69.598 / 69.598 | 103.302 / 140.272 / 140.272 | 41.265 | 106.209 |
| 100K | 66.251 / 68.385 / 68.385 | 772.883 / 1,131.687 / 1,131.687 | 41.345 | 1,118.342 |

Absolute scale limits pass. Paired Lean overhead fails the frozen combined absolute/percentage rule: selective p95 overhead is 35.771 ms/188.0% at 1K, 28.333 ms/68.7% at 10K, and 27.040 ms/65.4% at 100K. Broad overhead fails at 1K (29.771 ms/424.7%) and 10K (34.063 ms/32.1%), and passes at 100K (13.344 ms/1.2%). The default vector backend identifies itself as `local-linear`, not production ANN.

Model-inclusive: no new paid run was justified after hard release blockers. Prior Phase 31 same-provider evidence reports STRONG_RAG total p50/p95 1,515.982/1,988.838 ms. Its former production condition is not valid Lean evidence. Provider latency is therefore not used to hide local overhead.

## Storage

| Records | Memory bytes | Vector bytes | Combined bytes | Memory bytes/record |
|---:|---:|---:|---:|---:|
| 1K | 2,351,104 | 512,000 | 2,863,104 | 2,351.10 |
| 10K | 22,921,216 | 5,120,000 | 28,041,216 | 2,292.12 |
| 100K | 228,945,920 | 51,200,000 | 280,145,920 | 2,289.46 |

Growth is approximately linear and passes the 8 KiB/record preregistered ceiling. Persistent audit storage is zero because core audit is not persisted; this is a correctness failure, not a storage win. Gateway evidence remains separately persisted. Telemetry is off.

## Hot path

- Writes/context request: 0 entity, journal, lifecycle or lifecycle-event rows.
- Writes/model request: durable gateway transitions, reservation/reconciliation, attempt evidence and semantic commit by design; exact row count varies with retries.
- Writes/remember: source plus observation, lifecycle rows and change-journal rows.
- Writes/revision: no public lean revision operation exists.
- Writes/forget: one journal row plus one lifecycle-event row and lifecycle-state update.
- Experimental writes: 0 on the default path.

Measured context stages expose retrieval timings, but authorization, temporal filtering and context optimization are not separately timed, so the required complete stage breakdown is not available.

## Startup

- p50: 150.521 ms.
- p95: 159.825 ms.
- Repositories opened: 2.
- Services initialized: memory, study registry, index, retrieval, context, Study.
- Background jobs/threads: 0.
- Research/learning services: 0.
- Fresh state still creates four database files, including unused learning and execution compatibility stores.
- One unspaced repeated-open run hit `PermissionError` replacing `metadata/state.json.tmp`; 25 samples spaced by 50 ms had zero failures. This requires follow-up before release.

## Complexity reduction

- Full Cognitive: 4 repositories opened, 11 constructed services/indexes, 4 research/learning services.
- Lean Core: 2 repositories opened, 6 initialized services, 0 research/learning services.
- Repository reduction: 50% active-open reduction.
- Service reduction: 45.5% (11 to 6).
- Research-service reduction: 100%.
- Normal context write reduction: zero experimental writes.
- Configuration reduction: **none**; four feature flags were added.
- Runtime dependency reduction: **none**; MCP and PDF remain mandatory dependencies.

## Detachability

- MEMORY_ONLY: PARTIAL — low-level repository can be used directly; no named product mode.
- CONTEXT_ONLY: FAIL — context requires memory/retrieval and no mode exists.
- MODEL_GATEWAY_ONLY: PASS via direct `ModelGateway` construction, not the `Syune` facade.
- MEMORY_CONTEXT: PARTIAL — default runtime provides it but no explicit detachable mode.
- FULL_LEAN: PASS.

The requested five-mode product contract is not implemented.

## Installation

- Clean wheel build: PASS after installing the declared Hatchling build backend.
- Isolated environment install with dependencies: PASS.
- Initialize, remember, context, shutdown, restart, retrieve: PASS.
- Authorization/lifecycle durability: PASS in regression.
- Audit durability: FAIL; prior events disappear across restart.
- Revision workflow: FAIL; no public lean revision API.
- Quickstart: FAIL on this host because it requires `uv`, which is not installed or accompanied by an executable fallback.

## Public surface

- SDK: core methods exist, but `model` is untyped at the facade boundary, revision is absent, and authorization/forgotten results often appear as empty/not-found rather than distinct actionable typed outcomes.
- MCP: compatibility tests pass, but the surface remains cognition/council/plan-oriented and reports `L3_SUPERVISED_EXECUTIVE`; it does not expose the lean core API.
- API: remember/context/forget/history/audit/model are understandable without research terminology, except stale handshake/status claims.
- Deprecations: legacy calls warn and load lazily; default startup remains uncontaminated.

## Claims

Supported: governed persistent memory; principal/purpose-aware filtering; durable memory/security/lifecycle; deterministic temporal/version filtering; bounded context; provider-neutral reliable ModelGateway; zero learning/cognitive work on the default hot path.

Unsupported or insufficiently evidenced for v1: 100% provenance-bearing model-visible context, durable auditable context/model operations as one trace, production-scale ANN hybrid retrieval, lean quality noninferiority, complete detachability and a public revision workflow.

Unsupported current-surface claim remains: SDK/MCP status and handshake advertise `L3_SUPERVISED_EXECUTIVE`. Research modules themselves remain isolated.

## Regression

- Collected: 375.
- Last complete run on the unchanged product source: 375 passed, 0 failed, 0 skipped, 2 intentional deprecation warnings.
- This gate's focused post-refactor run: 38 passed, 0 failed.
- Confirmatory full rerun: no failures through 76%; runner transport closed before the final summary. No product code changed during this validation, so the prior complete 375-test result remains the valid regression evidence; the interrupted rerun is not represented as a pass.

## Release blockers

1. **RELEASE_BLOCKER — quality noninferiority is not established.** A frozen lean-only STRONG_RAG comparison must report recall, precision, context precision, task success and abstention.
2. **RELEASE_BLOCKER — audit completeness/durability fails.** Persist and correlate principal, purpose, request, authorization decisions, returned context, model/provider/cost/result and lifecycle actions without secrets.
3. **RELEASE_BLOCKER — context provenance completeness fails.** Return origin, relevant timestamps and lineage, without fabrication.
4. **RELEASE_BLOCKER — frozen latency-overhead rule fails.** Selective relative overhead fails at all sizes and absolute overhead exceeds 25 ms; broad overhead fails at 1K/10K.
5. **RELEASE_BLOCKER — required public workflows/surfaces are incomplete.** Public revision and five detachability modes are absent; MCP and handshake/status retain L3 cognitive positioning instead of the lean contract.
6. **RELEASE_BLOCKER — failure experience is not sufficiently actionable.** Unauthorized, missing-principal, wrong-purpose, forgotten and purged outcomes are frequently indistinguishable as empty/not-found results.
7. **RELEASE_BLOCKER — installation documentation is not portable as written.** Quickstart requires unavailable `uv` and does not demonstrate revision or durable audit because those workflows do not exist.
8. **POST_V1 — remove schema-v1 compatibility stores from fresh lean initialization through a safe migration.** They are not opened, but fresh state still creates learning/execution databases.
9. **POST_V1 — use/configure a production ANN backend for production-scale semantic retrieval.** The default local-linear backend is suitable for deterministic development evidence only.
10. **OPTIONAL — investigate the one observed rapid-open metadata replacement failure.** Reproduce under a dedicated Windows restart stress test before release.

## Final decision

**LEAN_V1_NEEDS_FIXES**

The lean architecture remains justified; this is not `NOT_JUSTIFIED`. Its memory, authorization, temporal/lifecycle controls, isolation, storage shape, startup and gateway are useful. It does not yet satisfy the evidence and product-contract requirements for v1.0 release preparation. The blocker list is finite and requires no new cognition, learning or research phase.
