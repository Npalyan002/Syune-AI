from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID

import pytest

from syune.core import (
    AssociationId, ClaimId, ConceptId, Confidence, ObservationId,
    ProcedureId, ProvenanceId, SourceId,
)
from syune.memory import (
    Association, Claim, Concept, InMemoryReferenceRepository,
    Observation, Procedure, Provenance, Source, SourceLocator,
)
from syune.retrieval import (
    InvertedSeedIndex, RecallCue, RecallRequest, RetrievalConfig,
    RetrievalError, RetrievalErrorCode, RetrievalService,
)


def graph():
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    source_id = SourceId(UUID(int=1))
    p = Provenance(ProvenanceId(UUID(int=2)), source_id, at, locator=SourceLocator(block="b1"))
    repo = InMemoryReferenceRepository()
    source = Source(source_id, "file", "synthetic", at)
    a = Observation(ObservationId(UUID(int=10)), "orchard budget", "paragraph", p, at, at)
    b = Concept(ConceptId(UUID(int=11)), "allocation", p, Confidence(0.4), at)
    c = Procedure(ProcedureId(UUID(int=12)), ("review allocations",), p, Confidence(0.5), at)
    distractor = Claim(ClaimId(UUID(int=13)), "orchard budget", p, Confidence(0.95), at)
    for item in (source, a, b, c, distractor): repo.put(item)
    def edge(n, x, y, strength=1.0):
        repo.add_association(Association(AssociationId(UUID(int=n)), x.id, y.id,
                                         "associated_with", p, Confidence(0.8), at, strength))
    edge(30, a, b)
    edge(31, b, c)
    return repo, source, a, b, c, distractor, edge


def service(repo, config=None):
    index = InvertedSeedIndex(repo)
    index.rebuild()
    return RetrievalService(repo, index, config), index


def test_typed_contract_invalid_cue_and_config():
    with pytest.raises(RetrievalError) as error:
        RecallCue()
    assert error.value.code is RetrievalErrorCode.EMPTY_CUE
    with pytest.raises(RetrievalError):
        RecallCue(entity_ids=("bad",))
    with pytest.raises(RetrievalError):
        RetrievalConfig(max_edges=0)


def test_lexical_seed_association_score_and_provenance():
    repo, source, a, b, c, distractor, _ = graph()
    retrieval, index = service(repo)
    result = retrieval.recall(RecallRequest(RecallCue(text="orchard budget")))
    by_id = {item.entity_id: item for item in result.candidates}
    assert a.id in by_id and b.id in by_id and c.id in by_id
    assert "lexical:content" in by_id[a.id].seed_reasons
    assert by_id[a.id].lexical_tokens == ("budget", "orchard")
    assert by_id[b.id].association_paths
    assert by_id[c.id].association_paths
    assert by_id[a.id].entity_type == "Observation"
    assert by_id[distractor.id].entity_type == "Claim"
    assert by_id[a.id].source_id == source.id
    assert by_id[a.id].locator.block == "b1"
    assert dict(by_id[a.id].components)["confidence"] == 0.0
    assert result.working_memory and len(result.working_memory) <= 8
    assert dict(result.timings_ms)["total"] >= 0


def test_context_beats_lexical_distractor():
    repo, _, a, b, _, distractor, _ = graph()
    retrieval, _ = service(repo, RetrievalConfig(weights=(
        ("seed", 1.0), ("activation", 1.0), ("salience", 0.0),
        ("context", 3.0), ("confidence", 0.1), ("recency", 0.0),
        ("provenance", 0.0), ("pattern", 0.0),
    )))
    result = retrieval.recall(RecallRequest(RecallCue(text="orchard budget", context_ids=(b.id,))))
    ranked = {item.entity_id: item.rank for item in result.candidates}
    assert ranked[a.id] < ranked[distractor.id]
    assert dict(next(x for x in result.candidates if x.entity_id == a.id).components)["context"] > 0


