# MCP v1

MCP v1 is a local process-bound stdio surface started with `syune mcp serve` or `python -m syune.gateway.mcp`. Package version, public API version, and MCP contract version are separate fields in health/status. Normal errors are bounded stable codes and do not contain tracebacks.

| Tool | Class | Meaning |
| --- | --- | --- |
| `syune_health` | READ_ONLY | Component health and version metadata |
| `syune_status` | READ_ONLY | Runtime mode, autonomy, telemetry, versions |
| `syune_capabilities` | READ_ONLY | Mode-aware operation discovery |
| `syune_source_status` | READ_ONLY | Source/revision/materialization status |
| `syune_memory_get` | READ_ONLY | Public record by canonical typed ID |
| `syune_recall` | READ_ONLY | Bounded associative recall |
| `syune_cognize` | READ_ONLY | Bounded profile cognition |
| `syune_council` | READ_ONLY | Explicit multi-profile advisory Council |
| `syune_plan` | PLANNING_ONLY | Proposal-only L2 plan |
| `syune_study_source` | MEMORY_WRITE | Study an allowed local source |

NORMAL exposes all ten tools. SHADOW/read-only omits `syune_study_source`; capability discovery also marks Study unavailable. No MCP execution tool exists. A plan, action proposal, or approval envelope cannot cause execution through this transport.

Inputs obey SDK limits, typed ID rules, provenance semantics, configured-root path confinement, and correlation handling. SDK/MCP transport shapes differ where MCP uses JSON arguments, but health, recall, cognition, Council, and planning retain the same meanings.

Generic host configuration is in `examples/host_integration/mcp-config.json`; it uses environment placeholders and contains no repository or personal path. The server opens product state through the Phase 15 configuration layer and never gives the host a database handle.

Approval boundary: the host owns approval presentation, SYUNE owns verification, and plaintext confirmation is insufficient. Since execution is not public in v1, approval transport is documented by the host protocol for compatibility but no tool accepts an approval or bypass flag.
