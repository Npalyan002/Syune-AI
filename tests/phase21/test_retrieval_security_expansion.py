"""AML-09I adversarial authorization-boundary coverage."""
from datetime import datetime, timezone

from syune.core import AssociationId, Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (
    AccessContext, Association, InMemoryReferenceRepository, Observation, Principal,
    Provenance, SecurityEnvelope, Source,
)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService


def test_unauthorized_lexical_seed_cannot_reveal_authorized_neighbor() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo = InMemoryReferenceRepository()
    source = Source(SourceId.new(), "audit", "aml09i", now)
    provenance = Provenance(ProvenanceId.new(), source.id, now)
    secret = Observation(
        ObservationId.new(), "cinnabar-private-trigger", "text", provenance, now, now,
        Confidence(1), security=SecurityEnvelope(owner="user:alice", agent_scope="agent-a"),
    )
    public = Observation(
        ObservationId.new(), "ordinary public note", "text", provenance, now, now,
        Confidence(1), security=SecurityEnvelope(owner="user:bob", agent_scope="agent-b"),
    )
    for item in (source, secret, public):
        repo.put(item)
    repo.add_association(Association(
        AssociationId.new(), secret.id, public.id, "associated_with", provenance,
        Confidence(1), now, 1.0,
    ))
    index = InvertedSeedIndex(repo)
    index.rebuild()
    service = RetrievalService(repo, index)
    access = AccessContext(Principal("bob", "agent-b"), "audit", legacy_local_compatible=False)

    result = service.recall(RecallRequest(RecallCue(
        text="cinnabar-private-trigger", access_context=access,
    )))

    assert result.candidates == ()
