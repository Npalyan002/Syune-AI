"""Shared, provenance-aware structural Memory Kernel."""
from .model import (
    ActivationState, Association, Claim, Concept, Episode, Evidence,
    ContradictionKind, EvidencePolarity, MemoryTrace, Observation, Procedure, Provenance, Source,
    SourceLocator, TruthMetadata, TruthState,
)
from .repository import (
    DuplicateIdError, InMemoryReferenceRepository, MemoryRepository,
    MissingEndpointError,
)
from .sqlite_repository import SQLiteMemoryRepository
from .truth import (
    ALLOWED_TRANSITIONS, QueryMode, TruthAuditEvent, VerificationPolicy,
    classify_disagreement, temporally_eligible, validate_transition,
)
from .security import (
    AccessAuditEvent, AccessContext, AuthorizationDecision, AuthorizationDecisionCode,
    DefaultAccessPolicy, Principal, SecurityEnvelope, Sensitivity, authorize,
)
from .lifecycle import (LifecycleEvent, LifecycleMetrics, LifecycleRecord, LifecycleService,
    LifecycleState, MemoryClass, RetentionPolicy, RetentionRule, decay_priority, normalized_fingerprint)

__all__ = [
    "ActivationState", "Association", "Claim", "Concept", "Episode",
    "Evidence", "EvidencePolarity", "ContradictionKind", "MemoryTrace", "Observation", "Procedure",
    "Provenance", "Source", "SourceLocator", "TruthMetadata", "TruthState", "DuplicateIdError",
    "InMemoryReferenceRepository", "SQLiteMemoryRepository", "MemoryRepository", "MissingEndpointError",
    "ALLOWED_TRANSITIONS", "QueryMode", "TruthAuditEvent", "VerificationPolicy",
    "classify_disagreement", "temporally_eligible", "validate_transition",
    "AccessAuditEvent", "AccessContext", "AuthorizationDecision", "AuthorizationDecisionCode",
    "DefaultAccessPolicy", "Principal", "SecurityEnvelope", "Sensitivity", "authorize",
    "LifecycleEvent", "LifecycleMetrics", "LifecycleRecord", "LifecycleService", "LifecycleState",
    "MemoryClass", "RetentionPolicy", "RetentionRule", "decay_priority", "normalized_fingerprint",
]
