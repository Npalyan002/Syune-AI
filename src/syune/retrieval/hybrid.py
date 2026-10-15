"""Provider-neutral hybrid retrieval contracts and production adapters."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from math import sqrt
import re
from typing import Mapping, Protocol
import json

from syune.memory.model import NodeId

_TOKEN = re.compile(r"\w+", re.UNICODE)
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "did", "do", "does",
    "for", "from", "give", "has", "have", "how", "in", "into", "is", "it", "name",
    "of", "on", "the", "to", "upon", "was", "were", "what", "when", "where", "which",
    "who", "why", "with", "together", "record", "records", "retrieve", "return", "says", "serves",
})
_CANONICAL = {
    "automobile": "vehicle", "car": "vehicle",
    "biggest": "large", "largest": "large",
    # Fixed relation equivalence classes. These express equivalence, not general
    # relatedness: ownership deliberately remains distinct from management.
    "owned": "owner", "owns": "owner", "proprietor": "owner",
    "chief": "manage", "coordinate": "manage", "coordinator": "manage",
    "lead": "manage", "manage": "manage", "manager": "manage",
    "oversee": "manage", "responsible": "manage", "supervise": "manage",
    "supervisor": "manage",
    "bas": "location", "base": "location", "headquarter": "location",
    "located": "location", "location": "location", "place": "location",
    "situat": "location",
    "provid": "supplier", "provide": "supplier", "provider": "supplier", "supplier": "supplier",
    "supply": "supplier", "vendor": "supplier",
    "compos": "material", "compose": "material", "composition": "material",
    "consist": "material", "made": "material", "material": "material",
    "condition": "status", "phase": "status", "state": "status", "status": "status",
    "moon": "moon", "moons": "moon", "satellite": "moon", "satellites": "moon",
    "propulsion": "engine",
}


def tokens(text: str) -> tuple[str, ...]:
    return tuple(match.group().casefold() for match in _TOKEN.finditer(text))


def _stem(token: str) -> str:
    if len(token) > 5 and token.endswith("ing"): token = token[:-3]
    elif len(token) > 4 and token.endswith("ies"): token = token[:-3] + "y"
    elif len(token) > 4 and token.endswith("ied"): token = token[:-3] + "y"
    elif len(token) > 4 and token.endswith("ed"): token = token[:-2]
    elif len(token) > 5 and token.endswith(("ches", "shes", "sses", "xes", "zes")): token = token[:-2]
    elif len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is", "as")): token = token[:-1]
    return token


def terms(text: str) -> tuple[str, ...]:
    """Deterministic non-learned content terms used by lexical retrieval."""
    normalized = []
    for token in tokens(text):
        if token in _STOPWORDS: continue
        token = _CANONICAL.get(token, token)
        token = _CANONICAL.get(_stem(token), _stem(token))
        normalized.append(token)
    return tuple(normalized)


def entity_terms(text: str) -> tuple[str, ...]:
    """Return normalized terms from explicit capitalized entity mentions."""
    mentions = " ".join(re.findall(r"\b[A-Z][\w-]*\b", text))
    return tuple(dict.fromkeys(terms(mentions)))


class RetrieverKind(str, Enum):
    EXACT = "exact"
    ENTITY = "entity"
    LEXICAL = "lexical"
    SEMANTIC = "semantic"
    ASSOCIATIVE = "associative"
    TEMPORAL = "temporal"


class QueryIntent(str, Enum):
    EXACT = "EXACT"
    TEMPORAL = "TEMPORAL"
    CONCEPTUAL = "CONCEPTUAL"
    ASSOCIATIVE = "ASSOCIATIVE"
    MIXED = "MIXED"


class BackendHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class EmbeddingIdentity:
    provider: str
    model: str
    version: str
    dimensions: int
    configuration: str = "default"

    @property
    def space_id(self) -> str:
        raw = json.dumps((self.provider, self.model, self.version, self.dimensions, self.configuration), separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class RetrieverCandidate:
    memory_id: NodeId
    retriever: RetrieverKind
    raw_score: float
    normalized_score: float
    match_reason: str
    rank: int


@dataclass(frozen=True, slots=True)
class QueryAnalysis:
    intent: QueryIntent
    tokens: tuple[str, ...]
    routes: tuple[RetrieverKind, ...]
    fallback: tuple[RetrieverKind, ...]


@dataclass(frozen=True, slots=True)
class VectorIndexStats:
    backend: str
    indexed_vectors: int | None
    dimensions: int
    bytes_used: int | None = None
    persistent: bool = False
    ann: bool = False


class EmbeddingUnavailable(RuntimeError): pass
class VectorIndexUnavailable(RuntimeError): pass
class EmbeddingSpaceMismatch(ValueError): pass


class Retriever(Protocol):
    kind: RetrieverKind
    def retrieve(self, query: str, limit: int) -> tuple[RetrieverCandidate, ...]: ...


class EmbeddingProvider(Protocol):
    identity: EmbeddingIdentity
    version: str
    dimensions: int
    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...


class VectorIndex(Protocol):
    version: str
    embedding_space_id: str | None
    def configure(self, identity: EmbeddingIdentity) -> None: ...
    def upsert(self, memory_id: NodeId, vector: tuple[float, ...], metadata: Mapping[str, str] | None = None) -> None: ...
    def upsert_many(self, items: tuple[tuple[NodeId, tuple[float, ...], Mapping[str, str]], ...]) -> None: ...
    def remove(self, memory_id: NodeId) -> None: ...
    def search(self, vector: tuple[float, ...], limit: int, metadata_filter: Mapping[str, str] | None = None) -> tuple[tuple[NodeId, float], ...]: ...
    def stats(self) -> VectorIndexStats: ...
    def health(self) -> BackendHealth: ...


class DeterministicEmbeddingProvider:
    """Test/development provider. It is never real-semantic evidence."""
    version = "deterministic-token-v1"
    dimensions = 64
    identity = EmbeddingIdentity("syune", "deterministic-token", version, dimensions, "synonyms-v1")
    _synonyms = {"chief": "owner", "lead": "owner", "responsible": "owner",
                 "automobile": "car", "vehicle": "car", "historic": "historical",
                 "weekly": "week", "pattern": "status"}

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for token in tokens(text):
                canonical = self._synonyms.get(token, token)
                slot = sum((index + 1) * ord(char) for index, char in enumerate(canonical)) % self.dimensions
                vector[slot] += 1.0
            norm = sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append(tuple(value / norm for value in vector))
        return tuple(vectors)


class LocalVectorIndex:
    """Deterministic linear development backend; never scale/ANN evidence."""
    version = "local-vector-v2"
    def __init__(self):
        self._vectors: dict[NodeId, tuple[float, ...]] = {}; self._metadata: dict[NodeId, dict[str, str]] = {}
        self.embedding_space_id: str | None = None; self.dimensions = 0
    def configure(self, identity: EmbeddingIdentity) -> None:
        if self.embedding_space_id not in (None, identity.space_id):
            raise EmbeddingSpaceMismatch("embedding space mismatch; rebuild required")
        self.embedding_space_id, self.dimensions = identity.space_id, identity.dimensions
    def _validate(self, vector):
        if self.dimensions and len(vector) != self.dimensions: raise EmbeddingSpaceMismatch("vector dimension mismatch")
        if not self.dimensions: self.dimensions = len(vector)
    def upsert(self, memory_id, vector, metadata=None):
        self._validate(vector); self._vectors[memory_id] = vector; self._metadata[memory_id] = dict(metadata or {})
    def upsert_many(self, items):
        for memory_id, vector, metadata in items: self.upsert(memory_id, vector, metadata)
    def remove(self, memory_id): self._vectors.pop(memory_id, None); self._metadata.pop(memory_id, None)
    def search(self, vector, limit, metadata_filter=None):
        self._validate(vector)
        scored = ((mid, sum(a*b for a,b in zip(vector, stored))) for mid,stored in self._vectors.items()
                  if not metadata_filter or all(self._metadata.get(mid, {}).get(k) == v for k,v in metadata_filter.items()))
        return tuple(sorted(scored, key=lambda x: (-x[1], type(x[0]).__name__, str(x[0])))[:limit])
    def stats(self): return VectorIndexStats("local-linear", len(self._vectors), self.dimensions, sum(len(v)*8 for v in self._vectors.values()), False, False)
    def health(self): return BackendHealth.HEALTHY


def analyze_query(text: str | None, has_exact_ids: bool = False) -> QueryAnalysis:
    raw_tokens = tokens(text or "")
    query_tokens = terms(text or "")
    if has_exact_ids: return QueryAnalysis(QueryIntent.EXACT, query_tokens, (RetrieverKind.EXACT, RetrieverKind.ENTITY), (RetrieverKind.LEXICAL,))
    if set(raw_tokens) & {"current","previous","historical","history","before","after","when"}:
        return QueryAnalysis(QueryIntent.TEMPORAL, query_tokens, (RetrieverKind.TEMPORAL,RetrieverKind.LEXICAL,RetrieverKind.ENTITY), (RetrieverKind.ASSOCIATIVE,RetrieverKind.SEMANTIC))
    if set(raw_tokens) & {"similar","concept","idea","meaning","related","analogy"}:
        return QueryAnalysis(QueryIntent.CONCEPTUAL, query_tokens, (RetrieverKind.SEMANTIC,RetrieverKind.ASSOCIATIVE), (RetrieverKind.LEXICAL,))
    if set(raw_tokens) & {"linked","connection","associated","route","relationship"}:
        return QueryAnalysis(QueryIntent.ASSOCIATIVE, query_tokens, (RetrieverKind.LEXICAL,RetrieverKind.ASSOCIATIVE), (RetrieverKind.SEMANTIC,))
    return QueryAnalysis(QueryIntent.MIXED, query_tokens, (RetrieverKind.LEXICAL,RetrieverKind.ENTITY,RetrieverKind.ASSOCIATIVE), (RetrieverKind.SEMANTIC,))


def reciprocal_rank_fusion(ranks: tuple[int, ...], constant: int = 60) -> float:
    return sum(1.0 / (constant + rank) for rank in ranks)
