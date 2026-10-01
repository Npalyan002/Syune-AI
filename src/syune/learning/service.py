"""Explicit record, consolidation, retrieval view, and administrative rollback."""
from __future__ import annotations

from hashlib import sha256
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

from syune.core import ConsolidationBatchId, SourceId, utc_now
from syune.memory import AccessContext, MemoryRepository, TruthState, authorize
from syune.memory.model import NodeId
from .errors import LearningError, LearningErrorCode
from .model import ConsolidationBatch, ConsolidationResult, LearningSignal, LearningSignalKind, LearningStatus, PlasticityState
from .policy import PlasticityPolicy
from .store import SQLiteLearningStore


def _key(entity_id) -> str: return f"{type(entity_id).__name__}:{entity_id}"


class StorePlasticityView:
    """Read-only adapter consumed by RetrievalService."""
    def __init__(self, store: SQLiteLearningStore): self.store = store
    def utility_adjustment(self, entity_id: NodeId) -> float: return self.store.state(_key(entity_id)).utility_delta
    def salience_adjustment(self, entity_id: NodeId) -> float: return self.store.state(_key(entity_id)).salience_delta
    def association_adjustment(self, source_id: NodeId, target_id: NodeId) -> float:
        key = "coactivation:" + "|".join(sorted((_key(source_id), _key(target_id))))
        return self.store.state(key).association_delta


class LearningService:
    def __init__(self, memory: MemoryRepository, store: SQLiteLearningStore, policy: PlasticityPolicy | None = None):
        self.memory, self.store, self.policy = memory, store, policy or PlasticityPolicy()
        self.append_latencies_ms: list[float] = []

    def record(self, signal: LearningSignal, access_context: AccessContext | None = None) -> bool:
        started = perf_counter()
        try:
            for target in signal.targets:
                association = self.memory.get_association(target.id) if type(target.id).__name__ == "AssociationId" else None
                if not self.memory.exists(target.id) and association is None:
                    raise LearningError(LearningErrorCode.UNKNOWN_TARGET, f"unknown target {target.key}")
                entity = self.memory.get(target.id) if association is None else None
                truth = getattr(entity, "truth", None)
                if truth is not None and truth.state in {TruthState.INVALIDATED, TruthState.SUPERSEDED}:
                    raise LearningError(LearningErrorCode.INVALID_SIGNAL,
                                        "learning cannot promote invalidated or superseded memory")
                if entity is not None and not authorize(getattr(entity, "security", None), access_context).allowed:
                    raise LearningError(LearningErrorCode.INVALID_SIGNAL,
                                        "learning cannot consume unauthorized memory")
            if signal.kind is LearningSignalKind.CO_ACTIVATION:
                left, right = (target.id for target in signal.targets)
                if not any({edge.source_id, edge.target_id} == {left, right}
                           for edge in self.memory.associations_for(left)):
                    raise LearningError(LearningErrorCode.UNKNOWN_TARGET,
                                        "co-activation v1 requires an existing canonical association")
            return self.store.append(signal)
        finally:
            self.append_latencies_ms.append((perf_counter() - started) * 1000)

    def _expanded_targets(self, signal: LearningSignal) -> tuple[str, ...]:
        if signal.kind is not LearningSignalKind.SOURCE_RETRACTION_NOTICE:
            return tuple(target.key for target in signal.targets)
        source_id = signal.targets[0].id
        keys = sorted(_key(entity.id) for entity in self.memory.iter_entities()
                      if getattr(entity, "provenance", None) is not None and entity.provenance.source_id == source_id)
        if not keys:
            raise LearningError(LearningErrorCode.UNKNOWN_TARGET, "retracted source has no derived memory")
        return tuple(keys)

    def consolidate_once(self, *, max_signals: int | None = None, correlation_id: str | None = None,
                         entity_ids: tuple[NodeId, ...] = (), source_id: SourceId | None = None) -> ConsolidationResult:
        started = perf_counter()
        limit = min(max_signals or self.policy.config.max_signals_per_batch, self.policy.config.max_signals_per_batch)
        pending = list(self.store.pending(self.policy.config.max_signals_per_batch + 1))
        deferred = max(0, len(pending) - limit)
        pending = pending[:limit]
        if correlation_id is not None: pending = [x for x in pending if x.correlation_id == correlation_id]
        if entity_ids:
            wanted = {_key(x) for x in entity_ids}
            pending = [x for x in pending if wanted & {t.key for t in x.targets}]
        if source_id is not None:
            def belongs(signal):
                for target in signal.targets:
                    if target.id == source_id: return True
                    entity = self.memory.get(target.id)
                    if entity is not None and getattr(entity, "provenance", None) is not None:
                        if entity.provenance.source_id == source_id: return True
                return False
            pending = [x for x in pending if belongs(x)]
        proposal_started = perf_counter()
        current = {state.target_key: state for state in self.store.snapshot()}
        proposals = []
        for signal in pending:
            proposals.extend(self.policy.propose(signal, self._expanded_targets(signal), current))
            if len(proposals) > self.policy.config.max_proposals_per_batch:
                raise LearningError(LearningErrorCode.CONSOLIDATION_FAILED, "proposal limit exceeded")
        bound = self.policy.config.max_total_delta
        if any(abs(value) > bound for item in proposals for value in
               (item.after.utility_delta, item.after.salience_delta, item.after.association_delta)):
            raise LearningError(LearningErrorCode.CONSOLIDATION_FAILED, "proposal outside configured bounds")
        proposal_ms = (perf_counter() - proposal_started) * 1000
        material = "|".join(str(x.id) for x in pending) + ":" + self.policy.config.version
        batch_id = ConsolidationBatchId(uuid5(NAMESPACE_URL, material or "empty-learning-batch"))
        now = utc_now()
        checksum = sha256((material + "|" + "|".join(str(x.id) for x in proposals)).encode()).hexdigest()
        batch = ConsolidationBatch(batch_id, now, now, self.policy.config.version,
            tuple(x.id for x in pending), tuple(x.id for x in proposals), len(proposals), 0,
            checksum, (perf_counter() - started) * 1000, LearningStatus.APPLIED)
        apply_started = perf_counter()
        if pending: self.store.apply_batch(batch, tuple(proposals))
        return ConsolidationResult(batch, tuple(proposals), deferred, proposal_ms,
                                   (perf_counter() - apply_started) * 1000)

    def rollback(self, batch_id: ConsolidationBatchId) -> tuple[PlasticityState, ...]:
        return self.store.rollback(batch_id, utc_now())
