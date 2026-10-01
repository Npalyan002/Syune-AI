from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID

import pytest

from syune.core import (
    AssociationId, ClaimId, ConceptId, Confidence, EpisodeId, EvidenceId,
    MemoryTraceId, ObservationId, ProcedureId, ProvenanceId, SourceId,
    SourceVersionId,
)
from syune.memory import (
    Association, Claim, Concept, DuplicateIdError, Episode, Evidence,
    EvidencePolarity, InMemoryReferenceRepository, MemoryTrace,
    MissingEndpointError, Observation, Procedure, Provenance, Source,
    SourceLocator, SQLiteMemoryRepository,
)


def sample_entities():
    at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    ids = [cls(UUID(int=n)) for n, cls in enumerate((
        SourceId, ObservationId, ConceptId, ClaimId, EvidenceId,
        EpisodeId, ProcedureId, MemoryTraceId, AssociationId,
    ), 1)]
    source, observation, concept, claim, evidence, episode, procedure, trace, association = ids
    provenance = Provenance(ProvenanceId(UUID(int=50)), source, at,
                            SourceVersionId(UUID(int=51)),
                            SourceLocator(page=2, section="Part", block="b1", span="1-4"),
                            "study", "1", (ProvenanceId(UUID(int=52)),))
    objects = (
        Source(source, "file", "sample", at, SourceVersionId(UUID(int=51)), "abc", "file:///sample", "text/plain"),
        Observation(observation, "perceived text", "paragraph", provenance, at, at, None),
        Concept(concept, "label", provenance, Confidence(0.2), at),
        Claim(claim, "statement", provenance, Confidence(0.3), at),
        Evidence(evidence, (claim,), EvidencePolarity.SUPPORTS, "summary", provenance, Confidence(0.4), at),
        Episode(episode, "event", at, provenance, Confidence(0.5), at),
        Procedure(procedure, ("step 1", "step 2"), provenance, Confidence(0.6), at),
        MemoryTrace(trace, observation, at, provenance, Confidence(1.0), at),
    )
    edge = Association(association, observation, claim, "related_to", provenance, Confidence(0.7), at, 0.8)
    return objects, edge


@pytest.mark.parametrize("adapter", ["memory", "sqlite"])
def test_repository_contract_parity(tmp_path, adapter):
    repo = InMemoryReferenceRepository() if adapter == "memory" else SQLiteMemoryRepository(tmp_path / "memory.sqlite3")
    objects, edge = sample_entities()
    try:
        with pytest.raises(MissingEndpointError):
            repo.put(objects[-1])
        with pytest.raises(MissingEndpointError):
            repo.add_association(edge)
        for item in objects:
            repo.put(item)
            assert repo.exists(item.id)
            assert repo.get(item.id) == item
        repo.add_association(edge)
        assert repo.get_association(edge.id) == edge
        assert repo.associations_for(edge.source_id) == (edge,)
        assert repo.associations_for(edge.target_id) == (edge,)
        with pytest.raises(DuplicateIdError):
            repo.put(objects[0])
        with pytest.raises(DuplicateIdError):
            repo.add_association(edge)
        with pytest.raises(TypeError):
            repo.get("untyped")
    finally:
        if adapter == "sqlite":
            repo.close()


def test_all_entities_and_provenance_survive_reopen(tmp_path):
    path = tmp_path / "state" / "memory.sqlite3"
    objects, edge = sample_entities()
    with SQLiteMemoryRepository(path) as repo:
        for item in objects:
            repo.put(item)
        repo.add_association(edge)
    with SQLiteMemoryRepository(path) as repo:
        for item in objects:
            restored = repo.get(item.id)
            assert restored == item
            assert type(restored.id) is type(item.id)
        assert repo.get_association(edge.id) == edge
        assert repo.associations_for(edge.source_id) == (edge,)
        assert repo.get(objects[-1].id).entity_id == objects[1].id
        assert repo.get(objects[1].id).provenance.locator.page == 2


def test_atomic_batch_rolls_back_and_schema_version_rejected(tmp_path):
    path = tmp_path / "memory.sqlite3"
    objects, _ = sample_entities()
    with SQLiteMemoryRepository(path) as repo:
        repo.put(objects[0])
        with pytest.raises(MissingEndpointError):
            repo.put_many((objects[1], replace(objects[-1], entity_id=ObservationId(UUID(int=999)))))
        assert not repo.exists(objects[1].id)
        assert not repo.exists(objects[-1].id)
        assert repo._db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "1"
        repo._db.execute("UPDATE metadata SET value='999' WHERE key='schema_version'")
        repo._db.commit()
    with pytest.raises(ValueError, match="incompatible memory schema"):
        SQLiteMemoryRepository(path)
