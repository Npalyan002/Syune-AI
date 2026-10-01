from dataclasses import FrozenInstanceError
from datetime import datetime
from uuid import UUID

import pytest

from syune.core import (
    AssociationId, ClaimId, Confidence, MemoryTraceId, ObservationId,
)
from syune.memory import (
    ActivationState, Association, InMemoryReferenceRepository, MemoryTrace,
    MissingEndpointError, Observation, Provenance, SourceLocator,
)


def make_observation(now, provenance, value=40):
    return Observation(
        ObservationId(UUID(int=value)), "The document says X.", "text",
        provenance, now, now,
    )


def test_observation_is_typed_immutable_and_non_epistemic(now, provenance):
    item = make_observation(now, provenance)
    assert item.id == ObservationId(UUID(int=40))
    assert item.content == "The document says X."
    assert item.extraction_confidence is None
    assert not hasattr(item, "claim_ids")
    assert not hasattr(item, "statement")
    assert item.schema_version == "1"
    assert item.id != ClaimId(UUID(int=40))
    with pytest.raises(FrozenInstanceError):
        item.content = "X is true."


def test_observation_requires_provenance_and_valid_time(now, provenance):
    with pytest.raises(ValueError):
        Observation(ObservationId.new(), "text", "text", None, now, now)
    with pytest.raises(ValueError):
        Observation(ObservationId.new(), "text", "text", provenance, datetime(2026, 1, 1), now)
    with pytest.raises(ValueError):
        Observation(ObservationId.new(), " ", "text", provenance, now, now)
    with pytest.raises(TypeError):
        Observation(ObservationId.new(), "text", "text", provenance, now, now, 0.8)


def test_observation_provenance_preserves_source_locator(now, ids):
    provenance = Provenance(
        ids["provenance"], ids["source"], now,
        locator=SourceLocator(page=3, section="Results", block="b-7", span="12:40"),
        process_id="text-extraction", pipeline_version="v1",
    )
    item = Observation(
        ObservationId.new(), "A quoted passage", "text", provenance,
        now, now, Confidence(0.8),
    )
    assert item.provenance.source_id == ids["source"]
    assert item.provenance.locator.page == 3
    assert item.provenance.locator.block == "b-7"
    assert item.extraction_confidence == Confidence(0.8)


def test_observation_trace_and_generic_association(now, provenance):
    repo = InMemoryReferenceRepository()
    observed = make_observation(now, provenance)
    another = make_observation(now, provenance, 41)
    trace = MemoryTrace(
        MemoryTraceId(UUID(int=42)), observed.id, now,
        provenance, Confidence(0.7), now,
    )
    with pytest.raises(MissingEndpointError):
        repo.put(trace)
    repo.put(observed)
    repo.put(another)
    repo.put(trace)
    assert repo.get(observed.id) == observed
    assert repo.get(trace.id).entity_id == observed.id
    association = Association(
        AssociationId(UUID(int=43)), observed.id, another.id,
        "associated_with", provenance, Confidence(0.4), now,
    )
    repo.add_association(association)
    assert repo.associations_for(observed.id) == (association,)
    assert repo.exists(observed.id)
    assert ActivationState(observed.id, 1.0, now).node_id == observed.id
