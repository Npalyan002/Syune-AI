"""Allowlisted public MCP v1 tools over the standalone SYUNE services."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime
from enum import Enum
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Iterator
from uuid import UUID, uuid4

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from syune.api.capabilities import capability_summary
from syune.api.model import RuntimeMode
from syune.api.serialization import to_primitive
from syune.api.version import MCP_CONTRACT_VERSION, PUBLIC_API_VERSION
from syune.cognition import CognitiveRequest, CognitiveService, ProfileName, ProfileRegistry
from syune.core import ClaimId, ConceptId, CouncilRequestId, CognitiveRequestId, EpisodeId, EvidenceId, ExecutiveRequestId, GoalId, MemoryTraceId, ObservationId, OpaqueId, ProcedureId, SourceId, utc_now
from syune.council import CouncilMemberSpec, CouncilRequest, CouncilService
from syune.executive import ExecutiveRequest, ExecutiveService, Goal, GoalSource
from syune.memory import AccessContext, MemoryRepository, Principal, SQLiteMemoryRepository, authorize
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalError, RetrievalService
from syune.study import SqliteStudyRegistry, StudyError, StudyService
from syune.release import RELEASE_VERSION

GATEWAY_VERSION = MCP_CONTRACT_VERSION
TOOL_ALLOWLIST = frozenset({"syune_health", "syune_status", "syune_capabilities", "syune_source_status",
                            "syune_memory_get", "syune_recall", "syune_cognize", "syune_council",
                            "syune_plan", "syune_study_source"})
ID_TYPES = {cls.__name__: cls for cls in (SourceId, ObservationId, ConceptId, ClaimId, EvidenceId, EpisodeId, ProcedureId, MemoryTraceId)}


def _correlation(value: str | None) -> str:
    if value is None: return str(uuid4())
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ToolError("INVALID_REQUEST: correlation_id must be 1..128 characters")
    return value


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    state_dir: Path
    study_roots: tuple[Path, ...]
    max_recall_results: int = 16
    shadow_read_only: bool = False
    memory_path: Path | None = None
    study_path: Path | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state_dir, Path) or not self.study_roots or any(not root.is_dir() for root in self.study_roots):
            raise ValueError("state directory and explicit existing Study roots required")
        if type(self.max_recall_results) is not int or not 1 <= self.max_recall_results <= 32:
            raise ValueError("max_recall_results must be 1..32")


@dataclass(slots=True)
class GatewayServices:
    memory: MemoryRepository
    registry: SqliteStudyRegistry
    study: StudyService
    retrieval: RetrievalService
    index: InvertedSeedIndex
    profiles: ProfileRegistry | None = None
    cognition: CognitiveService | None = None
    council: CouncilService | None = None
    planner: ExecutiveService | None = None


def _safe_path(raw: str, roots: tuple[Path, ...], must_exist: bool) -> Path:
    path = Path(raw)
    if not path.is_absolute() or ".." in path.parts:
        raise ToolError("SOURCE_OUTSIDE_ROOT: absolute child path without traversal required")
    try:
        resolved = path.resolve(strict=must_exist)
    except (FileNotFoundError, OSError) as exc:
        raise ToolError("SOURCE_NOT_FOUND: source unavailable") from exc
    if not any(resolved.is_relative_to(root.resolve(strict=True)) for root in roots):
        raise ToolError("SOURCE_OUTSIDE_ROOT: outside approved Study root")
    return resolved


def _typed_id(value: str):
    try:
        kind, raw = value.split(":", 1)
        return ID_TYPES[kind](UUID(raw))
    except (ValueError, KeyError, TypeError) as exc:
        raise ToolError("INVALID_TYPED_ID: expected TypeName:UUID") from exc


def _access(user_id=None, agent_id=None, organization_id=None, project_id=None,
            department_id=None, service_id=None, purpose=None, task_id=None):
    if not any((user_id, agent_id, service_id)): return None
    return AccessContext(Principal(user_id, agent_id, organization_id, project_id, department_id, service_id),
                         purpose, task_id, False)


def _plain(value):
    if isinstance(value, OpaqueId): return str(value)
    if isinstance(value, datetime): return value.isoformat()
    if isinstance(value, UUID): return str(value)
    if isinstance(value, Enum): return value.value
    if is_dataclass(value):
        return {item.name: _plain(getattr(value, item.name)) for item in fields(value) if item.name != "locator_uri"}
    if isinstance(value, tuple): return [_plain(item) for item in value]
    return value


def _recall_candidate(candidate) -> dict[str, object]:
    """Map a candidate without discarding its canonical typed ID class."""
    mapped = _plain(candidate)
    mapped["typed_entity_id"] = f"{type(candidate.entity_id).__name__}:{candidate.entity_id}"
    return mapped


def _status(status, study: StudyService) -> dict:
    if status is None: return {"known": False, "is_studied": False, "materialization": "NOT_ENCODED"}
    return {"known": True, "source_id": str(status.source_id), "revision_id": str(status.revision_id),
            "classification": status.classification.value, "state": status.state.value,
            "is_studied": status.is_studied, "materialization": study.materialization_status(status.revision_id).value,
            "sha256": status.sha256, "aliases_count": len(status.locators), "parser_version": status.parser_version,
            "pipeline_version": status.pipeline_version, "blocks_total": status.blocks_total,
            "blocks_encoded": status.blocks_encoded, "derived_memory_count": len(status.derived_memory_ids),
            "error_code": status.error_code, "first_seen": status.first_seen.isoformat(),
            "last_processed": status.last_processed.isoformat() if status.last_processed else None}


def create_syune_mcp_server(config: GatewayConfig, services: GatewayServices) -> MCPServer:
    def ensure_research() -> None:
        """Legacy tools load research services only when explicitly invoked."""
        services.profiles = services.profiles or ProfileRegistry()
        services.cognition = services.cognition or CognitiveService(services.memory, services.retrieval, services.profiles)
        services.council = services.council or CouncilService(services.cognition)
        services.planner = services.planner or ExecutiveService()
    mode = RuntimeMode.SHADOW if config.shadow_read_only else RuntimeMode.NORMAL
    server = MCPServer("SYUNE Research Compatibility", version=RELEASE_VERSION,
                       instructions="Deprecated research compatibility surface; not Lean v1 core")
    metrics: dict[str, list[float]] = {name: [] for name in TOOL_ALLOWLIST}

    def tracked(name, operation):
        start = perf_counter()
        try: return operation()
        except ToolError: raise
        except (StudyError, RetrievalError) as exc:
            raise ToolError(f"{exc.code.value}: {str(exc)[:160]}") from exc
        except (ValueError, TypeError) as exc:
            raise ToolError(f"INVALID_REQUEST: {str(exc)[:160]}") from exc
        except Exception as exc:
            code = getattr(getattr(exc, "code", None), "value", None)
            if code: raise ToolError(f"{code}: {str(exc)[:160]}") from exc
            raise ToolError("INTERNAL: operation failed") from exc
        finally: metrics[name].append((perf_counter() - start) * 1000)

    @server.tool(name="syune_health", structured_output=True)
    async def syune_health(correlation_id: str | None = None) -> dict[str, object]:
        return tracked("syune_health", lambda: {
            "service": "SYUNE Research Compatibility", "version": RELEASE_VERSION, "gateway_contract_version": GATEWAY_VERSION,
            "public_api_version": PUBLIC_API_VERSION, "autonomy_level": "RESEARCH_COMPATIBILITY_L3",
            "execution_mode": "ADVISORY_RESEARCH", "runtime_mode": mode.value, "memory": "available",
            "study_registry": "available", "retrieval_index": "available" if services.index.ready else "unavailable",
            "supported_study_formats": [".txt", ".md", ".markdown", ".pdf"], "transport": "stdio",
            "sdk_version": version("mcp"), "timestamp": utc_now().isoformat(),
            "degraded_components": [] if services.index.ready else ["retrieval_index"],
            "local_tool_calls": {key: len(value) for key, value in metrics.items()},
            "correlation_id": _correlation(correlation_id)})

    @server.tool(name="syune_status", structured_output=True)
    async def syune_status(correlation_id: str | None = None) -> dict[str, object]:
        return tracked("syune_status", lambda: {
            "package_version": RELEASE_VERSION, "public_api_version": PUBLIC_API_VERSION,
            "mcp_contract_version": GATEWAY_VERSION, "runtime_mode": mode.value,
            "autonomy_level": "RESEARCH_COMPATIBILITY_L3", "execution_exposed": False,
            "telemetry": "OFF", "correlation_id": _correlation(correlation_id),
        })

    @server.tool(name="syune_capabilities", structured_output=True)
    async def syune_capabilities(correlation_id: str | None = None) -> dict[str, object]:
        return tracked("syune_capabilities", lambda: to_primitive(capability_summary(mode)) | {
            "correlation_id": _correlation(correlation_id)})

    @server.tool(name="syune_source_status", structured_output=True)
    async def syune_source_status(fingerprint: str | None = None, source_id: str | None = None,
                                  path: str | None = None, correlation_id: str | None = None) -> dict[str, object]:
        def operation():
            if sum(value is not None for value in (fingerprint, source_id, path)) != 1:
                raise ToolError("INVALID_ARGUMENT: exactly one lookup key required")
            if fingerprint is not None:
                if len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint):
                    raise ToolError("INVALID_ARGUMENT: SHA-256 hex required")
                status = services.registry.by_fingerprint(fingerprint)
            elif source_id is not None:
                typed = _typed_id(source_id)
                if type(typed) is not SourceId: raise ToolError("INVALID_TYPED_ID: SourceId required")
                status = services.registry.by_source_id(typed)
            else:
                status = services.registry.by_locator(str(_safe_path(path, config.study_roots, False)))
            return _status(status, services.study) | {"correlation_id": _correlation(correlation_id)}
        return tracked("syune_source_status", operation)

    @server.tool(name="syune_memory_get", structured_output=True)
    async def syune_memory_get(entity_id: str, include_associations: bool = False,
                               correlation_id: str | None = None, user_id: str | None = None,
                               agent_id: str | None = None, organization_id: str | None = None,
                               project_id: str | None = None, department_id: str | None = None,
                               service_id: str | None = None, purpose: str | None = None,
                               task_id: str | None = None) -> dict[str, object]:
        def operation():
            typed = _typed_id(entity_id)
            entity = services.memory.get(typed)
            if entity is None: raise ToolError("MEMORY_NOT_FOUND: typed entity ID unavailable")
            context = _access(user_id, agent_id, organization_id, project_id, department_id,
                              service_id, purpose, task_id)
            if not authorize(getattr(entity, "security", None), context).allowed:
                raise ToolError("MEMORY_NOT_FOUND: typed entity ID unavailable")
            result = {"entity_type": type(entity).__name__, "id": str(entity.id), "fields": _plain(entity)}
            if include_associations:
                visible = []
                for edge in services.memory.associations_for(typed):
                    other_id = edge.target_id if edge.source_id == typed else edge.source_id
                    other = services.memory.get(other_id)
                    if other is not None and authorize(getattr(other, "security", None), context).allowed:
                        visible.append({"id": str(edge.id), "source_id": str(edge.source_id),
                                        "target_id": str(edge.target_id), "relation_type": edge.relation_type})
                    if len(visible) == 32: break
                result["associations"] = visible
            result["correlation_id"] = _correlation(correlation_id)
            return result
        return tracked("syune_memory_get", operation)

    @server.tool(name="syune_recall", structured_output=True)
    async def syune_recall(text: str | None = None, entity_ids: list[str] | None = None,
                     source_ids: list[str] | None = None, context_ids: list[str] | None = None,
                     max_results: int = 8, max_hops: int = 2, max_fanout: int = 16,
                     diagnostics: bool = True, correlation_id: str | None = None,
                     query_mode: str = "CURRENT", valid_at: str | None = None,
                     knowledge_at: str | None = None,
                     verification_policy: str = "PREFER_VERIFIED", user_id: str | None = None,
                     agent_id: str | None = None, organization_id: str | None = None,
                     project_id: str | None = None, department_id: str | None = None,
                     service_id: str | None = None, purpose: str | None = None,
                     task_id: str | None = None, include_archived: bool = False) -> dict[str, object]:
        def operation():
            if not 1 <= max_results <= config.max_recall_results or not 0 <= max_hops <= 3 or not 1 <= max_fanout <= 32:
                raise ToolError("INVALID_ARGUMENT: recall limit exceeded")
            sources = tuple(_typed_id(item) for item in (source_ids or ()))
            if any(type(item) is not SourceId for item in sources): raise ToolError("INVALID_TYPED_ID: SourceId required")
            cid = _correlation(correlation_id)
            from syune.retrieval import QueryMode, VerificationPolicy
            parse_time = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
            cue = RecallCue(text=text, entity_ids=tuple(_typed_id(item) for item in (entity_ids or ())),
                            source_ids=sources, context_ids=tuple(_typed_id(item) for item in (context_ids or ())),
                            correlation_id=cid, query_mode=QueryMode(query_mode), valid_at=parse_time(valid_at),
                            knowledge_at=parse_time(knowledge_at),
                            verification_policy=VerificationPolicy(verification_policy),
                            access_context=_access(user_id, agent_id, organization_id, project_id,
                                                   department_id, service_id, purpose, task_id),
                            include_archived=include_archived)
            service = RetrievalService(services.memory, services.index,
                replace(services.retrieval.config, max_hops=max_hops, max_fanout=max_fanout),
                services.retrieval.materialization_check)
            start = perf_counter()
            recalled = service.recall(RecallRequest(cue, max_results=max_results))
            mapped = {"request_id": str(recalled.request_id), "config_version": recalled.config_version,
                      "score_meaning": "relevance/activation, not truth probability",
                      "correlation_id": cid, "public_api_version": PUBLIC_API_VERSION,
                      "candidates": [_recall_candidate(item) for item in recalled.candidates],
                      "working_memory_ids": [str(item.entity_id) for item in recalled.working_memory],
                      "truncated": list(recalled.truncated), "service_ms": (perf_counter() - start) * 1000}
            if diagnostics:
                mapped["diagnostics"] = dict(recalled.diagnostics)
                mapped["timings_ms"] = dict(recalled.timings_ms)
            return mapped
        return tracked("syune_recall", operation)

    @server.tool(name="syune_cognize", structured_output=True)
    async def syune_cognize(text: str, profile: str = "GENERAL",
                            correlation_id: str | None = None, user_id: str | None = None,
                            agent_id: str | None = None, organization_id: str | None = None,
                            project_id: str | None = None, department_id: str | None = None,
                            service_id: str | None = None, purpose: str | None = None,
                            task_id: str | None = None) -> dict[str, object]:
        def operation():
            ensure_research()
            cid = _correlation(correlation_id)
            selected = services.profiles.by_name(ProfileName(profile.upper()))
            request = CognitiveRequest(CognitiveRequestId.new(), text, correlation_id=cid,
                                       activation_profile=selected.id,
                                       access_context=_access(user_id, agent_id, organization_id, project_id,
                                                              department_id, service_id, purpose, task_id))
            result = to_primitive(services.cognition.process(request))
            result["correlation_id"] = cid
            result["public_api_version"] = PUBLIC_API_VERSION
            return result
        return tracked("syune_cognize", operation)

    @server.tool(name="syune_council", structured_output=True)
    async def syune_council(text: str, members: list[str] | None = None,
                           correlation_id: str | None = None) -> dict[str, object]:
        def operation():
            ensure_research()
            cid = _correlation(correlation_id)
            names = members or ["GENERAL", "RESEARCH"]
            profile_ids = tuple(services.profiles.by_name(ProfileName(name.upper())).id for name in names)
            cognitive = CognitiveRequest(CognitiveRequestId.new(), text, correlation_id=cid)
            request = CouncilRequest(CouncilRequestId.new(), cognitive,
                tuple(CouncilMemberSpec(item) for item in profile_ids), correlation_id=cid)
            result = to_primitive(services.council.run(request))
            result["correlation_id"] = cid
            result["agreement_meaning"] = "structural convergence, not truth probability"
            result["public_api_version"] = PUBLIC_API_VERSION
            return result
        return tracked("syune_council", operation)

    @server.tool(name="syune_plan", structured_output=True)
    async def syune_plan(goal: str, success_criteria: list[str] | None = None,
                         correlation_id: str | None = None) -> dict[str, object]:
        def operation():
            ensure_research()
            cid = _correlation(correlation_id)
            typed_goal = Goal(GoalId.new(), goal, tuple(success_criteria or ()), source=GoalSource.HOST,
                              correlation_id=cid)
            request = ExecutiveRequest(ExecutiveRequestId.new(), typed_goal, correlation_id=cid)
            result = to_primitive(services.planner.plan(request))
            result["correlation_id"] = cid
            result["execution_authority"] = False
            result["approval_does_not_execute"] = True
            result["public_api_version"] = PUBLIC_API_VERSION
            return result
        return tracked("syune_plan", operation)

    if not config.shadow_read_only:
        @server.tool(name="syune_study_source", structured_output=True)
        async def syune_study_source(path: str, correlation_id: str | None = None) -> dict[str, object]:
            def operation():
                resolved = _safe_path(path, config.study_roots, True)
                if resolved.suffix.lower() not in {".txt", ".md", ".markdown", ".pdf"}:
                    raise ToolError("UNSUPPORTED_FORMAT: local text format required")
                if not resolved.is_file(): raise ToolError("SOURCE_NOT_FOUND: regular file required")
                result = services.study.study(resolved)
                services.index.sync()
                mapped = _status(result.status, services.study)
                mapped["classification"] = result.classification.value
                mapped["correlation_id"] = _correlation(correlation_id)
                mapped["public_api_version"] = PUBLIC_API_VERSION
                return mapped
            return tracked("syune_study_source", operation)

    assert set(metrics) == TOOL_ALLOWLIST
    return server


@contextmanager
def open_gateway(config: GatewayConfig) -> Iterator[tuple[MCPServer, GatewayServices]]:
    config.state_dir.mkdir(parents=True, exist_ok=True)
    with SQLiteMemoryRepository(config.memory_path or config.state_dir / "memory.sqlite3") as memory, \
         SqliteStudyRegistry(config.study_path or config.state_dir / "study.sqlite3") as registry:
        index = InvertedSeedIndex(memory)
        index.rebuild()
        study = StudyService(registry, memory)
        def materialization(source_id: SourceId) -> str | None:
            status = registry.by_source_id(source_id)
            return study.materialization_status(status.revision_id).value if status else None
        retrieval = RetrievalService(memory, index, materialization_check=materialization)
        services = GatewayServices(memory, registry, study, retrieval, index)
        yield create_syune_mcp_server(config, services), services
