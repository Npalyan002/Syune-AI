# SYUNE Phase 12: Executive Contracts / L2 Planner v1

## Autonomy boundary

Phase 12 activates L2 PLANNER. SYUNE accepts an explicit goal, constructs and validates a bounded proposal, and prepares a version-bound review envelope. It has no execution authority. An `ActionProposal` describes a possible future action as immutable data; an `ApprovalEnvelope` binds review scope and does not represent approval or authorization. Human or host authority remains final.

The autonomy ladder is L0 Memory, L1 Advisor, L2 Planner, L3 Supervised Executive, and L4 Autonomous Executive. L3 and L4 remain inactive. Executive exposes `plan()` and explicit immutable `revise()` only. There is no executor, tool invocation, agent dispatch, Control Core call, shell or network operation, automatic approval, or self-authorization.

## Contracts

Typed contracts include `ExecutiveRequest`, `ExecutiveContext`, `Goal`, `PlanningAssumption`, `Constraint`, `Plan`, `PlanStep`, `PlanDependency`, `PlanCheckpoint`, `ActionProposal`, `RiskAssessment`, `BudgetEstimate`, `CapabilityDescriptor`, `ApprovalRequirement`, `ApprovalEnvelope`, `PolicyDecisionRecord`, `PlanValidationResult`, `PlanDiff`, `ExecutiveDiagnostics`, and `ExecutiveResult`. Executive, goal, assumption, constraint, plan, step, checkpoint, proposal, risk, policy, envelope, and capability identities use canonical typed opaque IDs.

An explicit non-empty Goal is mandatory. It retains source, success criteria, priority, horizon, correlation, timestamp, status, and ambiguity flags. `FUTURE_EXECUTIVE` is reserved and rejected for current goal creation. Missing success criteria produce a visible assumption and validation need rather than a silent user requirement.

Constraints carry kind, source, subject, requirement, satisfaction, prohibition, and explanation. Supported kinds are hard, soft, safety, resource, time, dependency, scope, policy, approval, and capability. Sources include user, host, governance, Cognitive/Council output, and system hard limits. Incompatible hard/safety/policy/scope requirements are returned as exact planning blockers. Unsatisfied hard, safety, dependency, or capability conditions block relevant planning.

## Planner and graph

`PlannerEngine` is deterministic and rule based. It normalizes the goal, emits prerequisite analysis, a pure data proposal, and a human review step, then attaches preconditions, expected outputs, verification criteria, risks, estimates, checkpoints, criterion references, and dependencies. `PlanValidator` performs deterministic topological ordering, detects cycles, propagates blocked ancestors to descendants, checks plan limits, records uncovered criteria, and combines policy decisions. It never silently repairs cycles.

Every emitted plan is immutable and versioned. `InMemoryPlanRepository` preserves all versions and their validation/envelope records for the service lifetime. Revision targets the latest version, creates a new plan version and proposal identities, retains lineage and provenance, returns a structured diff, and replaces the prior stored envelope with an invalid copy. Durable plan persistence is deferred because the canonical architecture has not selected an Executive store; no external execution state is stored.

## Context and provenance

Executive consumes only supplied structured `CognitiveResult` and `CouncilResult` artifacts. It copies bounded entity, source, and inference IDs; unresolved gaps and uncertainty; agreement/disagreement IDs; minority evidence IDs; Council metadata; and a stable context fingerprint. It does not retrieve, attend, infer, invoke Council, or copy all Memory. Council convergence never becomes authority. Disagreement and minority evidence become visible assumptions/risk drivers, while common gaps can block the plan.

Plan steps and proposals retain canonical entity/source references. Plan records retain inference IDs, planner version, configuration fingerprint, prior version, and revision reason. Planning objects are Executive artifacts and are never promoted to Observation, Claim, Evidence, Concept, Procedure, or LearningSignal.

## Action, risk, budget, and capability data

`ActionProposal` contains typed category, target description, scalar structured parameters, preconditions, expected effect, reversible state and notes, risk, cost estimate, approval requirement, static capability requirement, idempotency requirement, side-effect class, explanation, and provenance references. It contains no callable, client, live handle, token, or callback.

Categories include READ, ANALYZE, CREATE, UPDATE, DELETE, SEND, EXECUTE_TOOL, CALL_AGENT, EXTERNAL_REQUEST, and HUMAN_DECISION. EXECUTE_TOOL and CALL_AGENT remain descriptions of unavailable future capability. Side effects are NONE, local/external reversible/irreversible, or UNKNOWN. Unknown capability is explicit.

Risk is ordinal rather than a calibrated probability. Drivers include irreversible change, external side effect, missing evidence, unknown capability, Council disagreement/minority concern, sensitive target, and unknown cost. Destructive or external proposals expose target, rollback uncertainty, verification checkpoints, high or unknown risk, and mandatory review.

Budget estimates cover time, compute, tokens, money, external/tool/agent calls, human reviews, and storage. Unknown monetary cost stays `None` with UNKNOWN uncertainty. Planning never spends budget. Global limits cap steps, dependencies, proposals, assumptions, risks, checkpoints, revisions, deterministic refinement iterations, wall time, and decomposition depth; caller limits can only reduce these ceilings.

## Policy and approval

`PolicyEvaluator` is a pure evaluator with visible rule IDs and inputs. Precedence is: hard violation or prohibited category or critical unresolved gap blocks; irreversible effects, unknown side-effect risk, and mandatory reviewers require approval; read-only/no-side-effect proposals are allowed for review. ALLOW_FOR_REVIEW is not execution authorization.

Approval envelopes bind exact `plan_id`, version, proposal IDs, risks, side effects, estimate, gaps, reviewers, and scope. They contain no approved state or bypass. A revision invalidates the earlier stored envelope and creates a new envelope. `FUTURE_CONTROL_CORE` is only a reserved approval kind.

## Resource and failure behavior

Typed errors cover missing/ambiguous goals, constraint conflicts, graph cycles, hard violations, policy blocks, approval requirements, unknown capability/budget, insufficient Cognitive/Council context, revision conflicts, and plan limits. One deterministic draft/validate pass is used in v1; the typed iteration ceiling reserves bounded repair without enabling recursive planning. Stage timings and counts are diagnostic and do not affect plan semantics.

Executive event names remain reserved by the canonical Event Model. No event bus is introduced and no execution event exists. No dependency, provider, network library, store migration, MCP tool, or ART-DEP-AI integration is added.

## Limitations

V1 action selection uses a small generic lexical vocabulary and static unknown capability descriptors. Estimates are conservative local planning metadata. The reference repository is process local. Time windows are represented as goal/constraint/precondition data and are not scheduled. Planning quality is not truth probability, Council majority is not permission, and an ignored plan is safe.
