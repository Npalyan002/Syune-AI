# Phase 06 shadow integration

SYUNE is an optional MCP service for the ART-DEP-AI host. Its output is L1 ADVISORY and may only be inspected or compared manually. It does not route work, dispatch agents, invoke Control Core, update ART-DEP-AI state, or learn from host results.

## Shadow server

Set `SYUNE_SHADOW_READ_ONLY=1` when starting `python -m syune.gateway.mcp`. This registers only `syune_health`, `syune_source_status`, `syune_memory_get`, and `syune_recall`; `syune_study_source` is absent. `SYUNE_STUDY_ROOTS` must identify an existing approved directory and `SYUNE_STATE_DIR` selects the SYUNE state directory. Use the SYUNE project Python environment and working directory, with stdio transport.

The host registration is one `syune` entry in the host project's MCP configuration, using the SYUNE environment's Python executable, `-m syune.gateway.mcp`, and the environment variables above. The package is installed in the SYUNE environment, so the command also works from the host directory. The only host file changed was its project MCP configuration. No production prompts, routing, permissions, or control-core files were modified.

## Validation procedure

From the ART-DEP-AI host, list tools and call health, recall with a synthetic cue, then pass the returned candidate `typed_entity_id` directly to memory_get. The original bare `entity_id` and `entity_type` remain available for compatibility. Confirm entity type and provenance. Call source_status only when a known source ID is available. Disable or break the SYUNE command and verify the host's ordinary production path still works. Compare the host file inventory before and after; only the approved MCP registration may differ.

## Final result

Phase 06 passed. Root Claude Code discovered exactly the four read-only SYUNE tools. Health reported L1 ADVISORY, synthetic recall and direct `typed_entity_id` memory lookup succeeded, and provenance was preserved. With SYUNE disabled or unavailable, ART-DEP-AI continued normal read-only operation. The live result is recorded as `LIVE_SHADOW_HOST_TEST = PASS`.

The contract interoperability patch is commit `18f212c`. No SYUNE output changes production briefs, routing, agent authority, Review/HITL, Control Core, or production decisions. No automatic feedback learning is enabled, and the mutating Study tool remains unavailable to the shadow host.
