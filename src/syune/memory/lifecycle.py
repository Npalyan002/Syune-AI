"""Policy-driven memory lifecycle, deliberately orthogonal to truth and security."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from syune.core import utc_now
from .model import NodeId, TruthState


class LifecycleState(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    FORGOTTEN = "FORGOTTEN"
    PURGED = "PURGED"


class MemoryClass(str, Enum):
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    ENTITY = "ENTITY"
    TEMPORAL = "TEMPORAL"
    ORGANIZATIONAL = "ORGANIZATIONAL"


@dataclass(frozen=True, slots=True)
class LifecycleRecord:
    entity_id: NodeId
    state: LifecycleState = LifecycleState.ACTIVE
    memory_class: MemoryClass = MemoryClass.SEMANTIC
    created_at: datetime = field(default_factory=utc_now)
    changed_at: datetime = field(default_factory=utc_now)
    last_reinforced_at: datetime | None = None
    reinforcement_count: int = 0
    access_count: int = 0
    protected: bool = False
    historical_importance: float = 0.0
    source_memory_ids: tuple[NodeId, ...] = ()
    content_fingerprint: str | None = None
    reason: str = "ingested"


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    sequence: int
    kind: str
    entity_id: NodeId
    occurred_at: datetime
    from_state: LifecycleState | None
    to_state: LifecycleState
    reason: str


@dataclass(frozen=True, slots=True)
class RetentionRule:
    memory_class: MemoryClass
    archive_after: timedelta | None
    forget_after: timedelta | None
    minimum_importance: float = 0.25


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    rules: tuple[RetentionRule, ...] = (
        RetentionRule(MemoryClass.WORKING, timedelta(days=7), timedelta(days=30)),
        RetentionRule(MemoryClass.EPISODIC, timedelta(days=90), timedelta(days=730)),
        RetentionRule(MemoryClass.SEMANTIC, timedelta(days=365), None),
        RetentionRule(MemoryClass.PROCEDURAL, None, None),
        RetentionRule(MemoryClass.ENTITY, timedelta(days=365), None),
        RetentionRule(MemoryClass.TEMPORAL, timedelta(days=180), None),
        RetentionRule(MemoryClass.ORGANIZATIONAL, None, None),
    )
    decay_half_life_days: float = 180.0
    active_budget: int | None = None

    def rule_for(self, memory_class: MemoryClass) -> RetentionRule:
        return next(rule for rule in self.rules if rule.memory_class is memory_class)


@dataclass(frozen=True, slots=True)
class LifecycleMetrics:
    active: int
    archived: int
    forgotten: int
    purged: int
    consolidated: int
    backlog: int
    maintenance_latency_ms: float


def normalized_fingerprint(entity: object) -> str | None:
    body = next((getattr(entity, name, None) for name in
                 ("content", "statement", "label", "description") if getattr(entity, name, None)), None)
    if body is None and getattr(entity, "steps", None):
        body = "\n".join(entity.steps)
    if not body:
        return None
    normalized = re.sub(r"\s+", " ", body.casefold()).strip()
    truth = getattr(entity, "truth", None)
    fact = getattr(truth, "fact_key", None) or ""
    context = getattr(truth, "context_key", None) or ""
    valid_from = getattr(truth, "valid_from", None)
    valid_until = getattr(truth, "valid_until", None)
    # Scope/purpose and temporal intervals are identity constraints: equal text in
    # incompatible envelopes or different historical periods is not a duplicate.
    security = repr(getattr(entity, "security", None))
    material = f"{type(entity).__name__}|{fact}|{context}|{valid_from}|{valid_until}|{security}|{normalized}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def decay_priority(record: LifecycleRecord, now: datetime, policy: RetentionPolicy) -> float:
    """Interpretable exponential decay; reinforcement changes importance, never truth."""
    anchor = record.last_reinforced_at or record.created_at
    age_days = max(0.0, (now - anchor).total_seconds() / 86400.0)
    decay = 0.5 ** (age_days / policy.decay_half_life_days)
    evidence_boost = min(1.0, record.reinforcement_count * 0.1)
    return min(1.0, max(record.historical_importance, decay + evidence_boost))


class LifecycleService:
    """Bounded coordinator; repositories own durable metadata and event ordering."""
    def __init__(self, repository, policy: RetentionPolicy | None = None):
        self.repository = repository
        self.policy = policy or RetentionPolicy()

    def register(self, entity, memory_class: MemoryClass = MemoryClass.SEMANTIC,
                 *, protected: bool = False, historical_importance: float = 0.0):
        fingerprint = normalized_fingerprint(entity)
        duplicate = self.repository.find_active_fingerprint(fingerprint) if fingerprint else None
        self.repository.put(entity)
        self.repository.set_lifecycle(LifecycleRecord(
            entity.id, LifecycleState.ARCHIVED if duplicate else LifecycleState.ACTIVE,
            memory_class, getattr(entity, "created_at", None) or getattr(entity, "registered_at", utc_now()),
            utc_now(), protected=protected, historical_importance=historical_importance,
            source_memory_ids=(duplicate,) if duplicate else (), content_fingerprint=fingerprint,
            reason="exact_duplicate" if duplicate else "ingested"))
        if duplicate:
            self.repository.reinforce(duplicate, "independent duplicate evidence")
        return duplicate

    def reinforce(self, entity_id: NodeId, reason: str = "evidence-backed reinforcement") -> None:
        self.repository.reinforce(entity_id, reason)

    def access(self, entity_id: NodeId) -> None:
        self.repository.record_access(entity_id)

    def archive(self, entity_id: NodeId, reason: str = "explicit archive") -> None:
        self.repository.transition_lifecycle(entity_id, LifecycleState.ARCHIVED, reason)

    def restore(self, entity_id: NodeId, reason: str = "explicit restore") -> None:
        self.repository.transition_lifecycle(entity_id, LifecycleState.ACTIVE, reason)

    def forget(self, entity_id: NodeId, reason: str = "explicit forget") -> None:
        self.repository.transition_lifecycle(entity_id, LifecycleState.FORGOTTEN, reason)

    def purge(self, entity_id: NodeId, reason: str = "explicit administrative purge") -> None:
        self.repository.purge(entity_id, reason)

    def maintain(self, *, cursor: int = 0, limit: int = 256, now: datetime | None = None):
        now = now or utc_now()
        next_cursor, records = self.repository.lifecycle_scan(cursor, limit)
        for record in records:
            if record.state is not LifecycleState.ACTIVE or record.protected:
                continue
            entity = self.repository.get(record.entity_id)
            truth = getattr(entity, "truth", None)
            if truth is not None and truth.state in {TruthState.INVALIDATED, TruthState.SUPERSEDED}:
                self.archive(record.entity_id, f"truth state {truth.state.value}")
                continue
            rule = self.policy.rule_for(record.memory_class)
            age = now - (record.last_reinforced_at or record.created_at)
            if rule.forget_after is not None and age >= rule.forget_after and decay_priority(record, now, self.policy) < rule.minimum_importance:
                self.forget(record.entity_id, "retention policy expiry")
            elif rule.archive_after is not None and age >= rule.archive_after and decay_priority(record, now, self.policy) < rule.minimum_importance:
                self.archive(record.entity_id, "retention policy decay")
        if self.policy.active_budget is not None:
            pressure=max(0,self.repository.lifecycle_metrics().active-self.policy.active_budget)
            candidates=sorted((record for record in records if record.state is LifecycleState.ACTIVE and not record.protected),
                              key=lambda item:(decay_priority(item,now,self.policy),type(item.entity_id).__name__,str(item.entity_id)))
            for record in candidates[:pressure]:
                if self.repository.lifecycle(record.entity_id).state is LifecycleState.ACTIVE:
                    self.archive(record.entity_id,"active-memory budget pressure")
        return next_cursor, len(records)
