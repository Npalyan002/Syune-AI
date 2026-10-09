"""Transport-neutral public v1 request and response contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def _correlation(value: str | None) -> str:
    if value is None:
        return str(uuid4())
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError("correlation_id must be 1..128 characters")
    return value


class RuntimeMode(str, Enum):
    NORMAL = "NORMAL"
    READ_ONLY = "READ_ONLY"
    SHADOW = "SHADOW"
    TEST = "TEST"


class SideEffectClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    MEMORY_WRITE = "MEMORY_WRITE"
    PLANNING_ONLY = "PLANNING_ONLY"
    SIDE_EFFECTING = "SIDE_EFFECTING"


class DiagnosticsLevel(str, Enum):
    NONE = "NONE"
    BASIC = "BASIC"
    FULL = "FULL"

class ProvenanceMode(str, Enum):
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    FULL = "FULL"


@dataclass(frozen=True, slots=True)
class TypedId:
    entity_type: str
    value: str

    def __post_init__(self) -> None:
        if not self.entity_type or not self.entity_type.endswith("Id"):
            raise ValueError("typed ID entity_type must end with Id")
        UUID(self.value)

    @classmethod
    def parse(cls, value: str) -> "TypedId":
        try:
            kind, raw = value.split(":", 1)
            return cls(kind, raw)
        except (AttributeError, ValueError) as exc:
            raise ValueError("typed ID must be TypeNameId:UUID") from exc

    def __str__(self) -> str:
        return f"{self.entity_type}:{self.value}"


@dataclass(frozen=True, slots=True)
class HostSessionId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip() or len(self.value) > 128: raise ValueError("invalid host session ID")


@dataclass(frozen=True, slots=True)
class CorrelationId:
    value: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        _correlation(self.value)


@dataclass(frozen=True, slots=True)
class HostContext:
    session_id: HostSessionId | None = None
    task_id: str | None = None
    correlation_id: CorrelationId | None = None
    locale: str | None = None
    timezone: str | None = None
    context_references: tuple[TypedId, ...] = ()
    host_capabilities: tuple[str, ...] = ()
    approval_channel_available: bool = False


@dataclass(frozen=True, slots=True)
class StudyRequest:
    path: str
    correlation_id: str | None = None

@dataclass(frozen=True, slots=True)
class RememberRequest:
    text: str
    source_name: str = "direct-memory"
    owner: str | None = None
    allowed_principals: tuple[str, ...] = ()
    correlation_id: str | None = None
    observed_at: str | None = None


@dataclass(frozen=True, slots=True)
class AddMessage:
    ordinal: int
    text: str
    observed_at: str | None = None
    source_name: str = "agent-memory"


@dataclass(frozen=True, slots=True)
class BatchAddRequest:
    request_id: str
    user_id: str
    session_id: str
    messages: tuple[AddMessage, ...]
    correlation_id: str | None = None

@dataclass(frozen=True, slots=True)
class ReviseRequest:
    memory_id: TypedId
    content: str
    correlation_id: str | None = None
    valid_from: str | None = None
    user_id: str | None = None
    agent_id: str | None = None
    organization_id: str | None = None
    project_id: str | None = None
    department_id: str | None = None
    service_id: str | None = None
    purpose: str | None = None


@dataclass(frozen=True, slots=True)
class RecallRequest:
    cue: str | None = None
    entity_ids: tuple[TypedId, ...] = ()
    source_ids: tuple[TypedId, ...] = ()
    context_ids: tuple[TypedId, ...] = ()
    max_results: int = 8
    diagnostics: DiagnosticsLevel = DiagnosticsLevel.BASIC
    correlation_id: str | None = None
    query_mode: str = "CURRENT"
    valid_at: str | None = None
    knowledge_at: str | None = None
    verification_policy: str = "PREFER_VERIFIED"
    user_id: str | None = None
    agent_id: str | None = None
    organization_id: str | None = None
    project_id: str | None = None
    department_id: str | None = None
    service_id: str | None = None
    purpose: str | None = None
    task_id: str | None = None
    include_archived: bool = False

@dataclass(frozen=True, slots=True)
class ContextRequest:
    cue: str
    max_results: int = 8
    max_chars: int = 8_000
    correlation_id: str | None = None
    query_mode: str = "CURRENT"
    valid_at: str | None = None
    knowledge_at: str | None = None
    verification_policy: str = "PREFER_VERIFIED"
    user_id: str | None = None
    agent_id: str | None = None
    organization_id: str | None = None
    project_id: str | None = None
    department_id: str | None = None
    service_id: str | None = None
    purpose: str | None = None
    task_id: str | None = None
    provenance_mode: ProvenanceMode = ProvenanceMode.STANDARD


@dataclass(frozen=True, slots=True)
class CognitiveRequest:
    cue: str | None = None
    entity_ids: tuple[TypedId, ...] = ()
    source_ids: tuple[TypedId, ...] = ()
    context_ids: tuple[TypedId, ...] = ()
    profile: str = "GENERAL"
    diagnostics: DiagnosticsLevel = DiagnosticsLevel.BASIC
    correlation_id: str | None = None
    user_id: str | None = None
    agent_id: str | None = None
    organization_id: str | None = None
    project_id: str | None = None
    department_id: str | None = None
    service_id: str | None = None
    purpose: str | None = None
    task_id: str | None = None


@dataclass(frozen=True, slots=True)
class CouncilRequest:
    cue: str
    members: tuple[str, ...] = ("GENERAL", "RESEARCH")
    diagnostics: DiagnosticsLevel = DiagnosticsLevel.BASIC
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class PlanRequest:
    goal: str
    success_criteria: tuple[str, ...] = ()
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    plan_id: TypedId
    plan_version: int
    proposal_ids: tuple[TypedId, ...]
    approval_reference: str
    runtime_budget: dict[str, Any]
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if self.plan_id.entity_type != "PlanId" or self.plan_version < 1:
            raise ValueError("valid PlanId and positive plan_version required")
        if not self.proposal_ids or any(item.entity_type != "ActionProposalId" for item in self.proposal_ids):
            raise ValueError("exact ActionProposalId set required")
        if not self.approval_reference.strip() or not self.runtime_budget:
            raise ValueError("approval reference and runtime budget required")


@dataclass(frozen=True, slots=True)
class PublicResult:
    correlation_id: str
    data: dict[str, Any]
    public_api_version: str = "1"


class StudyResult(PublicResult): pass
class SourceStatusResult(PublicResult): pass
class MemoryResult(PublicResult): pass
class RememberResult(PublicResult): pass
class BatchAddResult(PublicResult): pass
class RevisionResult(PublicResult): pass
class HistoryResult(PublicResult): pass
class ModelResult(PublicResult): pass
class RecallResult(PublicResult): pass
class ContextResult(PublicResult): pass
class AuditResult(PublicResult): pass
class CognitiveResult(PublicResult): pass
class CouncilResult(PublicResult): pass
class PlanResult(PublicResult): pass
class ExecutionResult(PublicResult): pass


@dataclass(frozen=True, slots=True)
class HealthResult(PublicResult):
    pass


@dataclass(frozen=True, slots=True)
class StatusResult(PublicResult):
    pass


@dataclass(frozen=True, slots=True)
class Capability:
    operation: str
    available: bool
    version: str
    side_effect_class: SideEffectClass
    approval_required: bool
    locality: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilitySummary:
    runtime_mode: RuntimeMode
    capabilities: tuple[Capability, ...]
    public_api_version: str = "1"


@dataclass(frozen=True, slots=True)
class SyuneHandshake:
    package_version: str
    supported_public_api_versions: tuple[str, ...]
    selected_version: str
    state_schema: int
    autonomy_level: str
    capabilities: CapabilitySummary
    runtime_mode: RuntimeMode
    health_summary: str


__all__ = [
    "RuntimeMode", "SideEffectClass", "DiagnosticsLevel", "ProvenanceMode", "TypedId", "HostSessionId", "CorrelationId",
    "HostContext", "StudyRequest", "RememberRequest", "AddMessage", "BatchAddRequest", "ReviseRequest", "RecallRequest", "ContextRequest", "CognitiveRequest", "CouncilRequest", "PlanRequest",
    "ExecutionRequest", "PublicResult", "StudyResult", "SourceStatusResult", "MemoryResult", "RecallResult",
    "RememberResult", "BatchAddResult", "RevisionResult", "HistoryResult", "ModelResult", "ContextResult", "AuditResult", "CognitiveResult", "CouncilResult", "PlanResult", "ExecutionResult", "HealthResult", "StatusResult",
    "Capability", "CapabilitySummary", "SyuneHandshake",
]
