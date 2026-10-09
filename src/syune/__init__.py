"""SYUNE: governed memory, context assembly, and reliable model access."""
from .release import RELEASE_VERSION as __version__

from .api import (
    PUBLIC_API_VERSION, AddMessage, AuditResult, BatchAddRequest, BatchAddResult, CapabilitySummary, ContextRequest, ContextResult, HistoryResult, ModelResult, RememberRequest, RememberResult, ReviseRequest, RevisionResult, ProvenanceMode, CognitiveRequest, CognitiveResult,
    CouncilRequest, CouncilResult, ErrorCategory, ExecutionRequest, ExecutionResult,
    HealthResult, HostContext, HostSessionId, CorrelationId, MemoryResult, PlanRequest,
    PlanResult, RecallRequest, RecallResult, RuntimeMode, SourceStatusResult, StatusResult,
    StudyRequest, StudyResult, SyuneError, SyuneHandshake, TypedId, canonical_json,
    negotiate_version,
)
from .sdk import Syune, SyuneClient
from .product.modes import LeanAssembly, LeanMode, context_only, full_lean, memory_context, memory_only, model_gateway_only

__all__ = [
    "__version__", "PUBLIC_API_VERSION", "Syune", "SyuneClient", "SyuneError", "ErrorCategory",
    "StudyRequest", "StudyResult", "RememberRequest", "RememberResult", "AddMessage", "BatchAddRequest", "BatchAddResult", "ReviseRequest", "RevisionResult", "ProvenanceMode", "SourceStatusResult", "MemoryResult", "HistoryResult", "ModelResult", "RecallRequest", "RecallResult", "ContextRequest", "ContextResult", "AuditResult",
    "CognitiveRequest", "CognitiveResult", "CouncilRequest", "CouncilResult", "PlanRequest", "PlanResult",
    "ExecutionRequest", "ExecutionResult", "HealthResult", "StatusResult", "CapabilitySummary",
    "SyuneHandshake", "TypedId", "RuntimeMode", "HostSessionId", "CorrelationId", "HostContext",
    "canonical_json", "negotiate_version",
    "LeanAssembly", "LeanMode", "context_only", "full_lean", "memory_context", "memory_only", "model_gateway_only",
]
