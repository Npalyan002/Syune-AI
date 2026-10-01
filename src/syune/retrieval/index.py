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
from typing import Protocol

from syune.core import SourceId
from syune.memory import Claim, Concept, Episode, Observation, Procedure
from syune.memory import LifecycleState
from syune.memory.model import NodeId
from syune.memory.repository import MemoryRepository
from .model import RetrievalError, RetrievalErrorCode
from .hybrid import (
    BackendHealth, DeterministicEmbeddingProvider, EmbeddingProvider, EmbeddingSpaceMismatch,
    EmbeddingUnavailable, LocalVectorIndex, VectorIndex, VectorIndexUnavailable,
)

INDEX_VERSION = "1"
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


class SeedIndex(Protocol):
    version: str
    def rebuild(self) -> None: ...
    def sync(self) -> None: ...
    def clear(self) -> None: ...
    def lexical(self, text: str, limit: int) -> tuple[LexicalHit, ...]: ...
    def source_ids(self, source_id: SourceId, limit: int) -> tuple[NodeId, ...]: ...


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
                for token in set(tokens(prior.text)):
                    posting = self.postings.get(token)
                    if posting: posting.pop(entity.id, None)
                self._total_document_tokens -= len(tokens(prior.text))
                self.vector_index.remove(entity.id)
            provenance = getattr(entity, "provenance", None)
            entry = IndexEntry(entity.id, type(entity).__name__, field, text,
                               provenance.source_id if provenance else None)
            pending.append((entry, text))
        # Lexical indexing remains operational if semantic infrastructure fails.
        for entry, text in pending:
            self.entries[entry.entity_id] = entry
            self._total_document_tokens += len(tokens(text))
            for token in set(tokens(text)):
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

    def _remove(self,entity_id):
        prior=self.entries.pop(entity_id,None)
        if prior is None:return
        for token in set(tokens(prior.text)):
            posting=self.postings.get(token)
            if posting: posting.pop(entity_id,None)
        self._total_document_tokens-=len(tokens(prior.text)); self.vector_index.remove(entity_id)
        for group in self._truth_groups.values(): group.discard(entity_id)

    @_locked
    def lexical(self, text: str, limit: int) -> tuple[LexicalHit, ...]:
        self._check()
        query = tuple(dict.fromkeys(tokens(text)))
        if not query:
            return ()
        planned = sorted(query, key=lambda token: (len(self.postings.get(token, ())), token))
        ids: set[NodeId] = set()
        for token in planned:
            remaining = self.max_lexical_candidates - len(ids)
            if remaining <= 0: break
            posting = self.postings.get(token, {})
            ids.update(islice(posting, remaining))
        self.generated_candidates = len(ids)
        hits = []
        document_count = max(1, len(self.entries))
        average_length = self._total_document_tokens / document_count
        for entity_id in ids:
            entry = self.entries[entity_id]
            matched = tuple(token for token in query if token in tokens(entry.text))
            document_tokens = tokens(entry.text)
            bm25 = 0.0
            for token in matched:
                frequency = document_tokens.count(token)
                document_frequency = len(self.postings.get(token, ()))
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
    def exact(self, text: str, limit: int) -> tuple[LexicalHit, ...]:
        self._check(); needle = text.strip().casefold()
        hits = [LexicalHit(entry.entity_id, 1.0, entry.field, tokens(text))
                for entry in self.entries.values() if entry.text.strip().casefold() == needle]
        return tuple(sorted(hits, key=lambda hit: (type(hit.entity_id).__name__, str(hit.entity_id)))[:limit])

    @_locked
    def entity(self, text: str, limit: int) -> tuple[LexicalHit, ...]:
        self._check()
        names = tuple(token.casefold() for token in re.findall(r"\b[A-Z][\w-]*\b", text))
        if not names: return ()
        ids = set().union(*(self.postings.get(name, set()) for name in names))
        return tuple(LexicalHit(entity_id, 1.0, "entity", names) for entity_id in
                     sorted(ids, key=lambda item: (type(item).__name__, str(item)))[:limit])

    @_locked
    def semantic(self, text: str, limit: int) -> tuple[LexicalHit, ...]:
        self._check()
        try:
            vector = self.embedding_provider.embed((text,))[0]
            return tuple(LexicalHit(entity_id, max(0.0, min(1.0, score)), "semantic", ())
                         for entity_id, score in self.vector_index.search(vector, limit) if score > 0)
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

    def truth_peers(self, fact_key: str, context_key: str | None) -> tuple[NodeId, ...]:
        return tuple(self._truth_groups.get((fact_key, context_key), ()))

    def source_ids(self, source_id: SourceId, limit: int) -> tuple[NodeId, ...]:
        self._check()
        ids = (entry.entity_id for entry in self.entries.values() if entry.source_id == source_id)
        return tuple(sorted(ids, key=lambda entity_id: (type(entity_id).__name__, str(entity_id)))[:limit])
