from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from uuid import UUID

import pytest

from syune.core import (
    AssociationId, ClaimId, ConceptId, EpisodeId, EvidenceId,
    MemoryTraceId, ProcedureId, ProvenanceId, SourceVersionId,
)
from syune.memory import (
    ActivationState, Association, Claim, Concept, Episode, Evidence,
    EvidencePolarity, MemoryTrace, Procedure, Provenance, Source,
    SourceLocator,
)


def test_provenance_source_locators_and_derivation(now, ids):
    locator = SourceLocator(page=2, section="Intro", timestamp_seconds=3.5, block="b1", span="1:4", region="x")
    parent = Provenance(ids["provenance"], ids["source"], now, locator=locator)
    child = Provenance(
        ProvenanceId(UUID(int=5)), ids["source"], now,
        source_version_id=SourceVersionId(UUID(int=6)),
        process_id="extractor", pipeline_version="v1",
        parent_provenance_ids=(parent.id,),
    )
    assert child.parent_provenance_ids == (parent.id,)
    assert parent.locator.page == 2
    assert child.source_id == parent.source_id


@pytest.mark.parametrize("locator", [
    {"page": 0}, {"page": True}, {"section": ""}, {"timestamp_seconds": -1},
    {"timestamp_seconds": float("nan")}, {"region": " "},
])
def test_invalid_locator(locator):
    with pytest.raises((ValueError, TypeError)):
        SourceLocator(**locator)


def test_provenance_rejects_wrong_reference_and_naive_time(now, ids):
    with pytest.raises(TypeError):
        Provenance(ids["provenance"], ids["concept"], now)
    with pytest.raises(ValueError):
        Provenance(ids["provenance"], ids["source"], datetime(2026, 1, 1))


def test_source_is_distinct_from_derived_memory(now, ids):
    source = Source(ids["source"], "document", "Title", now, locator_uri="urn:syune:test")
    assert source.id == ids["source"]
    assert not hasattr(source, "provenance")
    assert source.schema_version == "1"


def test_all_derived_entity_types(now, ids, provenance, confidence):
    concept = Concept(ids["concept"], "resilience", provenance, confidence, now)
    claim = Claim(ids["claim"], "A proposition", provenance, confidence, now)
    evidence = Evidence(EvidenceId(UUID(int=7)), (claim.id,), EvidencePolarity.CONTRADICTS, "Counterexample", provenance, confidence, now)
    episode = Episode(EpisodeId(UUID(int=8)), "An event", now, provenance, confidence, now)
    procedure = Procedure(ProcedureId(UUID(int=9)), ("Observe", "Record"), provenance, confidence, now)
    trace = MemoryTrace(MemoryTraceId(UUID(int=10)), claim.id, now, provenance, confidence, now)
    for entity in (concept, claim, evidence, episode, procedure, trace):
        assert entity.provenance == provenance
        assert entity.confidence == confidence
        assert entity.schema_version == "1"
    assert evidence.polarity is EvidencePolarity.CONTRADICTS
    assert trace.entity_id == claim.id


def test_missing_provenance_and_wrong_id_rejected(now, ids, confidence):
    with pytest.raises(ValueError):
        Concept(ids["concept"], "x", None, confidence, now)
    with pytest.raises(TypeError):
        Claim(ids["concept"], "x", Provenance(ids["provenance"], ids["source"], now), confidence, now)


def test_creation_time_and_history_immutable(now, ids, provenance, confidence):
    concept = Concept(ids["concept"], "x", provenance, confidence, now)
    with pytest.raises(FrozenInstanceError):
        concept.label = "replacement"
    with pytest.raises(ValueError):
        replace(concept, created_at=datetime(2026, 1, 1))


def test_evidence_and_procedure_structural_validation(now, ids, provenance, confidence):
    with pytest.raises(ValueError):
        Evidence(EvidenceId(UUID(int=12)), (), EvidencePolarity.SUPPORTS, "x", provenance, confidence, now)
    with pytest.raises(ValueError):
        Procedure(ProcedureId(UUID(int=13)), (), provenance, confidence, now)
    with pytest.raises(TypeError):
        MemoryTrace(MemoryTraceId(UUID(int=14)), ids["source"], now, provenance, confidence, now)


def test_association_is_data_not_traversal(now, ids, provenance, confidence):
    association = Association(AssociationId(UUID(int=15)), ids["claim"], ids["concept"], "supported_by", provenance, confidence, now, 0.8)
    assert association.strength == 0.8
    with pytest.raises(TypeError):
        Association(AssociationId(UUID(int=16)), "claim", ids["concept"], "x", provenance, confidence, now)


def test_activation_is_transient_validated_data(now, ids):
    state = ActivationState(ids["concept"], 2.0, now, cue_id="session")
    assert state.value == 2.0
    assert not hasattr(state, "schema_version")
    with pytest.raises(ValueError):
        ActivationState(ids["concept"], float("nan"), now)
    with pytest.raises(ValueError):
        ActivationState(ids["concept"], 1.0, datetime(2026, 1, 1))
