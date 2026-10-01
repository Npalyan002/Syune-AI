> Historical baseline applicability (Phase 14): This v001 document preserves its original decisions. Current implementation status and superseding phase decisions are recorded in [Phase 14](PHASE_14_SYSTEM_HARDENING_E2E.md) and [release readiness](SYUNE_RELEASE_READINESS_v1.md). Phase 13 authorizes externally approved L3 local sandbox execution; MCP remains L1. The old roadmap label for Phase 14 is superseded by standalone system hardening. Legacy migration remains deferred. All shared-memory, epistemic and authority invariants remain binding.

# SYUNE

### *Persistent Cognitive Intelligence*

## v001 - BLUEPRINT BASELINE

**Version:** v001 / Baseline 0.1  
**Date:** 2026-09-21  
**Current execution mode:** ADVISORY  
**Primary integration:** Claude Agent System via MCP  
**Canonical principle:** shared distributed associative memory; domains do not own memory.

> Baseline rule: change this architecture intentionally and version the change. Do not let implementation silently redefine the system.

## 1. System boundary

SYUNE is an independent repository/product. The existing Agent System executes workflows. SYUNE studies, remembers, retrieves, reasons, learns, builds a world model, and later may gain governed executive control.

```text
CLAUDE AGENT SYSTEM <---- MCP ----> SYUNE
        |                                |
      AGENTS                Memory / Study / Cognition / Learning
```

## 2. Non-negotiable principles

1. Brain is separate from the Agent System repository.
2. MCP is the first integration boundary; REST/SDK can be added later.
3. Memory is shared, distributed, associative and provenance-aware.
4. Creative/Finance/Systems/Strategy are cognitive activation profiles, not physical memory silos.
5. RAG is a retrieval mechanism, not memory itself.
6. Every durable claim/memory trace retains provenance, evidence, version and confidence.
7. Study ingestion is idempotent and resumable.
8. LLMs/VLMs are replaceable providers, not the Brain.
9. STEP 01-30 are functional requirements, not 30 folders/agents/services.
10. Cognition and execution are separate; future action goes through governance and Control Core.
11. Legacy RAG/memory/learning remains until shadow comparison and migration gates pass.
12. Important state changes are evented, auditable and checkpointed.
13. The Brain must remain detachable and agent-framework/provider agnostic.

## 3. Top-level architecture

```text
Experience Interface ----\
                          +--> Shared Distributed Memory --> Cognitive Core
Study System ------------/            |                         |
                                       +--> Learning             +--> Domain Activation Profiles
                                       +--> Provenance           +--> Future Executive Layer
```

## 4. Repository layout

```text
workspace/
+-- host-application/         # integrating agent system
+-- syune/                    # independent product
|   +-- core\
|   +-- memory\
|   +-- study\
|   +-- retrieval\
|   +-- learning\
|   +-- world_model\
|   +-- domains\
|   +-- executive\
|   +-- gateway\
|   +-- providers\
|   +-- storage\
|   +-- events\
|   +-- governance\
|   +-- evals\
|   +-- tests\
|   +-- docs\
+-- SYUNE-LIBRARY\
    +-- inbox\ books\ research\ videos\ images\ audio\
```

## 5. Memory model

Core entities: Source, Concept, Episode, Procedure, Association, Claim, Evidence, MemoryTrace, Provenance, ActivationState, Confidence.

A memory may simultaneously connect to creative, financial, strategic, temporal, causal and systems concepts. Domain profiles only bias activation and reasoning.

## 6. Study System

```text
DISCOVER -> REGISTER -> FINGERPRINT -> PERCEIVE/PARSE -> UNDERSTAND
        -> ENCODE -> BUILD ASSOCIATIONS -> CONSOLIDATE -> VERIFY
```

Registry states: DISCOVERED, REGISTERED, PARSING, PERCEIVED, UNDERSTOOD, ENCODED, CONSOLIDATING, CONSOLIDATED, VERIFIED, FAILED, REJECTED, RETRACTED.

