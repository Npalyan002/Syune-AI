# SYUNE Phase 08 Cognitive Core v1

## Scope

Phase 08 adds a deterministic advisory cognitive cycle over canonical Memory, Retrieval, and the read-only learned-state view introduced in Phase 07. It does not call providers, write memory, create learning signals, persist hidden reasoning, dispatch agents, or execute actions.

## Contracts and cycle

`CognitiveRequest` carries a typed request ID, text and/or typed memory cues, optional temporal and correlation context, and a `CognitiveBudget`. `CognitiveResult` exposes status, transient context, structural inference records, metacognitive assessment, advisory response candidates, provenance, timings, diagnostics, and truncation reasons.

The cycle is: Intake -> Retrieval -> Attention -> WorkingContext -> Inference -> Metacognition -> ResponseCandidate. Intake normalizes whitespace and validates explicit typed IDs. RetrievalService remains the only retrieval authority. One follow-up recall is allowed only when a first round yields a single candidate and the request budget permits it.

Attention is deterministic and explainable. Its bounded score is `0.55 * cue_directness + 0.35 * activation + 0.10 * learned_relevance`, clamped to `[0,1]`. Each item exposes these components. Learned utility and salience arrive only through Retrieval's existing read-only `PlasticityView`; cognition never imports Learning.

WorkingContext is transient, ranked, provenance preserving, and capped by `max_active_entities`. It is returned for diagnostics and is never stored as canonical memory or hidden chain of thought.

## Structural inference

The inference engine reads canonical associations and provenance and emits bounded, typed, explainable records:

- `DIRECT_RELATION`: an existing association connects two active entities.
- `MULTI_HOP_SUPPORT`: a cycle-safe canonical path connects entities within depth/path limits.
- `CONVERGENT_SUPPORT`: paths from two or more active roots converge.
- `CONFLICT_SIGNAL`: an explicit canonical conflict/contradiction relation is present.
- `MISSING_LINK`: no bounded canonical connection is available.
- `SOURCE_OVERLAP`: active evidence shares or spans provenance sources.
- `TEMPORAL_ORDER`: canonical Episode timestamps safely establish `BEFORE`.

These records are structural diagnostics. They do not create Claims, rewrite confidence, or assert truth. UUID5 identities make identical request/evidence records deterministic across service reconstruction.

## Metacognition and response

Metacognition computes evidence coverage, source diversity, confidence distribution, materialization state, structural support, gaps, conflicts, resource truncation, and a bounded readiness score. It deterministically selects `READY`, `PARTIAL`, `INSUFFICIENT_EVIDENCE`, `CONFLICTED`, `DEGRADED_MEMORY`, or `LIMIT_REACHED`; `FAILED` remains available for a failed cycle record.

Response candidates are advisory summaries linked to entity, inference, and source IDs. They report supported structure, insufficient evidence, or conflicts and contain no executable action.

## Resource and authority boundaries

`CognitiveBudget` bounds recall rounds/candidates, active entities, graph edges, inference paths/depth/records, response candidates, and records a cycle time budget. Stage and total timings plus counts are visible. Result ordering uses explicit deterministic sort keys.

Canonical Memory remains authoritative and immutable during cognition. Retrieval owns recall and activation. Learning owns all adaptive writes. Observation remains non-epistemic, and inference is never promoted to Claim. The MCP allowlist is unchanged and no cognitive mutation or external integration is introduced.

## Limits

Inference v1 recognizes explicit relation labels containing conflict/contradiction semantics and Episode timestamp ordering. It does not perform semantic entailment, truth adjudication, language generation, background cognition, or autonomous follow-up. Time measurements vary by host and are diagnostic rather than semantic inputs.
