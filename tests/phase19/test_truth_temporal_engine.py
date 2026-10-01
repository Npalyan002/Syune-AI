from datetime import datetime, timezone

from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (
    ContradictionKind, InMemoryReferenceRepository, Observation, Provenance, QueryMode,
    SQLiteMemoryRepository, Source, TruthMetadata, TruthState, VerificationPolicy,
    classify_disagreement,
)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService


def at(year, month=1, day=1): return datetime(year, month, day, tzinfo=timezone.utc)


def build(repo, rows):
    source = Source(SourceId.new(), "test", "truth", at(2020))
    repo.put(source)
    ids = []
    for text, truth in rows:
        oid = ObservationId.new(); ids.append(oid)
        provenance = Provenance(ProvenanceId.new(), source.id, truth.recorded_at or at(2020))
        repo.put(Observation(oid, text, "text", provenance, truth.recorded_at or at(2020),
                             truth.recorded_at or at(2020), Confidence(1), truth))
    index = InvertedSeedIndex(repo); index.rebuild()
    return ids, RetrievalService(repo, index)


def result_ids(service, **cue):
    return tuple(item.entity_id for item in service.recall(RecallRequest(RecallCue(text="vendor", **cue))).candidates)


def test_current_historical_as_of_and_future_knowledge_are_distinct():
    repo = InMemoryReferenceRepository()
    old = TruthMetadata(TruthState.VERIFIED, at(2025, 1, 2), at(2025, 1, 1), at(2025, 6, 1),
                        fact_key="vendor", fact_value="a")
    new = TruthMetadata(TruthState.VERIFIED, at(2025, 6, 2), at(2025, 6, 1), None,
                        fact_key="vendor", fact_value="b")
    ids, service = build(repo, (("vendor A", old), ("vendor B", new)))
    assert result_ids(service, valid_at=at(2025, 7, 1)) == (ids[1],)
    assert result_ids(service, query_mode=QueryMode.HISTORICAL, valid_at=at(2025, 3, 1)) == (ids[0],)
    assert result_ids(service, query_mode=QueryMode.AS_OF, valid_at=at(2025, 7, 1),
                      knowledge_at=at(2025, 5, 1)) == ()


def test_supersession_is_order_independent_and_history_remains_traceable():
    repo = InMemoryReferenceRepository()
    first_id = ObservationId.new()
    source = Source(SourceId.new(), "test", "truth", at(2020)); repo.put(source)
    newer = ObservationId.new()
    new_truth = TruthMetadata(TruthState.VERIFIED, at(2025, 2, 1), at(2025, 2, 1),
                              revision_of=first_id, supersedes=(first_id,), fact_key="vendor", fact_value="b")
    p2 = Provenance(ProvenanceId.new(), source.id, at(2025, 2, 1))
    repo.put(Observation(newer, "vendor B", "text", p2, at(2025, 2, 1), at(2025, 2, 1), Confidence(1), new_truth))
    old_truth = TruthMetadata(TruthState.VERIFIED, at(2025, 3, 1), at(2025, 1, 1), at(2025, 2, 1),
                              fact_key="vendor", fact_value="a")
    p1 = Provenance(ProvenanceId.new(), source.id, at(2025, 3, 1))
    repo.put(Observation(first_id, "vendor A", "text", p1, at(2025, 1, 1), at(2025, 3, 1), Confidence(1), old_truth))
    index = InvertedSeedIndex(repo); index.rebuild(); service = RetrievalService(repo, index)
    assert first_id not in result_ids(service, valid_at=at(2025, 3, 1))
    assert repo.get(first_id) is not None
    assert any(event.event_type == "memory_superseded" for event in repo.truth_events())


def test_contradiction_context_and_verification_policies():
    base = dict(recorded_at=at(2025), valid_from=at(2025), fact_key="budget")
    a = TruthMetadata(TruthState.VERIFIED, fact_value="1m", context_key="global", **base)
    b = TruthMetadata(TruthState.ASSERTED, fact_value="2m", context_key="global", **base)
    france = TruthMetadata(TruthState.VERIFIED, fact_value="2m", context_key="france", **base)
    assert classify_disagreement(a, b) is ContradictionKind.CONTRADICTION
    assert classify_disagreement(a, france) is ContradictionKind.CONTEXTUAL_DIFFERENCE
    repo = InMemoryReferenceRepository(); ids, service = build(repo, (("vendor verified", a), ("vendor rumor", b)))
    only = result_ids(service, valid_at=at(2025, 2, 1), verification_policy=VerificationPolicy.VERIFIED_ONLY)
    assert only == (ids[0],)
    assert any(event.event_type == "contradiction_detected" for event in repo.truth_events())


def test_orphan_provenance_is_quarantined_and_restart_preserves_truth(tmp_path):
    path = tmp_path / "memory.sqlite3"
    truth = TruthMetadata(TruthState.VERIFIED, at(2025), at(2025), fact_key="vendor", fact_value="a")
    with SQLiteMemoryRepository(path) as repo:
        ids, service = build(repo, (("vendor A", truth),))
        assert ids[0] in result_ids(service, valid_at=at(2025, 2, 1))
    with SQLiteMemoryRepository(path) as repo:
        restored = repo.get(ids[0])
        assert restored.truth == truth
        index = InvertedSeedIndex(repo); index.rebuild()
        assert ids[0] in result_ids(RetrievalService(repo, index), valid_at=at(2025, 2, 1))

    orphan = InMemoryReferenceRepository()
    oid = ObservationId.new()
    orphan.put(Observation(oid, "vendor ghost", "text",
                           Provenance(ProvenanceId.new(), SourceId.new(), at(2025)), at(2025), at(2025),
                           Confidence(1), truth))
    index = InvertedSeedIndex(orphan); index.rebuild()
    assert oid not in result_ids(RetrievalService(orphan, index), valid_at=at(2025, 2, 1))
