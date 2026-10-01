"""Opaque typed identifiers, UTC time, and bounded confidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from numbers import Real
from typing import Callable, Self
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class OpaqueId:
    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise TypeError("ID value must be a UUID")

    @classmethod
    def new(cls, factory: Callable[[], UUID] = uuid4) -> Self:
        return cls(factory())

    @classmethod
    def parse(cls, value: str) -> Self:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)


class MemoryId(OpaqueId):
    __slots__ = ()


class SourceId(OpaqueId):
    __slots__ = ()


class SourceVersionId(OpaqueId):
    __slots__ = ()


class ContentBlockId(OpaqueId):
    __slots__ = ()


class ObservationId(OpaqueId):
    __slots__ = ()


class ConceptId(OpaqueId):
    __slots__ = ()


class ClaimId(OpaqueId):
    __slots__ = ()


class EvidenceId(OpaqueId):
    __slots__ = ()


class EpisodeId(OpaqueId):
    __slots__ = ()


class ProcedureId(OpaqueId):
    __slots__ = ()


class AssociationId(OpaqueId):
    __slots__ = ()


class MemoryTraceId(OpaqueId):
    __slots__ = ()


class ProvenanceId(OpaqueId):
    __slots__ = ()


class ActivationRunId(OpaqueId):
    __slots__ = ()


class LearningSignalId(OpaqueId):
    __slots__ = ()


class LearningProposalId(OpaqueId):
    __slots__ = ()


class ConsolidationBatchId(OpaqueId):
    __slots__ = ()


class CognitiveRequestId(OpaqueId):
    __slots__ = ()


class InferenceId(OpaqueId):
    __slots__ = ()


class ResponseCandidateId(OpaqueId):
    __slots__ = ()


class ActivationProfileId(OpaqueId):
    __slots__ = ()

class PerceptionRunId(OpaqueId): __slots__=()
class PerceivedSegmentId(OpaqueId): __slots__=()
class DerivedArtifactId(OpaqueId): __slots__=()
class CouncilRequestId(OpaqueId): __slots__=()
class CouncilRunId(OpaqueId): __slots__=()
class CouncilAgreementId(OpaqueId): __slots__=()
class CouncilDisagreementId(OpaqueId): __slots__=()
class CouncilGapId(OpaqueId): __slots__=()
class CouncilSynthesisId(OpaqueId): __slots__=()
class ExecutiveRequestId(OpaqueId): __slots__=()
class GoalId(OpaqueId): __slots__=()
class PlanningAssumptionId(OpaqueId): __slots__=()
class ConstraintId(OpaqueId): __slots__=()
class PlanId(OpaqueId): __slots__=()
class PlanStepId(OpaqueId): __slots__=()
class PlanCheckpointId(OpaqueId): __slots__=()
class ActionProposalId(OpaqueId): __slots__=()
class RiskAssessmentId(OpaqueId): __slots__=()
class ApprovalEnvelopeId(OpaqueId): __slots__=()
class PolicyDecisionId(OpaqueId): __slots__=()
class CapabilityId(OpaqueId): __slots__=()
class ExecutionRequestId(OpaqueId): __slots__=()
class ExecutionId(OpaqueId): __slots__=()
class ApprovalTokenId(OpaqueId): __slots__=()
class VerificationId(OpaqueId): __slots__=()
class RollbackPlanId(OpaqueId): __slots__=()
class RollbackResultId(OpaqueId): __slots__=()
class ExecutionReceiptId(OpaqueId): __slots__=()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def require_utc(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be timezone-aware UTC")


@dataclass(frozen=True, slots=True)
class Confidence:
    """Evidence-state value, not an objective probability."""

    value: float

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, Real):
            raise TypeError("confidence must be a real number")
        if not isfinite(self.value) or not 0.0 <= self.value <= 1.0:
            raise ValueError("confidence must be finite and within [0, 1]")
