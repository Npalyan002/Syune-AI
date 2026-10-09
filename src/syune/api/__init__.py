"""Intentional public API v1 exports."""
from .capabilities import capability_summary
from .errors import ErrorCategory, SyuneError
from .model import *
from .serialization import canonical_json, to_primitive
from .version import MCP_CONTRACT_VERSION, PUBLIC_API_VERSION, SUPPORTED_PUBLIC_API_VERSIONS, negotiate_version

__all__ = [
    "PUBLIC_API_VERSION", "SUPPORTED_PUBLIC_API_VERSIONS", "MCP_CONTRACT_VERSION", "negotiate_version",
    "SyuneError", "ErrorCategory", "capability_summary", "canonical_json", "to_primitive",
    "RuntimeMode", "SideEffectClass", "DiagnosticsLevel", "ProvenanceMode", "TypedId", "HostSessionId", "CorrelationId",
    "HostContext", "StudyRequest", "RememberRequest", "AddMessage", "BatchAddRequest", "ReviseRequest", "RecallRequest", "ContextRequest", "CognitiveRequest", "CouncilRequest", "PlanRequest",
    "ExecutionRequest", "StudyResult", "SourceStatusResult", "MemoryResult", "RememberResult", "BatchAddResult", "RevisionResult", "HistoryResult", "ModelResult", "RecallResult", "ContextResult", "AuditResult", "CognitiveResult",
    "CouncilResult", "PlanResult", "ExecutionResult", "HealthResult", "StatusResult", "Capability",
    "CapabilitySummary", "SyuneHandshake",
]
