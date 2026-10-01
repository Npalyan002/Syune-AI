# Phase 16 public interfaces, SDK, and integration protocol

Phase 16 adds a transport-neutral public API v1, a synchronous local Python facade, MCP contract v1, and a generic host protocol. It changes no memory, retrieval, inference, Council, planning, approval, or execution algorithms.

The public package is `syune.api`; the lifecycle facade is `syune.sdk.Syune`, intentionally re-exported as `from syune import Syune`. Public requests/results are frozen dataclasses. Stable errors, typed IDs, correlation context, deterministic JSON, capability discovery, and handshake/version negotiation are owned by the API layer. The facade maps to the Phase 15 runtime but returns only public values. Its runtime reference is private and no repository, store, SQLite connection, index, adapter, or execution service is exported.

Public operations are health, status, capabilities, handshake, Study, source status, memory get, Recall, Cognition, Council, and Planning. Study repeats configured-root confinement. Recall/cognition/Council retain source locators, typed entity/source IDs, structural reasons, gaps, conflicts, and readiness semantics. Planning remains proposal-only.

Supervised execution is explicitly not exposed in public v1. Phase 13 remains active inside SYUNE, but no SDK method or MCP tool can invoke it. This avoids inventing approval transport before a stable public verifier contract exists and ensures no self-approval or bypass flag appears. `ExecutionRequest`/`ExecutionResult` reserve the typed wire vocabulary and documentation; they confer no capability.

MCP v1 expands the earlier advisory gateway with status, capabilities, cognition, Council, and planning. NORMAL mode exposes ten allowlisted tools. SHADOW/read-only mode omits Study. No execution tool exists. Errors are bounded and mapped to stable codes; normal output has no traceback.

JSON schemas cover the common public result envelope and error envelope. They permit additive fields and pin API version 1. A deterministic v1 fixture anchors compatibility. The generic host imports only top-level public symbols, uses public operations only, and never accesses state databases.

No ADR was needed: the public facade implements the detachable-interface direction already frozen by ADR-0001 and preserves the provider, memory, provenance, advisory/planning, and L3 supervision boundaries. There is no REST/cloud service, auth, multi-tenancy, legacy migration, ART-DEP-AI coupling, telemetry, generic shell/code execution, or Phase 17 work.
