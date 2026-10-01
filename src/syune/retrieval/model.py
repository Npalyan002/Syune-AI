"""Typed request and explanation contracts for transient associative recall."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from math import isfinite
from typing import Protocol

from syune.core import OpaqueId, SourceId, require_utc
from syune.memory.model import ContradictionKind, NodeId, SourceLocator, TruthState
from syune.memory.truth import QueryMode, VerificationPolicy
from syune.memory.security import AccessContext, AuthorizationDecisionCode


class RetrievalRunId(OpaqueId):
    __slots__ = ()


class RetrievalErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    EMPTY_CUE = "EMPTY_CUE"
    MISSING_ENTITY = "MISSING_ENTITY"
    INDEX_UNAVAILABLE = "INDEX_UNAVAILABLE"
    INCOMPATIBLE_INDEX = "INCOMPATIBLE_INDEX"
    DEGRADED_MATERIALIZATION = "DEGRADED_MATERIALIZATION"
    REPOSITORY_FAILURE = "REPOSITORY_FAILURE"
    INVALID_CONFIG = "INVALID_CONFIG"


class RetrievalError(Exception):
    def __init__(self, code: RetrievalErrorCode, message: str):
        self.code = code
        super().__init__(message)


class PlasticityView(Protocol):
    """Narrow read-only learned-state view; Retrieval owns no learning storage."""
    def utility_adjustment(self, entity_id: NodeId) -> float: ...
    def salience_adjustment(self, entity_id: NodeId) -> float: ...
    def association_adjustment(self, source_id: NodeId, target_id: NodeId) -> float: ...


class NullPlasticityView:
    def utility_adjustment(self, entity_id: NodeId) -> float: return 0.0
    def salience_adjustment(self, entity_id: NodeId) -> float: return 0.0
    def association_adjustment(self, source_id: NodeId, target_id: NodeId) -> float: return 0.0


@dataclass(frozen=True, slots=True)
class RecallCue:
    text: str | None = None
    entity_ids: tuple[NodeId, ...] = ()
    source_ids: tuple[SourceId, ...] = ()
    context_ids: tuple[NodeId, ...] = ()
    temporal_context: datetime | None = None
    correlation_id: str | None = None
    query_mode: QueryMode = QueryMode.CURRENT
    valid_at: datetime | None = None
    knowledge_at: datetime | None = None
    verification_policy: VerificationPolicy = VerificationPolicy.PREFER_VERIFIED
    access_context: AccessContext | None = None
    include_archived: bool = False

    def __post_init__(self) -> None:
        if not (self.text and self.text.strip()) and not self.entity_ids and not self.source_ids and not self.context_ids:
            raise RetrievalError(RetrievalErrorCode.EMPTY_CUE, "cue needs text or typed IDs")
        for ids in (self.entity_ids, self.context_ids):
            if not isinstance(ids, tuple) or any(not isinstance(x, NodeId.__args__) for x in ids):
                raise RetrievalError(RetrievalErrorCode.INVALID_REQUEST, "typed memory IDs required")
        if not isinstance(self.source_ids, tuple) or any(type(x) is not SourceId for x in self.source_ids):
            raise RetrievalError(RetrievalErrorCode.INVALID_REQUEST, "typed SourceIds required")
        if self.temporal_context is not None:
            require_utc(self.temporal_context)
        if not isinstance(self.query_mode, QueryMode) or not isinstance(self.verification_policy, VerificationPolicy):
            raise RetrievalError(RetrievalErrorCode.INVALID_REQUEST, "typed temporal and verification policies required")
        for value in (self.valid_at, self.knowledge_at):
            if value is not None: require_utc(value)
        if self.query_mode is not QueryMode.CURRENT and self.valid_at is None:
            raise RetrievalError(RetrievalErrorCode.INVALID_REQUEST, "historical/as-of recall requires valid_at")
        if self.access_context is not None and not isinstance(self.access_context, AccessContext):
            raise RetrievalError(RetrievalErrorCode.INVALID_REQUEST, "AccessContext required")
        if type(self.include_archived) is not bool:
            raise RetrievalError(RetrievalErrorCode.INVALID_REQUEST, "include_archived must be bool")


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    version: str = "1"
    max_lexical_seeds: int = 32
    max_explicit_seeds: int = 32
    max_hops: int = 2
    max_fanout: int = 16
    max_edges: int = 512
    max_candidates: int = 256
    max_results: int = 16
    working_memory_capacity: int = 8
    hop_decay: float = 0.6
    minimum_activation: float = 0.01
    fanout_normalization: bool = False
    pattern_min_support: int = 2
    pattern_bonus: float = 0.5
    source_diversity: bool = False
    weights: tuple[tuple[str, float], ...] = (
        ("seed", 1.0), ("activation", 1.0), ("salience", 0.2),
        ("context", 1.0), ("confidence", 0.1), ("recency", 0.1),
        ("provenance", 0.1), ("pattern", 1.0),
    )

    def __post_init__(self) -> None:
        ints = ("max_lexical_seeds", "max_explicit_seeds", "max_fanout", "max_edges",
                "max_candidates", "max_results", "working_memory_capacity", "pattern_min_support")
        if any(type(getattr(self, name)) is not int or getattr(self, name) < 1 for name in ints):
            raise RetrievalError(RetrievalErrorCode.INVALID_CONFIG, "limits must be positive integers")
        if type(self.max_hops) is not int or self.max_hops < 0:
            raise RetrievalError(RetrievalErrorCode.INVALID_CONFIG, "max_hops must be nonnegative")
        if not 0 < self.hop_decay <= 1 or not 0 <= self.minimum_activation <= 1:
            raise RetrievalError(RetrievalErrorCode.INVALID_CONFIG, "invalid activation configuration")
        if self.pattern_bonus < 0 or not isfinite(self.pattern_bonus):
            raise RetrievalError(RetrievalErrorCode.INVALID_CONFIG, "invalid pattern bonus")
        expected = {"seed", "activation", "salience", "context", "confidence", "recency", "provenance", "pattern"}
        if {key for key, _ in self.weights} != expected or len(self.weights) != len(expected) or any(
                not isfinite(value) or value < 0 for _, value in self.weights):
            raise RetrievalError(RetrievalErrorCode.INVALID_CONFIG, "invalid score weights")


@dataclass(frozen=True, slots=True)
class RecallRequest:
    cue: RecallCue
    request_id: RetrievalRunId = field(default_factory=RetrievalRunId.new)
    max_results: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.cue, RecallCue) or type(self.request_id) is not RetrievalRunId:
            raise RetrievalError(RetrievalErrorCode.INVALID_REQUEST, "typed cue and request ID required")
        if self.max_results is not None and (type(self.max_results) is not int or self.max_results < 1):
            raise RetrievalError(RetrievalErrorCode.INVALID_REQUEST, "max_results must be positive")


@dataclass(frozen=True, slots=True)
class RecallCandidate:
    entity_id: NodeId
    entity_type: str
    rank: int
    score: float
    components: tuple[tuple[str, float], ...]
    activation: float
    seed_reasons: tuple[str, ...]
    association_paths: tuple[tuple[str, ...], ...]
    source_id: SourceId | None
    locator: SourceLocator | None
    confidence: float | None
    lexical_tokens: tuple[str, ...]
    pattern_support: int
    truth_state: TruthState | None = None
    contradiction: ContradictionKind = ContradictionKind.NONE
    temporally_valid: bool = True
    provenance_valid: bool = True
    authorization: AuthorizationDecisionCode | None = None
    found_by: tuple[str, ...] = ()
    fusion_score: float = 0.0


@dataclass(frozen=True, slots=True)
class RecallResult:
    request_id: RetrievalRunId
    candidates: tuple[RecallCandidate, ...]
    working_memory: tuple[RecallCandidate, ...]
    diagnostics: tuple[tuple[str, int | float | str], ...]
    timings_ms: tuple[tuple[str, float], ...]
    truncated: tuple[str, ...]
    config_version: str
    evidence_status: str = "SUFFICIENT_EVIDENCE"
    route: tuple[str, ...] = ()
