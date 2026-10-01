# SYUNE Phase 11: Cognitive Council v1

## Purpose

The Cognitive Council runs two to six explicitly selected Phase 09 activation profiles over one base `CognitiveRequest`. Each member is an equal, read-only view through the existing `CognitiveService`; members are profiles rather than agents. The Council compares structured cognitive results and returns advisory synthesis without choosing a hidden winner.

## Architecture

`CouncilService` captures a `CouncilCognitiveSnapshot`, resolves the explicit member list, executes members sequentially, verifies state after every member, invokes `CouncilAnalyzer`, and invokes `CouncilSynthesizer`. Sequential execution is the deterministic v1 strategy. The package depends on cognition, profiles, retrieval, memory read interfaces, and core types. It does not call Study, Learning, providers, Control Core, agent dispatch, or external actions.

The snapshot fingerprints canonical entities and associations, retrieval index version and entries, the shared plasticity state, profile definitions, and Cognitive Core version. The present repositories expose no unified source materialization version, so the typed snapshot reports `NOT_EXPOSED`. Before and after markers detect observable state drift and fail with `SHARED_STATE_MISMATCH`.

## Contracts and lifecycle

Typed immutable contracts cover `CouncilRequest`, `CouncilMemberSpec`, `CouncilMemberResult`, `CouncilRun`, `CouncilCognitiveSnapshot`, `CouncilEvidenceMap`, `CouncilAgreement`, `CouncilDisagreement`, `CouncilGap`, `CouncilSynthesis`, `CouncilResult`, `CouncilDiagnostics`, and `CouncilBudget`. Council, run, agreement, disagreement, gap, and synthesis identifiers use canonical typed IDs.

Membership is explicit, distinct, and bounded to the six immutable built-ins: GENERAL, CREATIVE, SYSTEMS, STRATEGY, PRODUCT, and RESEARCH. A base request cannot preselect a profile. The stable lifecycle is CREATED, MEMBERS_RESOLVED, MEMBERS_RUNNING, MEMBERS_COMPLETE, ANALYSIS_COMPLETE, SYNTHESIS_COMPLETE, and RESULT_READY; failures are represented by typed Council errors or explicit member states.

## Analysis and synthesis

The evidence map preserves typed entity IDs, source IDs, profile usage, union, intersection, per-profile unique evidence, and source counts. Agreements cover entity, source, structural inference, gap, conflict, status, and candidate shape overlap. Agreement coverage is structural convergence and is never interpreted as truth probability.

Disagreements preserve member positions, implicated entities and sources, relevant profile factors, severity, driver, difference level, resolvability, and explanation. The contract supports evidence selection, inference priority, readiness, gaps, conflicts, response emphasis, and resource effects. A canonical conflict visible to every member remains a substantive evidence-driven disagreement. The Council performs no majority vote and does not rewrite confidence.

Evidence used by exactly one completed profile is returned as a minority insight. A gap reported by at least two profiles becomes a common gap. Synthesis modes are BALANCED, EVIDENCE_FIRST, and DIVERGENCE_FIRST. Readiness is a visible deterministic composition of completion, evidence overlap, profile diversity, gap penalty, conflict penalty, and resource penalty. Status is READY, PARTIAL, INSUFFICIENT_EVIDENCE, CONFLICTED, LIMIT_REACHED, or FAILED. Synthesis stays advisory and names limitations and the next information need.

## Bounds and failures

Council hard limits cap members, aggregate recall rounds, retrieval candidates, inference records, per-member cycle time, evidence records, synthesis records, and wall time. Request limits are intersected with global hard limits. Exhausted aggregate budgets mark remaining members `NOT_RUN` and produce LIMIT_REACHED. One member failure is explicit and does not discard successful member results. Unknown and incompatible profiles, drift, analysis failure, synthesis failure, and budget exhaustion have typed errors.

## Invariants

All members use one MemoryRepository, one retrieval index, and one shared learned-state view. Council execution writes none of them. Observation stays non-epistemic, provenance survives through evidence and synthesis references, canonical confidence remains unchanged, and no LearningSignal is created. Multimodal caption, transcript, and text observations participate through their existing canonical IDs and exact source locators.

## Operational limits

V1 uses sequential execution and in-process fingerprints rather than repository-level snapshot handles. Structural comparison depends on the bounded evidence exposed by each `CognitiveResult`; it does not infer semantic truth. Timing diagnostics are observational and excluded from semantic determinism comparisons. No persistence is added because Council output is an advisory result over durable shared state.
