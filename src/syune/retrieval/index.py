"""Rebuildable, local lexical seed index. MemoryRepository is authoritative."""
from __future__ import annotations

import re
from math import log
import heapq
from itertools import islice
from functools import wraps
from threading import RLock
from dataclasses import dataclass
from enum import Enum
from time import perf_counter
from typing import Callable, Protocol

from syune.core import SourceId
from syune.memory import (
    AccessContext, Claim, Concept, Episode, LifecycleState, Observation, Procedure,
    SecurityEnvelope, TruthMetadata, authorize, temporally_eligible,
)
from syune.memory.model import NodeId
from syune.memory.repository import MemoryRepository
from .model import RetrievalError, RetrievalErrorCode
from .hybrid import (
    BackendHealth, DeterministicEmbeddingProvider, EmbeddingProvider, EmbeddingSpaceMismatch,
    EmbeddingUnavailable, LocalVectorIndex, VectorIndex, VectorIndexUnavailable,
    entity_terms, terms,
)

INDEX_VERSION = "2"
_TOKEN = re.compile(r"\w+", re.UNICODE)

def _locked(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock: return method(self, *args, **kwargs)
    return wrapper


def tokens(text: str) -> tuple[str, ...]:
    return tuple(match.group().casefold() for match in _TOKEN.finditer(text))


@dataclass(frozen=True, slots=True)
class IndexEntry:
    entity_id: NodeId
    entity_type: str
    field: str
    text: str
    source_id: SourceId | None
    lexical_terms: tuple[str, ...]
    security: SecurityEnvelope | None
    truth: TruthMetadata | None
    provenance_valid: bool
    version: str = INDEX_VERSION


@dataclass(frozen=True, slots=True)
class LexicalHit:
    entity_id: NodeId
    score: float
    field: str
    matched_tokens: tuple[str, ...]


class IndexConsistency(str, Enum):
    SYNCED = "SYNCED"
    LAGGING = "LAGGING"
    DEGRADED = "DEGRADED"
    REBUILD_REQUIRED = "REBUILD_REQUIRED"


@dataclass(frozen=True, slots=True)
class RetrievalIndexMetrics:
    backend: str
    consistency: IndexConsistency
    canonical_memories: int
    lexical_memories: int
    indexed_vectors: int | None
    index_lag: int
    embedding_failures: int
    ann_failures: int
    fallback_count: int
    sync_latency_ms: float


@dataclass(frozen=True, slots=True)
class PolicyPartition:
    generation: int
    entity_ids: frozenset[NodeId]
    document_tokens: int
    document_frequency: dict[str, int]


class SeedIndex(Protocol):
    version: str
    def rebuild(self) -> None: ...
    def sync(self) -> None: ...
    def clear(self) -> None: ...
    def lexical(self, text: str, limit: int, *, eligible: Callable[[NodeId], bool] | None = None) -> tuple[LexicalHit, ...]: ...
    def source_ids(self, source_id: SourceId, limit: int, *, eligible: Callable[[NodeId], bool] | None = None) -> tuple[NodeId, ...]: ...


class InvertedSeedIndex:
    """Explicit in-memory derivative index; no durable mutation or external search."""

    def __init__(self, memory: MemoryRepository, version: str = INDEX_VERSION,
                 embedding_provider: EmbeddingProvider | None = None,
                 vector_index: VectorIndex | None = None):
        self.memory = memory
        self.version = version
        self.entries: dict[NodeId, IndexEntry] = {}
        self.postings: dict[str, dict[NodeId, None]] = {}
        self.ready = False
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.vector_index = vector_index or LocalVectorIndex()
        self.consistency = IndexConsistency.LAGGING
        self.embedding_failures = self.ann_failures = self.fallback_count = 0
        self.sync_latency_ms = 0.0
        self.cursor = 0
        self.lifecycle_cursor = 0
        self.max_lexical_candidates = 2048
        self.generated_candidates = self.ranked_candidates = 0
        self.generation = 0
        self.partition_cache_hits = self.partition_cache_misses = 0
        self.partition_cache_invalidations = 0
        self._policy_partitions: dict[AccessContext | None, PolicyPartition] = {}
        self._total_document_tokens = 0
        self._truth_groups: dict[tuple[str, str | None], set[NodeId]] = {}
        self._superseded: set[NodeId] = set()
        self._lock = RLock()
        try:
            self.vector_index.configure(self.embedding_provider.identity)
        except EmbeddingSpaceMismatch:
            self.consistency = IndexConsistency.REBUILD_REQUIRED
            raise

    def _check(self) -> None:
        if self.version != INDEX_VERSION:
            raise RetrievalError(RetrievalErrorCode.INCOMPATIBLE_INDEX, "index version mismatch")
        if not self.ready:
            raise RetrievalError(RetrievalErrorCode.INDEX_UNAVAILABLE, "index must be rebuilt")

    @_locked
    def clear(self) -> None:
        for entity_id in tuple(self.entries):
            self.vector_index.remove(entity_id)
        self.entries.clear()
        self.postings.clear()
        self.ready = False
        self.consistency = IndexConsistency.LAGGING
        self.cursor = 0; self.lifecycle_cursor = 0; self._total_document_tokens = 0
        self._truth_groups.clear(); self._superseded.clear()
        self._publish_generation()

    def _publish_generation(self) -> None:
        self.generation += 1
        if self._policy_partitions:
            self.partition_cache_invalidations += len(self._policy_partitions)
            self._policy_partitions.clear()

    @_locked
    def rebuild(self) -> None:
        if self.version != INDEX_VERSION:
            raise RetrievalError(RetrievalErrorCode.INCOMPATIBLE_INDEX, "index version mismatch")
        self.clear()
        self.ready = True
        self.sync()

    @_locked
    def sync(self) -> None:
        self._check()
        started = perf_counter()
        pending: list[tuple[IndexEntry, str]] = []
        if hasattr(self.memory,"lifecycle_changes_since"):
            while True:
                next_cursor,transitions=self.memory.lifecycle_changes_since(self.lifecycle_cursor,1024)
                self.lifecycle_cursor=next_cursor
                for entity_id,state in transitions:
                    if state is not LifecycleState.ACTIVE: self._remove(entity_id)
                if len(transitions)<1024: break
        if hasattr(self.memory, "changes_since"):
            changed = []
            while True:
                next_cursor, batch = self.memory.changes_since(self.cursor, 1024)
                changed.extend(batch); self.cursor = next_cursor
                if len(batch) < 1024: break
        else:
            changed = self.memory.iter_entities()
        for entity in changed:
            if hasattr(self.memory,"lifecycle") and self.memory.lifecycle(entity.id).state is not LifecycleState.ACTIVE:
                self._remove(entity.id); continue
            field, text = None, None
            if isinstance(entity, Observation): field, text = "content", entity.content
            elif isinstance(entity, Concept): field, text = "label", entity.label
            elif isinstance(entity, Claim): field, text = "statement", entity.statement
            elif isinstance(entity, Episode): field, text = "description", entity.description
            elif isinstance(entity, Procedure): field, text = "steps", " ".join(entity.steps)
            if text is None:
                continue
            prior = self.entries.get(entity.id)
            if prior is not None:
                for token in set(prior.lexical_terms):
                    posting = self.postings.get(token)
                    if posting: posting.pop(entity.id, None)
                self._total_document_tokens -= len(prior.lexical_terms)
                self.vector_index.remove(entity.id)
            provenance = getattr(entity, "provenance", None)
            truth = getattr(entity, "truth", None)
            provenance_valid = (provenance is None or self.memory.exists(provenance.source_id)
                                or truth is None or truth.recorded_at is None)
            entry = IndexEntry(
                entity.id, type(entity).__name__, field, text,
                provenance.source_id if provenance else None, terms(text),
                getattr(entity, "security", None), truth, provenance_valid,
            )
            pending.append((entry, text))
        # Lexical indexing remains operational if semantic infrastructure fails.
        for entry, text in pending:
            self.entries[entry.entity_id] = entry
            self._total_document_tokens += len(entry.lexical_terms)
            for token in set(entry.lexical_terms):
                self.postings.setdefault(token, {})[entry.entity_id] = None
            entity = self.memory.get(entry.entity_id)
            truth = getattr(entity, "truth", None)
            if truth is not None:
                for group in self._truth_groups.values(): group.discard(entry.entity_id)
                if truth.fact_key: self._truth_groups.setdefault((truth.fact_key, truth.context_key), set()).add(entry.entity_id)
                self._superseded.discard(entry.entity_id)
                self._superseded.update(truth.supersedes)
        if pending:
            try:
                vectors = self.embedding_provider.embed(tuple(text for _, text in pending))
                if len(vectors) != len(pending): raise EmbeddingSpaceMismatch("embedding batch count mismatch")
                self.vector_index.upsert_many(tuple(
                    (entry.entity_id, vector, {"entity_type": entry.entity_type})
                    for (entry, _), vector in zip(pending, vectors)))
            except (EmbeddingUnavailable, EmbeddingSpaceMismatch):
                self.embedding_failures += 1; self.consistency = IndexConsistency.DEGRADED
            except VectorIndexUnavailable:
                self.ann_failures += 1; self.consistency = IndexConsistency.DEGRADED
        if self.consistency is not IndexConsistency.DEGRADED:
            self.consistency = IndexConsistency.SYNCED
        self.sync_latency_ms = (perf_counter() - started) * 1000
        # Writers call sync before releasing the runtime write lock. Publishing a
        # generation here atomically invalidates policy, ownership, Add, lifecycle,
        # temporal-metadata, association, and rebuild-derived partitions. Even a
        # metadata-only/association write therefore cannot retain a stale view.
        self._publish_generation()

    def _remove(self,entity_id):
        prior=self.entries.pop(entity_id,None)
        if prior is None:return
        for token in set(prior.lexical_terms):
            posting=self.postings.get(token)
            if posting: posting.pop(entity_id,None)
        self._total_document_tokens-=len(prior.lexical_terms); self.vector_index.remove(entity_id)
        for group in self._truth_groups.values(): group.discard(entity_id)

    @_locked
    def lexical(self, text: str, limit: int, *, eligible: Callable[[NodeId], bool] | None = None,
                partition: PolicyPartition | None = None) -> tuple[LexicalHit, ...]:
        self._check()
        query = tuple(dict.fromkeys(terms(text)))
        if not query:
            return ()
        allowed_ids = {entity_id for entity_id in self.entries if eligible is None or eligible(entity_id)}
        cached_stats = (partition is not None and partition.generation == self.generation
                        and allowed_ids == partition.entity_ids)
        allowed_frequency = ({token: partition.document_frequency.get(token, 0) for token in query}
                             if cached_stats else {
                                 token: sum(entity_id in allowed_ids for entity_id in self.postings.get(token, ()))
                                 for token in query
                             })
        planned = sorted(query, key=lambda token: (
            allowed_frequency[token], token))
        ids: set[NodeId] = set()
        for token in planned:
            remaining = self.max_lexical_candidates - len(ids)
            if remaining <= 0: break
            posting = (entity_id for entity_id in self.postings.get(token, {}) if entity_id in allowed_ids)
            ids.update(islice(posting, remaining))
        self.generated_candidates = len(ids)
        hits = []
        document_count = max(1, len(allowed_ids))
        allowed_document_tokens = (partition.document_tokens if cached_stats else
                                   sum(len(self.entries[entity_id].lexical_terms) for entity_id in allowed_ids))
        average_length = allowed_document_tokens / document_count
        for entity_id in ids:
            entry = self.entries[entity_id]
            matched = tuple(token for token in query if token in entry.lexical_terms)
            document_tokens = entry.lexical_terms
            bm25 = 0.0
            for token in matched:
                frequency = document_tokens.count(token)
                document_frequency = allowed_frequency[token]
                inverse = log(1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5))
                denominator = frequency + 1.2 * (1 - 0.75 + 0.75 * len(document_tokens) / max(1, average_length))
                bm25 += inverse * frequency * 2.2 / denominator
            score = min(1.0, (len(matched) / len(query)) * 0.7 + (bm25 / (bm25 + 1)) * 0.3)
            if text.casefold() in entry.text.casefold():
                score = min(1.0, score + 0.1)
            hits.append(LexicalHit(entity_id, score, entry.field, matched))
        self.ranked_candidates = min(limit, len(hits))
        return tuple(heapq.nsmallest(limit, hits, key=lambda hit: (-hit.score, type(hit.entity_id).__name__, str(hit.entity_id))))

    @_locked
    def exact(self, text: str, limit: int, *, eligible: Callable[[NodeId], bool] | None = None) -> tuple[LexicalHit, ...]:
        self._check(); needle = text.strip().casefold()
        hits = [LexicalHit(entry.entity_id, 1.0, entry.field, tokens(text))
                for entry in self.entries.values()
                if entry.text.strip().casefold() == needle and (eligible is None or eligible(entry.entity_id))]
        return tuple(sorted(hits, key=lambda hit: (type(hit.entity_id).__name__, str(hit.entity_id)))[:limit])

    @_locked
    def entity(self, text: str, limit: int, *, eligible: Callable[[NodeId], bool] | None = None) -> tuple[LexicalHit, ...]:
        self._check()
        names = entity_terms(text)
        if not names: return ()
        ids = {entity_id for name in names for entity_id in self.postings.get(name, set())
               if eligible is None or eligible(entity_id)}
        hits = []
        for entity_id in sorted(ids, key=lambda item: (type(item).__name__, str(item))):
            matched = tuple(name for name in names if name in self.entries[entity_id].lexical_terms)
            hits.append(LexicalHit(entity_id, len(matched) / len(names), "entity", matched))
        return tuple(sorted(hits, key=lambda hit: (-hit.score, type(hit.entity_id).__name__,
                                                   str(hit.entity_id)))[:limit])

    @_locked
    def semantic(self, text: str, limit: int, *, eligible: Callable[[NodeId], bool] | None = None) -> tuple[LexicalHit, ...]:
        self._check()
        try:
            vector = self.embedding_provider.embed((text,))[0]
            # Search the complete derivative index before applying the request policy.
            # Filtering a limited ANN page afterwards lets hidden vectors crowd visible
            # results out and makes their presence observable through fallback behavior.
            searched = self.vector_index.search(vector, len(self.entries) if eligible is not None else limit)
            return tuple(LexicalHit(entity_id, max(0.0, min(1.0, score)), "semantic", ())
                         for entity_id, score in searched
                         if score > 0 and (eligible is None or eligible(entity_id)))[:limit]
        except (EmbeddingUnavailable, VectorIndexUnavailable):
            self.fallback_count += 1; self.consistency = IndexConsistency.DEGRADED
            return ()

    @_locked
    def health(self) -> RetrievalIndexMetrics:
        canonical = self.memory.entity_count() if hasattr(self.memory, "entity_count") else len(self.entries)
        try: stats = self.vector_index.stats()
        except VectorIndexUnavailable:
            stats = None; self.ann_failures += 1; self.consistency = IndexConsistency.DEGRADED
        indexed = stats.indexed_vectors if stats else None
        lag = max(0, canonical - (indexed if indexed is not None else len(self.entries)))
        state = (self.consistency if self.consistency in {IndexConsistency.DEGRADED, IndexConsistency.REBUILD_REQUIRED}
                 else IndexConsistency.LAGGING if lag else self.consistency)
        return RetrievalIndexMetrics(stats.backend if stats else type(self.vector_index).__name__, state,
            canonical, len(self.entries), indexed, lag, self.embedding_failures, self.ann_failures,
            self.fallback_count, self.sync_latency_ms)

    def is_superseded(self, entity_id: NodeId) -> bool:
        return entity_id in self._superseded

    def request_eligible(self, entity_id: NodeId, access_context: AccessContext | None, *,
                         valid_at, knowledge_at, current: bool,
                         partition: PolicyPartition | None = None) -> bool:
        """Evaluate discovery eligibility from the synchronized immutable snapshot.

        This is only the pre-limit candidate filter. RetrievalService rechecks the
        authoritative repository before traversal and return.
        """
        entry = self.entries.get(entity_id)
        if entry is None or not entry.provenance_valid:
            return False
        if partition is not None:
            if partition.generation != self.generation or entity_id not in partition.entity_ids:
                return False
        elif not authorize(entry.security, access_context).allowed:
            return False
        return entry.truth is None or temporally_eligible(
            entry.truth, valid_at=valid_at, knowledge_at=knowledge_at, current=current,
            superseded_by_other=entity_id in self._superseded,
        )

    @_locked
    def policy_partition(self, access_context: AccessContext | None) -> PolicyPartition:
        cached = self._policy_partitions.get(access_context)
        if cached is not None and cached.generation == self.generation:
            self.partition_cache_hits += 1
            return cached
        self.partition_cache_misses += 1
        allowed = frozenset(
            entity_id for entity_id, entry in self.entries.items()
            if entry.provenance_valid and authorize(entry.security, access_context).allowed
        )
        frequency: dict[str, int] = {}
        total = 0
        for entity_id in allowed:
            entry = self.entries[entity_id]
            total += len(entry.lexical_terms)
            for token in set(entry.lexical_terms):
                frequency[token] = frequency.get(token, 0) + 1
        candidate = PolicyPartition(self.generation, allowed, total, frequency)
        # The index lock makes validation plus publication atomic. If generation ever
        # differs, fail closed by returning an unpublished empty partition.
        if candidate.generation != self.generation:
            return PolicyPartition(self.generation, frozenset(), 0, {})
        self._policy_partitions[access_context] = candidate
        return candidate

    def partition_metrics(self) -> dict[str, int]:
        return {"generation": self.generation, "entries": len(self._policy_partitions),
                "hits": self.partition_cache_hits, "misses": self.partition_cache_misses,
                "invalidations": self.partition_cache_invalidations}

    @_locked
    def denied_lexical_ids(self, text: str, access_context: AccessContext | None,
                           limit: int) -> tuple[NodeId, ...]:
        """Bounded audit-only matches; never used for admission, scoring, or routing."""
        self._check()
        query = tuple(dict.fromkeys(terms(text)))
        ids = {entity_id for token in query for entity_id in self.postings.get(token, ())}
        denied = (entity_id for entity_id in sorted(ids, key=lambda item: (type(item).__name__, str(item)))
                  if not authorize(self.entries[entity_id].security, access_context).allowed)
        return tuple(islice(denied, limit))

    def truth_peers(self, fact_key: str, context_key: str | None) -> tuple[NodeId, ...]:
        return tuple(self._truth_groups.get((fact_key, context_key), ()))

    def source_ids(self, source_id: SourceId, limit: int, *, eligible: Callable[[NodeId], bool] | None = None) -> tuple[NodeId, ...]:
        self._check()
        ids = (entry.entity_id for entry in self.entries.values()
               if entry.source_id == source_id and (eligible is None or eligible(entry.entity_id)))
        return tuple(sorted(ids, key=lambda entity_id: (type(entity_id).__name__, str(entity_id)))[:limit])
