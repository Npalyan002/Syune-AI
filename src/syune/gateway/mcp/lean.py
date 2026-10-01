"""Lean v1 MCP surface. Legacy cognitive MCP remains compatibility-only."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from syune import ContextRequest, RememberRequest, ReviseRequest, Syune, SyuneError, TypedId
from syune.api.serialization import to_primitive
from syune.release import RELEASE_VERSION

LEAN_TOOL_ALLOWLIST = frozenset({"syune_health", "syune_remember", "syune_context", "syune_revise",
                                 "syune_forget", "syune_history", "syune_audit", "syune_model"})


def create_lean_mcp_server(client: Syune) -> MCPServer:
    server = MCPServer("SYUNE", version=RELEASE_VERSION,
        instructions="SYUNE LEAN_V1: governed memory, context, audit, and reliable model access")

    def call(operation):
        try: return to_primitive(operation())
        except SyuneError as exc: raise ToolError(f"{exc.code}: {exc.message}") from exc
        except (ValueError, TypeError) as exc: raise ToolError(f"INVALID_REQUEST: {str(exc)[:160]}") from exc

    @server.tool(name="syune_health", structured_output=True)
    async def health(correlation_id: str | None = None) -> dict[str, object]:
        return call(lambda: client.health(correlation_id=correlation_id)) | {
            "product": "SYUNE", "runtime": "LEAN_V1", "version": RELEASE_VERSION,
            "tools": sorted(LEAN_TOOL_ALLOWLIST),
            "transport": "stdio", "experimental": ["research_compatibility"]}

    @server.tool(name="syune_remember", structured_output=True)
    async def remember(text: str, source_name: str = "direct-memory", correlation_id: str | None = None) -> dict[str, object]:
        return call(lambda: client.remember(RememberRequest(text, source_name, correlation_id=correlation_id)))

    @server.tool(name="syune_context", structured_output=True)
    async def context(cue: str, max_results: int = 8, provenance_mode: str = "STANDARD",
                      correlation_id: str | None = None) -> dict[str, object]:
        from syune import ProvenanceMode
        return call(lambda: client.context(ContextRequest(cue, max_results=max_results,
            correlation_id=correlation_id, provenance_mode=ProvenanceMode(provenance_mode))))

    @server.tool(name="syune_revise", structured_output=True)
    async def revise(memory_id: str, content: str, correlation_id: str | None = None) -> dict[str, object]:
        return call(lambda: client.revise(ReviseRequest(TypedId.parse(memory_id), content,
                                                         correlation_id=correlation_id)))

    @server.tool(name="syune_forget", structured_output=True)
    async def forget(memory_id: str, reason: str = "MCP request", correlation_id: str | None = None) -> dict[str, object]:
        return call(lambda: client.forget(memory_id, reason=reason, correlation_id=correlation_id))

    @server.tool(name="syune_history", structured_output=True)
    async def history(memory_id: str, correlation_id: str | None = None) -> dict[str, object]:
        return call(lambda: client.history(memory_id, correlation_id=correlation_id))

    @server.tool(name="syune_audit", structured_output=True)
    async def audit(limit: int = 100, correlation_id: str | None = None) -> dict[str, object]:
        return call(lambda: client.audit(limit=limit, correlation_id=correlation_id))

    @server.tool(name="syune_model", structured_output=True)
    async def model(logical_call_id: str, purpose: str, prompt: str) -> dict[str, object]:
        from syune.model_gateway import ModelExecutionRequest
        return call(lambda: client.model(ModelExecutionRequest(logical_call_id, purpose,
                                                                 ({"role":"user", "content":prompt},))))
    return server


__all__ = ["LEAN_TOOL_ALLOWLIST", "create_lean_mcp_server"]
