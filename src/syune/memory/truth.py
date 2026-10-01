"""Deterministic Phase 19 truth, temporal, lineage, and contradiction rules."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .model import ContradictionKind, TruthMetadata, TruthState


class QueryMode(str, Enum):
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    AS_OF = "AS_OF"


class VerificationPolicy(str, Enum):
    ALLOW_UNVERIFIED = "ALLOW_UNVERIFIED"
    PREFER_VERIFIED = "PREFER_VERIFIED"
    VERIFIED_ONLY = "VERIFIED_ONLY"


ALLOWED_TRANSITIONS = {
    TruthState.OBSERVED: {TruthState.ASSERTED, TruthState.SUPPORTED, TruthState.VERIFIED, TruthState.DISPUTED, TruthState.INVALIDATED},
    TruthState.ASSERTED: {TruthState.SUPPORTED, TruthState.VERIFIED, TruthState.DISPUTED, TruthState.SUPERSEDED, TruthState.INVALIDATED},
    TruthState.SUPPORTED: {TruthState.VERIFIED, TruthState.DISPUTED, TruthState.SUPERSEDED, TruthState.INVALIDATED},
    TruthState.VERIFIED: {TruthState.DISPUTED, TruthState.SUPERSEDED, TruthState.INVALIDATED},
    TruthState.DISPUTED: {TruthState.SUPPORTED, TruthState.VERIFIED, TruthState.SUPERSEDED, TruthState.INVALIDATED},
    TruthState.SUPERSEDED: set(),
    TruthState.INVALIDATED: set(),
}


@dataclass(frozen=True, slots=True)
class TruthAuditEvent:
    event_type: str
    entity_id: object
    occurred_at: datetime
    prior_state: TruthState | None
    new_state: TruthState
    reason: str


def validate_transition(prior: TruthState, new: TruthState) -> None:
    if new is not prior and new not in ALLOWED_TRANSITIONS[prior]:
        raise ValueError(f"invalid truth transition: {prior.value} -> {new.value}")


def overlaps(left: TruthMetadata, right: TruthMetadata) -> bool:
    return not ((left.valid_until is not None and right.valid_from is not None and left.valid_until <= right.valid_from)
                or (right.valid_until is not None and left.valid_from is not None and right.valid_until <= left.valid_from))


def classify_disagreement(left: TruthMetadata, right: TruthMetadata) -> ContradictionKind:
    if not left.fact_key or left.fact_key != right.fact_key or left.fact_value is None or right.fact_value is None:
        return ContradictionKind.POSSIBLE_CONTRADICTION
    if left.context_key != right.context_key:
        return ContradictionKind.CONTEXTUAL_DIFFERENCE
    if left.fact_value == right.fact_value:
        return ContradictionKind.NONE
    if not overlaps(left, right):
        return ContradictionKind.REVISION
    return ContradictionKind.CONTRADICTION


def temporally_eligible(meta: TruthMetadata, *, valid_at: datetime | None, knowledge_at: datetime | None,
                        current: bool, superseded_by_other: bool = False) -> bool:
    if knowledge_at is not None and meta.recorded_at is not None and meta.recorded_at > knowledge_at:
        return False
    if valid_at is not None:
        if meta.valid_from is not None and valid_at < meta.valid_from: return False
        if meta.valid_until is not None and valid_at >= meta.valid_until: return False
    if meta.state is TruthState.INVALIDATED: return False
    if current and (meta.state is TruthState.SUPERSEDED or superseded_by_other): return False
    return True
