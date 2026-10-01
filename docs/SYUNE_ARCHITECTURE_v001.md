> Historical baseline applicability (Phase 14): This v001 document preserves its original decisions. Current implementation status and superseding phase decisions are recorded in [Phase 14](PHASE_14_SYSTEM_HARDENING_E2E.md) and [release readiness](SYUNE_RELEASE_READINESS_v1.md). Phase 13 authorizes externally approved L3 local sandbox execution; MCP remains L1. The old roadmap label for Phase 14 is superseded by standalone system hardening. Legacy migration remains deferred. All shared-memory, epistemic and authority invariants remain binding.

# SYUNE — Architecture

Version: v001 / Baseline 0.1. Status: Phase 00 architecture freeze.
Authority: [Blueprint](SYUNE_BLUEPRINT_v001.md), [Constitution](SYUNE_CONSTITUTION_v001.md), and root Phase 00 specification.
Current mode: L1 ADVISORY.

## System boundary

SYUNE owns study/intake orchestration, source registry and fingerprints, shared memory, provenance/evidence, retrieval/activation, working memory and cognitive contracts, learning/consolidation, world model, domain profiles, cognitive council, model gateway, MCP cognitive surface, and evaluations. Executive planning is future contract only.

ART-DEP-AI initially owns task intake, Claude Main Orchestrator, agent routing, production/review agents, tool execution, Human Approval Gate, Control Core, and production workflows. Initial integration is MCP. REST/SDK may follow without changing the core.

Experience, Study, and external sources feed Shared Distributed Memory. Retrieval/Activation, Learning/Consolidation, World Model, and Cognitive Core operate over it. Domain Profiles and Council serve cognition. Future Executive Layer must pass Governance → Control Core → Capability Registry → Agents/Tools. In current L1 ADVISORY mode, SYUNE may study, remember, retrieve, reason, learn, and recommend; it cannot dispatch agents.

Opaque stable IDs, versioned records, source/derived distinction, bidirectional provenance, and factual events span components. Provider-specific APIs remain behind adapters. Physical database, distribution topology, algorithms, and transport details are deferred. See [Contracts](SYUNE_CONTRACTS_v001.md), [Governance](SYUNE_GOVERNANCE_v001.md), and [Event Model](SYUNE_EVENT_MODEL_v001.md).
