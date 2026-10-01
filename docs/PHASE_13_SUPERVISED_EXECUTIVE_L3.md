# SYUNE Phase 13: Supervised Executive / L3 v1

## L3 boundary

Phase 13 activates a narrow L3 SUPERVISED EXECUTIVE for fixed-purpose local capabilities under a dedicated SYUNE sandbox. `SupervisedExecutiveService.execute_approved()` is the only runtime entry point. It requires an explicit typed `ExecutionRequest`; plans and envelopes alone cause nothing. There is no watcher, autonomous goal, self approval, approval by confidence/Council, hidden replanning, production agent, live Control Core, generic shell/code/HTTP capability, or ART-DEP-AI integration.

Execution separates plan, external authorization, runtime gate, adapter invocation, outcome, verification, and optional uncommitted learning draft. A valid plan is not approval, adapter return is not verified success, and outcome capture does not learn.

## Approval runtime

`ApprovalToken` is supplied externally with source HUMAN, HOST, or TEST. FUTURE_CONTROL_CORE is reserved and rejected. Tokens bind the exact plan ID/version, Phase 12 envelope ID, nonempty proposal set, per-proposal parameter hashes and targets, risk ceiling, side-effect classes, runtime budget, issue/expiration times, approver reference, and canonical fingerprint. Wildcard scope is impossible. Revoked, expired, stale, malformed, broadened-budget, changed-parameter, changed-risk, changed-side-effect, and out-of-envelope requests block before adapter invocation.

`ApprovalVerifier` is read only and cannot mint, approve, authorize, widen, or refresh tokens. Revalidation occurs immediately before each attempt, including bounded retry.

## Capability registry and sandbox

`CapabilityRegistry` binds typed `RuntimeCapabilityDescriptor` records to constructor-registered adapters and rejects duplicate IDs. Descriptors expose category, status/health, side-effect class, exact input/output fields, idempotency, rollback, verification, approval, risk floor, execution location, adapter identity/version, and configuration source.

V1 ships only `LocalSandboxFileAdapter`. It creates, updates, or deletes one explicitly relative path beneath a fixed resolved sandbox root. Path traversal and the root itself are rejected. The adapter uses `pathlib` file operations and has no shell, subprocess, code evaluation, network client, environment discovery, or production path. Registry schema and side-effect metadata must exactly match the approved proposal before execution.

## Gate, policy, risk, budget, and sequence

Every adapter call passes `ExecutionGate` immediately beforehand. Visible runtime rules cover approval validity, capability health/status, risk floor, exact budget, idempotency state, emergency stop, checkpoint, dependency, and circuit state. Decisions are ALLOW, WAIT, BLOCK, or INVALID with rule IDs and reasons. ALLOW applies to one exact invocation.

`RuntimeBudget` caps actions, retries, wall time, external calls, optional compute/tokens/money, and write/delete operations. Runtime budget must equal the approved ceiling in v1; it cannot be widened. `RuntimePolicyEvaluator` blocks exhausted fuses and waits when risk has risen. Sequential execution rechecks every proposal. Verified predecessor steps and all blocking checkpoint IDs are required. Failure or incomplete verification stops dependent work. A subset is accepted only when its dependencies remain satisfied.

`ExecutionStopController` blocks before the next proposal and records the operator reason while allowing the current atomic local call to finish. `CircuitBreaker` opens after a bounded repeated failure threshold and produces a replan need. It does not trigger replanning.

## Idempotency, repository, and crash recovery

Invocation keys are SHA-256 fingerprints of plan ID/version, proposal ID, capability ID, and canonical parameters. `SQLiteExecutionRepository` durably stores state, audit identity, invocation material, outcomes, verification, and immutable receipt data. A confirmed duplicate returns the prior receipt with `idempotent_replay=True`; it never calls the adapter again. IN_PROGRESS and UNKNOWN_OUTCOME wait for reconciliation.

The SQLite transaction covers internal execution metadata only. It cannot transact the filesystem side effect. `recover_incomplete()` reads durable IN_PROGRESS rows, reconstructs the fixed registered invocation, verifies current target state, and classifies it SUCCEEDED_VERIFIED or UNKNOWN_OUTCOME without reinvocation. Restart never blindly repeats a side effect.

## Outcome, verification, retry, and rollback

`ExecutionOutcome` records observed effect, typed output pairs, side-effect confirmation, target, adapter metadata, warnings, uncertainty, and verification requirement. `OutcomeVerifier` supports NONE_REQUIRED, RETURN_VALUE, READ_BACK, STATE_COMPARISON, CHECKSUM, and EXPLICIT_CONFIRMATION contracts. V1 file operations use READ_BACK. Success is SUCCEEDED_VERIFIED only after matching state; return success plus mismatch becomes ROLLBACK_REQUIRED. A possible side effect followed by uncertainty becomes UNKNOWN_OUTCOME and is never automatically retried.

`RetryPolicy` is capped at three attempts. A retry requires a declared retryable error, still-valid approval, healthy capability, remaining budget, and idempotency support. No sleep or hidden attempt occurs. Nonretryable, exhausted, expired, degraded, or uncertain cases stop.

Rollback is a separate explicit service call and requires the original approval token to include rollback scope. The sandbox adapter snapshots prior bytes in process, restores them, read-back verifies, and retains the original receipt plus a typed `RollbackPlan`/`RollbackResult`. Rollback is not assumed safe, not automatic, and does not represent an external transaction.

## Learning, provenance, and security

Verified execution may return a `LearningSignalDraft` with `committed=False`. The runtime imports no Learning service and cannot write the ledger or overlay. Execution control does not mutate canonical Memory, Cognition, Council, Profiles, or Plan versions. `ExecutionFeedback` can request a future explicit plan revision; the runtime never calls PlannerEngine.

Typed audit retains plan/proposal/capability/approval identities, fingerprints, gate reasons, timestamps, idempotency state, outcome, verification, retry/rollback state, errors, and receipt. No secrets, live handles, callbacks, arbitrary dictionaries as primary contracts, or production credentials are accepted.

## Limitations

Only deterministic local test file behavior is supported. Circuit state and adapter rollback snapshots are process-local; durable execution/idempotency/outcome state is SQLite backed. Recovery can verify the sandbox target but cannot recover an in-memory preimage after process loss. Concurrency, live scheduling, production integrations, automatic event transport, live Control Core, autonomous replanning, and L4 remain deferred.
