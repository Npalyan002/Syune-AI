# SYUNE Phase 05 — MCP Gateway v1

**Purpose:** a thin local protocol adapter over existing Study, Memory, and Retrieval services. **Authority:** L1 ADVISORY. The gateway neither dispatches agents nor executes external actions.

## Protocol and lifecycle

The official MCP Python SDK v2 (`mcp>=2,<3`, resolved 2.2.0) supplies `MCPServer` and `Client`. The primary transport is stdio; an official SDK in-process client exercises the same factory in tests. `python -m syune.gateway.mcp` starts stdio with no listener. `SYUNE_STUDY_ROOTS` must list explicit existing approved directories; `SYUNE_STATE_DIR` may set the local state directory and defaults to `.syune/state`. No operational database opens at import. `open_gateway()` constructs and closes the two SQLite adapters, rebuilds the derivative retrieval index, and injects the services into `create_syune_mcp_server()`.

The explicit allowlist contains exactly `syune_health`, `syune_source_status`, `syune_memory_get`, `syune_recall`, and `syune_study_source`. There are no MCP resources, prompts, or generic method exposure. Tool outputs use the SDK's structured output mapping and a separate gateway contract version `1`; this version does not freeze internal SQLite schemas or a permanent public wire format. MCP protocol negotiation is handled by the SDK.

## Tool mapping

- `syune_health`: product/version, L1 ADVISORY, component availability, formats, transport, SDK version, UTC time, and local call counts. Paths and secrets are omitted.
- `syune_source_status`: exactly one SHA-256 fingerprint, typed SourceId, or approved path; reports lifecycle, materialization, counts, versions, and safe timestamps without filesystem aliases.
- `syune_memory_get`: one `TypeName:UUID` typed ID; returns canonical entity type, fields, provenance, confidence, and optionally up to 32 direct associations. Observation and Claim remain distinct. Source locator URI is redacted.
- `syune_recall`: maps typed IDs and bounded cue limits to the existing RetrievalService. Each ranked candidate preserves the existing bare `entity_id` and `entity_type` fields and adds `typed_entity_id` in canonical `TypeNameId:UUID` form, derived from the actual typed ID object for direct use with `syune_memory_get`. Results also include score decomposition, activation, seed/path evidence, provenance, timing, truncation, and working-memory IDs. Score means relevance, never truth probability.
- `syune_study_source`: the sole mutating tool. It checks a canonical absolute file path against configured Study roots, rejects `..`, siblings and symlink escapes, and accepts only local TXT, Markdown, or text PDF. It delegates to StudyService and then explicitly syncs the derivative index. Sources are read only.

Handlers are async so short synchronous local service calls stay on the SQLite connection's owning event-loop thread. State writes remain in Study and Memory. Error mapping returns short structured codes for invalid inputs, missing IDs, unsupported paths/formats, Study/Recall failures, degraded materialization, and repository errors. Internal tracebacks, credentials, and sensitive absolute paths are not returned. MCP stdio stdout carries protocol traffic only; startup errors go to stderr. Local per-tool call counts and durations are in process only.

## Limits

The gateway does not provide remote authentication or network transport. Study roots require local configuration; there is no unrestricted filesystem or shell tool. It does not integrate with ART-DEP-AI, Claude, Control Core, or Executive behavior. Phase 06 integration remains deferred. The official SDK has transitive HTTP-related packages, but the SYUNE stdio server opens no network listener or web client.
