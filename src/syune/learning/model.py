"""Typed, immutable contracts for explicit adaptive learning."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite

from syune.core import (
    AssociationId, ConsolidationBatchId, LearningProposalId, LearningSignalId,
    OpaqueId, ProvenanceId, SourceId, require_utc,
)
from syune.memory.model import NodeId

SCHEMA_VERSION = "1"


class LearningSignalKind(str, Enum):
    CO_ACTIVATION = "CO_ACTIVATION"
    POSITIVE_OUTCOME = "POSITIVE_OUTCOME"
    NEGATIVE_OUTCOME = "NEGATIVE_OUTCOME"
    HUMAN_FEEDBACK = "HUMAN_FEEDBACK"
    SOURCE_RETRACTION_NOTICE = "SOURCE_RETRACTION_NOTICE"


class LearningSource(str, Enum):
    HUMAN = "HUMAN"
    SYSTEM_TEST = "SYSTEM_TEST"
    EXTERNAL_CALLER = "EXTERNAL_CALLER"
    FUTURE_AGENT = "FUTURE_AGENT"


class FeedbackLabel(str, Enum):
    USEFUL = "USEFUL"
    NOT_USEFUL = "NOT_USEFUL"
    RELEVANT = "RELEVANT"
    NOT_RELEVANT = "NOT_RELEVANT"
    CORRECT_IN_CONTEXT = "CORRECT_IN_CONTEXT"
    INCORRECT_IN_CONTEXT = "INCORRECT_IN_CONTEXT"


class LearningStatus(str, Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    ROLLED_BACK = "ROLLED_BACK"


class TargetKind(str, Enum):
    ENTITY = "ENTITY"
    ASSOCIATION = "ASSOCIATION"
    CO_ACTIVATION = "CO_ACTIVATION"


@dataclass(frozen=True, slots=True)
class LearningTarget:
    id: NodeId | AssociationId

    def __post_init__(self) -> None:
        if not isinstance(self.id, OpaqueId):
            raise TypeError("learning target requires a typed canonical ID")

    @property
    def key(self) -> str:
        return f"{type(self.id).__name__}:{self.id}"


@dataclass(frozen=True, slots=True)
class LearningSignal:
    id: LearningSignalId
    kind: LearningSignalKind
    occurred_at: datetime
    targets: tuple[LearningTarget, ...]
    source: LearningSource
    idempotency_key: str
    provenance_id: ProvenanceId
    correlation_id: str | None = None
    context_ids: tuple[NodeId, ...] = ()
    outcome_value: float | None = None
    feedback_label: FeedbackLabel | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.id) is not LearningSignalId or not isinstance(self.kind, LearningSignalKind):
            raise TypeError("typed signal identity and kind required")
        require_utc(self.occurred_at)
        if not self.targets or len(self.targets) > 32 or any(not isinstance(x, LearningTarget) for x in self.targets):
            raise ValueError("1..32 typed targets required")
        if not isinstance(self.source, LearningSource) or type(self.provenance_id) is not ProvenanceId:
            raise TypeError("explicit source and provenance required")
        if not isinstance(self.idempotency_key, str) or not self.idempotency_key.strip() or len(self.idempotency_key) > 200:
            raise ValueError("bounded idempotency key required")
        if self.outcome_value is not None and (not isfinite(self.outcome_value) or not -1 <= self.outcome_value <= 1):
            raise ValueError("outcome value must be within [-1,1]")
        if self.kind is LearningSignalKind.CO_ACTIVATION and len(self.targets) != 2:
            raise ValueError("co-activation requires exactly two targets")
        if self.kind is LearningSignalKind.HUMAN_FEEDBACK and self.feedback_label is None:
            raise ValueError("human feedback label required")
        if self.kind is LearningSignalKind.HUMAN_FEEDBACK and self.source is not LearningSource.HUMAN:
            raise ValueError("human feedback requires explicit HUMAN source")
        if self.kind is LearningSignalKind.SOURCE_RETRACTION_NOTICE and (
                len(self.targets) != 1 or type(self.targets[0].id) is not SourceId):
            raise ValueError("source retraction requires one SourceId")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported learning schema")


@dataclass(frozen=True, slots=True)
class PlasticityState:
    target_key: str
    target_kind: TargetKind
    utility_delta: float = 0.0
    salience_delta: float = 0.0
    association_delta: float = 0.0
    retraction_flag: bool = False
    update_count: int = 0
    updated_at: datetime | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION or not isinstance(self.target_kind, TargetKind) or not self.target_key:
            raise ValueError("invalid overlay metadata")
        if any(not isfinite(v) or abs(v)>1 for v in (self.utility_delta,self.salience_delta,self.association_delta)):
            raise ValueError("invalid overlay bounds")
        if type(self.update_count) is not int or self.update_count<0:
            raise ValueError("invalid overlay update count")
        if self.updated_at is not None: require_utc(self.updated_at)


@dataclass(frozen=True, slots=True)
class LearningProposal:
    id: LearningProposalId
    signal_id: LearningSignalId
    target_key: str
    target_kind: TargetKind
    before: PlasticityState
    after: PlasticityState
    reason: str
    policy_version: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ConsolidationBatch:
    id: ConsolidationBatchId
    started_at: datetime
    completed_at: datetime
    policy_version: str
    signal_ids: tuple[LearningSignalId, ...]
    proposal_ids: tuple[LearningProposalId, ...]
    applied_count: int
    skipped_count: int
    checksum: str
    total_ms: float
    status: LearningStatus = LearningStatus.APPLIED


@dataclass(frozen=True, slots=True)
class ConsolidationResult:
    batch: ConsolidationBatch
    proposals: tuple[LearningProposal, ...]
    deferred_signals: int
    proposal_ms: float
    apply_ms: float