Exact duplicate detection uses whole-source content hashes. Incremental reprocessing uses chapter/section/block fingerprints. Checkpoints make jobs resumable. Derived-memory links answer both "what did you learn from this source?" and "why do you believe this memory?".

## 7. Retrieval / activation

Retrieval v1 should combine candidate generation (vector, lexical, graph, episodic, procedural) with activation, associative spreading, salience/context/confidence/recency, pattern completion and working-memory selection. It must be benchmarked against legacy RAG.

## 8. Cognitive domains

Creative, Finance, Systems and Strategy are activation/reasoning profiles on one memory substrate. Cross-domain activation is allowed and desirable.

## 9. Agent integration

Initial MCP tools: `brain.health`, `brain.recall`, `brain.observe`, `brain.feedback`, `brain.source_status`, `brain.study_status`.

Current rule: Brain cannot dispatch agents. Future rule: Brain emits goals/plans/action proposals; governance and Control Core authorize execution.

## 10. Legacy migration

A. Parallel -> B. Shadow -> C. Hybrid -> D. Consolidation -> E. Retirement.

Do not delete existing RAG/memory/learning until acceptance gates and rollback path pass.

## 11. Future executive layer

```text
Memory/World Model -> Goals -> Plan -> Action Proposal -> Policy/Risk/Budget Check
-> Control Core -> Capability Registry -> Agent/Tool -> Outcome -> Learning
```

Autonomy levels: L0 Memory, L1 Advisor, L2 Planner, L3 Supervised Executive, L4 Autonomous Executive. Authority is capability-scoped, never one global ON/OFF switch.

## 12. Implementation roadmap

- PHASE 0 - Blueprint Freeze
- PHASE 1 - Repository Skeleton
- PHASE 2 - Memory Kernel
- PHASE 3 - Study System v1 (PDF/TXT/MD)
- PHASE 4 - Retrieval / Activation v1
- PHASE 5 - MCP Gateway v1
- PHASE 6 - Shadow Integration
- PHASE 7 - Learning + Consolidation
- PHASE 8 - Cognitive Core v1
- PHASE 9 - Domain Activation Profiles
- PHASE 10 - Multimodal Study
- PHASE 11 - Cognitive Council
- PHASE 12 - Executive Contracts / L2
- PHASE 13 - Supervised Executive / L3
- PHASE 14 - Legacy Consolidation
- PHASE 15 - Productization

## 13. Milestone M01

**Brain can independently ingest a previously unseen document, know that it has studied it, form distributed memories with provenance, retrieve relevant knowledge, and expose it to Claude through MCP.**

Acceptance: automatic source detection; duplicate protection; resume checkpoints; exact study status; provenance-linked memory; memory-oriented recall; source traceability; MCP access; legacy production remains untouched.

## 14. Context preservation

The canonical living source belongs in Git as Markdown. PDF is a version snapshot. DOCX is an editable business copy. Chat memory stores only the durable principles and current baseline version/location. Major architecture changes use ADRs.

Recommended docs:

```text
docs/
+-- SYUNE_BLUEPRINT_v001.md
+-- SYUNE_MEMORY_MODEL_v001.md
+-- SYUNE_STUDY_SYSTEM_v001.md
+-- SYUNE_CONTRACTS_v001.md
+-- SYUNE_EVENT_MODEL_v001.md
+-- SYUNE_EVALS_v001.md
+-- SYUNE_ROADMAP_v001.md
+-- ADR/
```

## 15. STEP 01-30 rule

STEP 01-30 remain cognitive research requirements mapped across implementation modules. They are not a service/folder topology.

## 16. Immediate build order

1. Create separate `SYUNE` Git repository.
2. Commit this Blueprint under `docs/`.
3. Create ADR index.
4. Define core contracts and IDs/events.
5. Define storage interfaces without locking databases prematurely.
6. Build Study Registry + hash/checkpoint logic.
7. Build PDF/TXT/MD vertical slice.
8. Build minimal distributed memory persistence.
9. Build recall v1 + benchmarks.
10. Expose minimal MCP gateway.
11. Connect to ART-DEP-AI in shadow mode.
