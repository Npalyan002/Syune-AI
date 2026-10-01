# SYUNE Phase 13 validation

`PHASE_13_STATUS = PASS`

## Implementation

Added typed supervised execution contracts, external approval verification, capability registry, fixed local sandbox adapter, per-attempt runtime gate/policy, risk and budget fuse, durable SQLite idempotency/audit, verification-first outcomes, bounded retry, explicit rollback, crash reconciliation, emergency stop, circuit breaker, feedback and uncommitted learning drafts. No dependency, provider, MCP tool, production adapter, schema outside the new execution database, or ADR was added.

## Demonstrations

- Approved action: exact TEST approval for one local reversible write passes gate, writes only to project-local runtime state or the pytest temporary sandbox, read-back verifies, and persists a receipt.
- No approval: invalid verification blocks with zero adapter calls and zero file side effects.
- Stale/revoked/expired approval: plan-version mismatch, revocation, and expiration each block before the adapter.
- Scope drift: changing the approved path or parameters fails the canonical parameter hash; widening runtime budget also blocks.
- Registry: duplicate IDs, disabled/unhealthy status, schema mismatch, side-effect mismatch, and missing capability are rejected or gated.
- Idempotency: the first call performs one write; the second returns the prior receipt and leaves adapter call count at one.
- Verification failure: a successful write plus forced read-back mismatch becomes ROLLBACK_REQUIRED rather than success.
- Unknown outcome: a synthetic post-write uncertainty becomes UNKNOWN_OUTCOME; repetition waits for reconciliation and does not reinvoke.
- Retry: one declared retryable failure on an idempotent adapter retries once within approval/budget and verifies; limits remain bounded.
- Rollback: an explicitly rollback-approved write restores the pre-execution absence and verifies; removing rollback scope blocks.
- Crash recovery: a durable IN_PROGRESS row after an actual sandbox write is reconciled by read-back into verified success with no second invocation.
- Checkpoint/budget/stop: missing checkpoint returns WAIT, zero write/action fuse blocks, and an activated stop controller prevents invocation.
- Dependencies: service requires completed verified predecessor steps and stops the sequence on failure or incomplete verification.
- L3 scope: only proposal IDs in the explicit request and approval are considered. No related action discovery occurs.
- Learning neutrality: results contain only `LearningSignalDraft(committed=False)`; the package has no Learning import or commit path.

## Benchmark

Twenty clean approved writes and idempotent replays under isolated project-local runtime state on Windows/Python 3.12:

| Measure | p50 ms | p95 ms |
| --- | ---: | ---: |
| Approval verification | 0.061 | 0.071 |
| Capability resolution | 0.002 | 0.002 |
| Gate evaluation | 0.012 | 0.014 |
| SQLite metadata transactions | 371.76 | 388.26 |
| Sandbox adapter invocation | 4.64 | 5.16 |
| Read-back verification | 4.08 | 4.67 |
| Full supervised execution | 381.22 | 397.51 |
| Idempotent replay | 0.41 | 0.52 |

All 20 actions verified and duplicate side effects were zero. Local SQLite commits and filesystem/antimalware behavior dominate the tiny adapter operation. These measurements establish an observational baseline, not an SLA.

## Gates

- Focused Phase 13 suite: PASS (`11 passed`).
- Full locked pytest suite: PASS (`138 passed in 20.68s`).
- Phase 13 architecture check: PASS.
- `git diff --check`: PASS.
- Full diff review: PASS.
- Local commit and clean worktree: PASS.
- Dependencies added: none.
- ADRs created or modified: none.
- ART-DEP-AI changes: none.
- Remote/push: none.

## Deviations and decisions

Safe local execution uses a dedicated path-confined file adapter; no production capability exists. Approval tokens are constructed by the host/test boundary because an approval-creation service would violate self-approval. Rollback preimages and circuit counters are process-local, while idempotency, incomplete state, outcome, verification, and receipts are durable. Runtime event names remain documentation-level because no canonical bus exists. No unresolved issue blocks the milestone.

## Exit checklist

- [x] Typed ExecutionRequest, ApprovedProposal, Invocation, gate, record, outcome, verification, rollback, retry, budget, receipt, feedback, and learning-draft contracts.
- [x] Exact external approval identity/version/proposal/parameter/risk/side-effect/budget/freshness/revocation binding; no wildcard or self approval.
- [x] Typed registry, metadata, fixed sandbox adapter, schema checks, no shell/code/network/production capability.
- [x] Per-attempt runtime revalidation, risk/budget fuse, dependency/checkpoint gate, stop controller, circuit breaker, and sequential failure isolation.
- [x] Durable idempotency and audit, verified success distinction, UNKNOWN_OUTCOME, bounded retry, explicit rollback, crash verification before classification.
- [x] Explicit request only; no watcher, autonomous goal, autonomous replan, Control Core, production agent, ART-DEP-AI, or L4 behavior.
- [x] No canonical Memory mutation or automatic LearningSignal; only uncommitted typed draft.
- [x] Instrumentation, sandbox benchmark, tests, architecture enforcement, docs, local commit, clean tree, no remote.
