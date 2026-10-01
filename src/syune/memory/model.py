"""Typed memory data only. No retrieval, ingestion, or execution."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from numbers import Real

from syune.core import (
    AssociationId, ClaimId, ConceptId, Confidence, EpisodeId,
    EvidenceId, MemoryTraceId, ObservationId, ProcedureId, ProvenanceId, SourceId,
    SourceVersionId, require_utc,
)
from .security import SecurityEnvelope

SCHEMA_VERSION = "1"
TRUTH_SCHEMA_VERSION = "2"
NodeId = SourceId | ObservationId | ConceptId | ClaimId | EvidenceId | EpisodeId | ProcedureId | MemoryTraceId
DerivedId = ObservationId | ConceptId | ClaimId | EvidenceId | EpisodeId | ProcedureId


class TruthState(str, Enum):
    OBSERVED = "OBSERVED"
    ASSERTED = "ASSERTED"
    SUPPORTED = "SUPPORTED"
    VERIFIED = "VERIFIED"
    DISPUTED = "DISPUTED"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"


class ContradictionKind(str, Enum):
    NONE = "NONE"
    REVISION = "REVISION"
    CONTRADICTION = "CONTRADICTION"
    CONTEXTUAL_DIFFERENCE = "CONTEXTUAL_DIFFERENCE"
    UNCERTAINTY = "UNCERTAINTY"
    POSSIBLE_CONTRADICTION = "POSSIBLE_CONTRADICTION"


@dataclass(frozen=True, slots=True)
class TruthMetadata:
    """Optional v2 truth envelope. None fields mean unknown, never inferred."""
    state: TruthState = TruthState.OBSERVED
    recorded_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    revision_of: NodeId | None = None
    supersedes: tuple[NodeId, ...] = ()
    fact_key: str | None = None
    fact_value: str | None = None
    context_key: str | None = None
    contradiction: ContradictionKind = ContradictionKind.NONE
    schema_version: str = TRUTH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.state, TruthState) or not isinstance(self.contradiction, ContradictionKind):
            raise TypeError("typed truth state and contradiction kind required")
        if self.schema_version != TRUTH_SCHEMA_VERSION: raise ValueError("unsupported truth schema_version")
        for value in (self.recorded_at, self.valid_from, self.valid_until):
            if value is not None: require_utc(value)
        if self.valid_from is not None and self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        valid_ids = NodeId.__args__
        if self.revision_of is not None and not isinstance(self.revision_of, valid_ids):
            raise TypeError("revision_of must be a typed memory ID")
        if not isinstance(self.supersedes, tuple) or any(not isinstance(item, valid_ids) for item in self.supersedes):
            raise TypeError("supersedes must contain typed memory IDs")
        for name in ("fact_key", "fact_value", "context_key"):
            value = getattr(self, name)
            if value is not None: _text(value, name)


def _id(value: object, expected: type) -> None:
    if type(value) is not expected:
        raise TypeError(f"expected {expected.__name__}")


def _text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty")


def _schema(value: str) -> None:
    if value != SCHEMA_VERSION: raise ValueError("unsupported memory schema_version")


def _security(value: SecurityEnvelope | None) -> None:
    if value is not None and not isinstance(value, SecurityEnvelope):
        raise TypeError("security must be SecurityEnvelope or None")


def _derived(provenance: Provenance, confidence: Confidence, created_at: datetime, schema_version: str) -> None:
    if not isinstance(provenance, Provenance):
        raise ValueError("durable derived memory requires provenance")
    if not isinstance(confidence, Confidence):
        raise TypeError("durable derived memory requires Confidence")
    require_utc(created_at)
    _schema(schema_version)


@dataclass(frozen=True, slots=True)
class SourceLocator:
    page: int | None = None
    section: str | None = None
    timestamp_seconds: float | None = None
    block: str | None = None
    span: str | None = None
    region: str | None = None

    def __post_init__(self) -> None:
        if self.page is not None and (type(self.page) is not int or self.page < 1):
            raise ValueError("page must be a positive integer")
        for name in ("section", "block", "span", "region"):
            value = getattr(self, name)
            if value is not None:
                _text(value, name)
        if self.timestamp_seconds is not None:
            value = self.timestamp_seconds
            if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
                raise ValueError("timestamp_seconds must be finite and nonnegative")


@dataclass(frozen=True, slots=True)
class Provenance:
    id: ProvenanceId
    source_id: SourceId
    created_at: datetime
    source_version_id: SourceVersionId | None = None
    locator: SourceLocator | None = None
    process_id: str | None = None
    pipeline_version: str | None = None
    parent_provenance_ids: tuple[ProvenanceId, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _id(self.id, ProvenanceId)
        _id(self.source_id, SourceId)
        require_utc(self.created_at)
        if self.source_version_id is not None:
            _id(self.source_version_id, SourceVersionId)
        if self.locator is not None and not isinstance(self.locator, SourceLocator):
            raise TypeError("locator must be SourceLocator")
        for name in ("process_id", "pipeline_version"):
            value = getattr(self, name)
            if value is not None:
                _text(value, name)
        if not isinstance(self.parent_provenance_ids, tuple):
            raise TypeError("parent_provenance_ids must be a tuple")
        for parent in self.parent_provenance_ids:
            _id(parent, ProvenanceId)
        _schema(self.schema_version)


@dataclass(frozen=True, slots=True)
class Source:
    id: SourceId
    kind: str
    display_name: str
    registered_at: datetime
    source_version_id: SourceVersionId | None = None
    fingerprint: str | None = None
    locator_uri: str | None = None
    media_type: str | None = None
    schema_version: str = SCHEMA_VERSION
    security: SecurityEnvelope | None = None

    def __post_init__(self) -> None:
        _id(self.id, SourceId)
        _text(self.kind, "kind")
        _text(self.display_name, "display_name")
        require_utc(self.registered_at)
        if self.source_version_id is not None:
            _id(self.source_version_id, SourceVersionId)
        for name in ("fingerprint", "locator_uri", "media_type"):
            value = getattr(self, name)
            if value is not None:
                _text(value, name)
        _schema(self.schema_version)
        _security(self.security)


@dataclass(frozen=True, slots=True)
class Observation:
    """A perceived representation, never an assertion that its content is true."""

    id: ObservationId
    content: str
    content_kind: str
    provenance: Provenance
    observed_at: datetime
    created_at: datetime
    extraction_confidence: Confidence | None = None
    truth: TruthMetadata = TruthMetadata()
    schema_version: str = SCHEMA_VERSION
    security: SecurityEnvelope | None = None

    def __post_init__(self) -> None:
        _id(self.id, ObservationId)
        _text(self.content, "content")
        _text(self.content_kind, "content_kind")
        if not isinstance(self.provenance, Provenance):
            raise ValueError("source-derived observation requires provenance")
        require_utc(self.observed_at)
        require_utc(self.created_at)
        if self.extraction_confidence is not None and not isinstance(self.extraction_confidence, Confidence):
            raise TypeError("extraction_confidence must be Confidence or None")
        if not isinstance(self.truth, TruthMetadata): raise TypeError("truth must be TruthMetadata")
        _security(self.security)
        _schema(self.schema_version)


@dataclass(frozen=True, slots=True)
class Concept:
    id: ConceptId
    label: str
    provenance: Provenance
    confidence: Confidence
    created_at: datetime
    truth: TruthMetadata = TruthMetadata()
    schema_version: str = SCHEMA_VERSION
    security: SecurityEnvelope | None = None

    def __post_init__(self) -> None:
        _id(self.id, ConceptId)
        _text(self.label, "label")
        _derived(self.provenance, self.confidence, self.created_at, self.schema_version)
        if not isinstance(self.truth, TruthMetadata): raise TypeError("truth must be TruthMetadata")
        _security(self.security)


@dataclass(frozen=True, slots=True)
class Claim:
    id: ClaimId
    statement: str
    provenance: Provenance
    confidence: Confidence
    created_at: datetime
    truth: TruthMetadata = TruthMetadata(state=TruthState.ASSERTED)
    schema_version: str = SCHEMA_VERSION
    security: SecurityEnvelope | None = None

    def __post_init__(self) -> None:
        _id(self.id, ClaimId)
        _text(self.statement, "statement")
        _derived(self.provenance, self.confidence, self.created_at, self.schema_version)
        if not isinstance(self.truth, TruthMetadata): raise TypeError("truth must be TruthMetadata")
        _security(self.security)


class EvidencePolarity(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"


@dataclass(frozen=True, slots=True)
class Evidence:
    id: EvidenceId
    claim_ids: tuple[ClaimId, ...]
    polarity: EvidencePolarity
    summary: str
    provenance: Provenance
    confidence: Confidence
    created_at: datetime
    truth: TruthMetadata = TruthMetadata(state=TruthState.SUPPORTED)
    schema_version: str = SCHEMA_VERSION
    security: SecurityEnvelope | None = None

    def __post_init__(self) -> None:
        _id(self.id, EvidenceId)
        if not isinstance(self.claim_ids, tuple) or not self.claim_ids:
            raise ValueError("evidence needs one or more claim IDs")
        for claim_id in self.claim_ids:
            _id(claim_id, ClaimId)
        if not isinstance(self.polarity, EvidencePolarity):
            raise TypeError("polarity must be EvidencePolarity")
        _text(self.summary, "summary")
        _derived(self.provenance, self.confidence, self.created_at, self.schema_version)
        if not isinstance(self.truth, TruthMetadata): raise TypeError("truth must be TruthMetadata")
        _security(self.security)


@dataclass(frozen=True, slots=True)
class Episode:
    id: EpisodeId
    description: str
    occurred_at: datetime
    provenance: Provenance
    confidence: Confidence
    created_at: datetime
    truth: TruthMetadata = TruthMetadata()
    schema_version: str = SCHEMA_VERSION
    security: SecurityEnvelope | None = None

    def __post_init__(self) -> None:
        _id(self.id, EpisodeId)
        _text(self.description, "description")
        require_utc(self.occurred_at)
        _derived(self.provenance, self.confidence, self.created_at, self.schema_version)
        if not isinstance(self.truth, TruthMetadata): raise TypeError("truth must be TruthMetadata")
        _security(self.security)


@dataclass(frozen=True, slots=True)
class Procedure:
    id: ProcedureId
    steps: tuple[str, ...]
    provenance: Provenance
    confidence: Confidence
    created_at: datetime
    truth: TruthMetadata = TruthMetadata(state=TruthState.ASSERTED)
    schema_version: str = SCHEMA_VERSION
    security: SecurityEnvelope | None = None

    def __post_init__(self) -> None:
        _id(self.id, ProcedureId)
        if not isinstance(self.steps, tuple) or not self.steps:
            raise ValueError("procedure requires steps")
        for step in self.steps:
            _text(step, "step")
        _derived(self.provenance, self.confidence, self.created_at, self.schema_version)
        if not isinstance(self.truth, TruthMetadata): raise TypeError("truth must be TruthMetadata")
        _security(self.security)


@dataclass(frozen=True, slots=True)
class MemoryTrace:
    id: MemoryTraceId
    entity_id: DerivedId
    encoded_at: datetime
    provenance: Provenance
    confidence: Confidence
    created_at: datetime
    truth: TruthMetadata = TruthMetadata()
    schema_version: str = SCHEMA_VERSION
    security: SecurityEnvelope | None = None

    def __post_init__(self) -> None:
        _id(self.id, MemoryTraceId)
        if not isinstance(self.entity_id, (ObservationId, ConceptId, ClaimId, EvidenceId, EpisodeId, ProcedureId)):
            raise TypeError("trace must represent a typed derived entity")
        require_utc(self.encoded_at)
        _derived(self.provenance, self.confidence, self.created_at, self.schema_version)
        if not isinstance(self.truth, TruthMetadata): raise TypeError("truth must be TruthMetadata")
        _security(self.security)


@dataclass(frozen=True, slots=True)
class Association:
    id: AssociationId
    source_id: NodeId
    target_id: NodeId
    relation_type: str
    provenance: Provenance
    confidence: Confidence
    created_at: datetime
    strength: float | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _id(self.id, AssociationId)
        valid = (SourceId, ObservationId, ConceptId, ClaimId, EvidenceId, EpisodeId, ProcedureId, MemoryTraceId)
        if not isinstance(self.source_id, valid) or not isinstance(self.target_id, valid):
            raise TypeError("association endpoints must be typed node IDs")
        _text(self.relation_type, "relation_type")
        _derived(self.provenance, self.confidence, self.created_at, self.schema_version)
        if self.strength is not None:
            if isinstance(self.strength, bool) or not isinstance(self.strength, Real) or not isfinite(self.strength):
                raise ValueError("strength must be finite")


@dataclass(frozen=True, slots=True)
class ActivationState:
    """Transient data only: no propagation or ranking."""
    node_id: NodeId
    value: float
    activated_at: datetime
    cue_id: str | None = None

    def __post_init__(self) -> None:
        valid = (SourceId, ObservationId, ConceptId, ClaimId, EvidenceId, EpisodeId, ProcedureId, MemoryTraceId)
        if not isinstance(self.node_id, valid):
            raise TypeError("activation needs a typed node ID")
        if isinstance(self.value, bool) or not isinstance(self.value, Real) or not isfinite(self.value):
            raise ValueError("activation value must be finite")
        require_utc(self.activated_at)
        if self.cue_id is not None:
            _text(self.cue_id, "cue_id")
