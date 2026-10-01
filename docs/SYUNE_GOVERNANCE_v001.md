> Historical baseline applicability (Phase 14): This v001 document preserves its original decisions. Current implementation status and superseding phase decisions are recorded in [Phase 14](PHASE_14_SYSTEM_HARDENING_E2E.md) and [release readiness](SYUNE_RELEASE_READINESS_v1.md). Phase 13 authorizes externally approved L3 local sandbox execution; MCP remains L1. The old roadmap label for Phase 14 is superseded by standalone system hardening. Legacy migration remains deferred. All shared-memory, epistemic and authority invariants remain binding.

# SYUNE — Governance

Version: v001 / Baseline 0.1. Status: Phase 00 architecture freeze.
Authority: [Blueprint](SYUNE_BLUEPRINT_v001.md), [Constitution](SYUNE_CONSTITUTION_v001.md), and root Phase 00 specification.
Current mode: L1 ADVISORY.

## Current authority

SYUNE_AUTONOMY_LEVEL = L1. SYUNE_EXECUTION_MODE = ADVISORY. Study, remember, retrieve, reason, learn, and recommend are allowed. Agent dispatch, publishing, direct production mutation, bypassing Control Core or human approvals are not. brain.observe and brain.feedback are cognitive intake, not execution authority.

## Future levels, inactive now

L0 MEMORY; L1 ADVISOR; L2 PLANNER; L3 SUPERVISED_EXECUTIVE; L4 AUTONOMOUS_EXECUTIVE. Future path: Goal → Plan → Intention → Action Proposal → Policy/Risk/Budget Check → Control Core → Capability Registry → Agent/Tool → Outcome → Learning. Authority is capability-scoped, never one unrestricted global switch. Policy, risk, budget, capability authorization, human approval, and audit remain gates.

## Data and migration boundaries

SYUNE-LIBRARY begins read-only to Study. Ingestion never implicitly deletes raw material. Provider adapters receive minimum required content. Secrets/API keys remain external configuration, never Git; logs/events do not intentionally persist secrets. External source trust is metadata, not truth. ART-DEP-AI legacy systems stay operational until the [Roadmap](SYUNE_ROADMAP_v001.md) retirement gates pass.
