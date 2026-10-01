# SYUNE release readiness v1

**Result: READY_WITH_LIMITATIONS for the standalone local reference implementation.** This is a Phase 14 engineering assessment, not production deployment authorization or cognitive truth certification. Runtime health for the audited golden fixture is HEALTHY. All required Phase 14 release-blocking correctness and authority gates pass; closing local Git checks are performed after the validation commit.

The architecture preserves one shared memory, explicit Learning, advisory Cognition/profiles/Council, bounded L2 plans and exact externally approved L3 local sandbox execution. MCP stays L1. Council consensus never becomes truth, profiles do not own memory, and execution outcomes do not automatically consolidate learning. No generic shell/network capability, autonomous goal formation, self-approval or L4 behavior is added.

Reliability evidence includes 203 passing tests, complete receipt-to-source provenance, idempotent repeated ingestion/execution, current-schema compatibility, actual process restart determinism, injected crash recovery without reinvocation, explicit corrupted-state failures and a completed ten-minute full-stack soak. The validation report and versioned JSON artifacts contain measured counts, timings and resource samples.

Safety hardening closes approval replay/rollback gaps, terminal/unknown-outcome retry hazards, indexed identity mismatches and unbounded local source/provider collection. Resource limits apply to the available local reference services. No production cloud, paid provider, live agent, financial API or legacy dependency is required.

Selective retrieval is measured through 100,000 entities; Cognition, Council and planning from retrieved context through 10,000. Council snapshots are the first meaningful scaling bottleneck, about 3 seconds at 10,000 entities. The benchmark matrix separates cognitive, planning, gate, metadata and capability time. Measurements are platform-specific local baselines with small empirical samples, not service-level promises.

Known limitations and unresolved risks for later productization:

- Plans remain host-supplied/in-memory. After restart, the host must supply the exact immutable plan/version for further execution. Persisted receipts and audit links do not reconstruct or authorize a new plan.
- The E2E test host explicitly reviews a generic L2 draft and binds a sandbox version-2 plan before approval. Autonomous capability binding/replanning is not implemented.
- The local adapter's rollback preimages and circuit breaker state are process-local. Restart reconciliation reads target state and never reinvokes; rollback across a process loss is unavailable without an explicit durable preimage design. A target already in the desired state proves state equivalence, not causal attribution of the effect.
- Crash tests model interruption at defined code boundaries with repository reopen, not power-loss durability or arbitrary filesystem corruption. SQLite and filesystem effects are separate transactions.
- Concurrency is limited to tested separate-connection reads and explicit writers, atomic metadata claims and explicit index refresh. Shared-connection concurrent writes, distributed execution and parallel Council members are unsupported.
- Provider timing is cooperative: a synchronous callback that never returns cannot be forcibly terminated. Unknown compressed-media duration is not proven; WAV duration and known metadata limits are tested. Production providers/uploads are absent, and canonical multimodal quality uses deterministic fakes.
- File confinement is for a trusted local sandbox without a concurrent hostile filesystem actor. No claim of OS-level isolation or protection from concurrent junction/symlink replacement is made. File/storage caps and rollback path re-resolution are enforced in the tested model.
- Existing historical parser records are preserved; the locator correction applies to newly produced perception runs. Historical idempotent sources are not silently rematerialized.
- Structural cognitive/retrieval judgments cover a small curated dataset. They do not establish human-level reasoning, semantic truth, OCR/transcription accuracy or broad-query production performance.
- Windows working-set/peak/handle metrics are practical leak indicators; total index/cache heap allocation and SQLite connection counts are not separately instrumented. Index text bytes are explicitly a size proxy.

These limits define the reference implementation's supported scope; none is presented as a passed production capability. No unresolved critical failure was observed inside the tested scope. See [validation](PHASE_14_VALIDATION.md) and [hardening design](PHASE_14_SYSTEM_HARDENING_E2E.md) for evidence and reproduction. No dependencies or ADRs changed. ART-DEP-AI was untouched, no migration or Phase 15 work was performed, and no remote was created or pushed.

## Phase 16 public integration update

Public API v1 and MCP contract v1 are implemented over package 0.1.0/state schema 1. The local synchronous SDK and stdio MCP surface pass installed-wheel validation for handshake, health, Study, source status, memory lookup, Recall, Cognition, Council, and proposal-only Planning. A generic host imports only the top-level public namespace and has no database or repository access. SDK/MCP semantic parity is covered for health, recall, cognition, and planning.

Public execution is deferred. Phase 13 L3 remains internal and exact-approval-gated; no SDK method, MCP tool, self-approval route, or bypass flag invokes execution. The prior reliability limits remain. Additional interface risks are pre-1.0 evolution, sync-only/limited-concurrency SDK behavior, Windows-only installed validation, static hand-maintained JSON schemas, and the unresolved `LICENSE_DECISION_REQUIRED`. This update does not declare v1.0 released or begin Phase 17.
