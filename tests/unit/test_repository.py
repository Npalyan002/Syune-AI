from uuid import UUID

import pytest

from syune.core import AssociationId, ConceptId, EvidenceId, MemoryTraceId, SourceId
from syune.memory import (
    Association, Claim, Concept, DuplicateIdError, Evidence,
    EvidencePolarity, InMemoryReferenceRepository, MemoryTrace,
    MissingEndpointError, Source,
)


def test_structural_put_get_and_generic_storage(now, ids, provenance, confidence):
    repo = InMemoryReferenceRepository()
    source = Source(ids["source"], "observation", "Observed", now)
    concept = Concept(ids["concept"], "idea", provenance, confidence, now)
    claim = Claim(ids["claim"], "assertion", provenance, confidence, now)
    for entity in (source, concept, claim):
        repo.put(entity)
        assert repo.exists(entity.id)
        assert repo.get(entity.id) == entity
    assert repo.get(ConceptId(UUID(int=99))) is None
    assert not hasattr(repo, "creative_memory")
    assert not hasattr(repo, "finance_memory")


def test_duplicate_ids_are_explicit(now, ids, provenance, confidence):
    repo = InMemoryReferenceRepository()
    first = Concept(ids["concept"], "first", provenance, confidence, now)
    repo.put(first)
    with pytest.raises(DuplicateIdError):
        repo.put(Concept(ids["concept"], "replacement", provenance, confidence, now))
    assert repo.get(ids["concept"]) == first


def test_association_endpoint_integrity_and_direct_listing(now, ids, provenance, confidence):
    repo = InMemoryReferenceRepository()
    repo.put(Concept(ids["concept"], "idea", provenance, confidence, now))
    assoc = Association(AssociationId(UUID(int=20)), ids["concept"], ids["claim"], "related_to", provenance, confidence, now)
    with pytest.raises(MissingEndpointError):
        repo.add_association(assoc)
    repo.put(Claim(ids["claim"], "x", provenance, confidence, now))
    repo.add_association(assoc)
    assert repo.get_association(assoc.id) == assoc
    assert repo.associations_for(ids["concept"]) == (assoc,)
    assert repo.associations_for(ids["claim"]) == (assoc,)
    with pytest.raises(DuplicateIdError):
        repo.add_association(assoc)


def test_no_silent_history_overwrite(now, ids, provenance, confidence):
    repo = InMemoryReferenceRepository()
    claim = Claim(ids["claim"], "original", provenance, confidence, now)
    repo.put(claim)
    with pytest.raises(DuplicateIdError):
        repo.put(Claim(ids["claim"], "revised", provenance, confidence, now))
    assert repo.get(claim.id).statement == "original"


def test_wrong_entity_rejected():
    repo = InMemoryReferenceRepository()
    with pytest.raises(TypeError):
        repo.put({"id": SourceId(UUID(int=1))})


def test_evidence_and_trace_references_must_exist(now, ids, provenance, confidence):
    repo = InMemoryReferenceRepository()
    evidence = Evidence(
        EvidenceId(UUID(int=30)), (ids["claim"],), EvidencePolarity.SUPPORTS,
        "support", provenance, confidence, now,
    )
    trace = MemoryTrace(MemoryTraceId(UUID(int=31)), ids["concept"], now, provenance, confidence, now)
    with pytest.raises(MissingEndpointError):
        repo.put(evidence)
    with pytest.raises(MissingEndpointError):
        repo.put(trace)
    repo.put(Claim(ids["claim"], "assertion", provenance, confidence, now))
    repo.put(Concept(ids["concept"], "concept", provenance, confidence, now))
    repo.put(evidence)
    repo.put(trace)
    assert repo.get(evidence.id) == evidence
    assert repo.get(trace.id) == trace


def test_repository_rejects_untyped_queries():
    repo = InMemoryReferenceRepository()
    with pytest.raises(TypeError):
        repo.get("name")
    with pytest.raises(TypeError):
        repo.exists("name")
    with pytest.raises(TypeError):
        repo.associations_for("name")
    with pytest.raises(TypeError):
        repo.get_association("name")