def test_convergent_pattern_completion_cycle_and_limits():
    repo, _, a, b, c, _, edge = graph()
    edge(32, a, c)
    edge(33, c, a)
    retrieval, _ = service(repo, RetrievalConfig(max_hops=2, max_edges=20, pattern_min_support=2))
    cue = RecallCue(entity_ids=(a.id, b.id))
    result = retrieval.recall(RecallRequest(cue))
    candidate = next(item for item in result.candidates if item.entity_id == c.id)
    assert candidate.pattern_support >= 2
    assert dict(candidate.components)["pattern"] > 0
    assert len(candidate.association_paths) >= 2
    again = retrieval.recall(RecallRequest(cue))
    assert [x.entity_id for x in result.candidates] == [x.entity_id for x in again.candidates]
    assert dict(result.diagnostics)["edges"] <= 20
    limited, _ = service(repo, RetrievalConfig(max_hops=3, max_edges=1, max_fanout=1, max_candidates=2))
    bounded = limited.recall(RecallRequest(cue))
    assert "edges" in bounded.truncated or "fanout" in bounded.truncated
    assert dict(bounded.diagnostics)["edges"] <= 1


def test_insufficient_pattern_support_and_factor_configuration():
    repo, _, a, b, c, _, _ = graph()
    one_seed, _ = service(repo, RetrievalConfig(max_hops=2))
    result = one_seed.recall(RecallRequest(RecallCue(entity_ids=(b.id,),
                                                  temporal_context=datetime(2026, 1, 2, tzinfo=timezone.utc))))
    target = next(item for item in result.candidates if item.entity_id == c.id)
    components = dict(target.components)
    assert components["pattern"] == 0
    assert components["recency"] > 0
    assert components["confidence"] > 0
    assert target.activation < 1.0
    limited, _ = service(repo, RetrievalConfig(max_candidates=1, max_explicit_seeds=1))
    bounded = limited.recall(RecallRequest(RecallCue(entity_ids=(a.id, b.id))))
    assert "candidates" in bounded.truncated or "explicit_seeds" in bounded.truncated
    assert dict(bounded.diagnostics)["candidates"] <= 1


def test_source_seed_index_rebuild_sync_and_version():
    repo, source, a, b, _, _, _ = graph()
    retrieval, index = service(repo)
    result = retrieval.recall(RecallRequest(RecallCue(source_ids=(source.id,))))
    assert any(item.entity_id == a.id for item in result.candidates)
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    p = Provenance(ProvenanceId(UUID(int=3)), source.id, at)
    new = Concept(ConceptId(UUID(int=20)), "new indexed token", p, Confidence(0.5), at)
    repo.put(new)
    assert not index.lexical("indexed", 10)
    index.sync()
    assert index.lexical("indexed", 10)[0].entity_id == new.id
    index.clear()
    with pytest.raises(RetrievalError) as error:
        index.lexical("indexed", 10)
    assert error.value.code is RetrievalErrorCode.INDEX_UNAVAILABLE
    index.rebuild()
    assert index.lexical("indexed", 10)[0].entity_id == new.id
    index.version = "999"
    with pytest.raises(RetrievalError) as error:
        index.rebuild()
    assert error.value.code is RetrievalErrorCode.INCOMPATIBLE_INDEX


def test_missing_explicit_entity_and_degraded_materialization():
    repo, source, a, _, _, _, _ = graph()
    retrieval, index = service(repo)
    with pytest.raises(RetrievalError) as error:
        retrieval.recall(RecallRequest(RecallCue(entity_ids=(ObservationId(UUID(int=999)),))))
    assert error.value.code is RetrievalErrorCode.MISSING_ENTITY
    degraded = RetrievalService(repo, index, materialization_check=lambda sid: "PARTIAL_MEMORY")
    with pytest.raises(RetrievalError) as error:
        degraded.recall(RecallRequest(RecallCue(entity_ids=(a.id,))))
    assert error.value.code is RetrievalErrorCode.DEGRADED_MATERIALIZATION
