import sqlite3

import pytest

from syune.core import (
    AssociationId, Confidence, LearningSignalId, ObservationId, ProvenanceId,
    SourceId, utc_now,
)
from syune.learning import (
    FeedbackLabel, LearningError, LearningSignal, LearningSignalKind,
    LearningSource, LearningTarget, LearningService, SQLiteLearningStore,
    StorePlasticityView,
)
from syune.memory import Association, InMemoryReferenceRepository, Observation, Provenance, Source
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService


def setup_memory():
    memory = InMemoryReferenceRepository()
    at = utc_now()
    source = Source(SourceId.new(), "synthetic", "learning test", at)
    provenance = Provenance(ProvenanceId.new(), source.id, at)
    a = Observation(ObservationId.new(), "shared learning marker alpha", "text", provenance, at, at, Confidence(0.5))
    b = Observation(ObservationId.new(), "shared learning marker beta", "text", provenance, at, at, Confidence(0.5))
    for entity in (source, a, b): memory.put(entity)
    edge = Association(AssociationId.new(), a.id, b.id, "associated_with", provenance, Confidence(0.5), at, 0.2)
    memory.add_association(edge)
    index = InvertedSeedIndex(memory); index.rebuild()
    return memory, index, source, a, b, edge


def make_signal(kind, targets, key, label=None, correlation="episode-1", source=LearningSource.SYSTEM_TEST):
    return LearningSignal(LearningSignalId.new(), kind, utc_now(),
        tuple(LearningTarget(x) for x in targets), source, key,
        ProvenanceId.new(), correlation_id=correlation, feedback_label=label)


def components(candidate): return dict(candidate.components)


def test_explicit_learning_retrieval_no_recall_learning_restart_and_rollback(tmp_path):
    memory, index, source, a, b, edge = setup_memory()
    canonical_before = memory.iter_entities(), memory.associations_for(a.id)
    path = tmp_path / "learning.sqlite3"
    with SQLiteLearningStore(path) as store:
        learning = LearningService(memory, store)
        retrieval = RetrievalService(memory, index, plasticity=StorePlasticityView(store))
        before = retrieval.recall(RecallRequest(RecallCue(text="shared learning marker")))
        overlay_before, signals_before = store.snapshot(), store.count_signals()
        for _ in range(100): retrieval.recall(RecallRequest(RecallCue(text="shared learning marker")))
        assert store.snapshot() == overlay_before and store.count_signals() == signals_before

        positive = make_signal(LearningSignalKind.POSITIVE_OUTCOME, (a.id,), "positive-a")
        assert learning.record(positive)
        assert learning.record(positive)  # same identity and idempotency key is an idempotent retry
        assert len(store.by_target(LearningTarget(a.id).key)) == 1
        assert len(store.by_correlation("episode-1")) == 1
        batch = learning.consolidate_once()
        assert batch.batch.applied_count == 1
        assert store.state(LearningTarget(a.id).key).utility_delta > 0
        after_positive = retrieval.recall(RecallRequest(RecallCue(text="shared learning marker")))
        candidate_a = next(x for x in after_positive.candidates if x.entity_id == a.id)
        assert components(candidate_a)["learned_utility"] > 0
        assert components(candidate_a)["learned_salience"] > 0

        negative = make_signal(LearningSignalKind.NEGATIVE_OUTCOME, (b.id,), "negative-b")
        learning.record(negative); negative_batch = learning.consolidate_once()
        assert store.state(LearningTarget(b.id).key).utility_delta < 0
        candidate_b = next(x for x in retrieval.recall(RecallRequest(RecallCue(text="shared learning marker"))).candidates if x.entity_id == b.id)
        assert components(candidate_b)["learned_utility"] < 0

        coactivation = make_signal(LearningSignalKind.CO_ACTIVATION, (a.id, b.id), "co-a-b")
        learning.record(coactivation); learning.consolidate_once()
        by_id = retrieval.recall(RecallRequest(RecallCue(entity_ids=(a.id,))))
        reached_b = next(x for x in by_id.candidates if x.entity_id == b.id)
        assert components(reached_b)["learned_association"] > 0

        human = make_signal(LearningSignalKind.HUMAN_FEEDBACK, (a.id,), "human-a", FeedbackLabel.USEFUL,
                            source=LearningSource.HUMAN)
        learning.record(human); learning.consolidate_once()
        assert store.state(LearningTarget(a.id).key).update_count == 2
        trace = store.proposal_audit(LearningTarget(a.id).key)
        assert all(len(row) == 4 for row in trace) and {row[1] for row in trace} == {str(positive.id), str(human.id)}

        assert memory.iter_entities() == canonical_before[0]
        assert memory.associations_for(a.id) == canonical_before[1]
        assert learning.consolidate_once().batch.applied_count == 0
        audit_before = store.audit()
        restored = learning.rollback(negative_batch.batch.id)
        assert restored and store.state(LearningTarget(b.id).key).update_count == 0
        assert len(store.audit()) == len(audit_before) + 1
        assert store.get(negative.id) == negative

    with SQLiteLearningStore(path) as reopened:
        assert reopened.count_signals() == 4
        assert reopened.state(LearningTarget(a.id).key).utility_delta > 0
        assert LearningService(memory, reopened).consolidate_once().batch.applied_count == 0


def test_source_retraction_preserves_canonical_memory_and_confidence(tmp_path):
    memory, index, source, a, b, _ = setup_memory()
    with SQLiteLearningStore(tmp_path / "learning.sqlite3") as store:
        learning = LearningService(memory, store)
        learning.record(make_signal(LearningSignalKind.POSITIVE_OUTCOME, (a.id,), "use-a"))
        learning.consolidate_once()
        confidence_before, entities_before = a.extraction_confidence, memory.iter_entities()
        retraction = make_signal(LearningSignalKind.SOURCE_RETRACTION_NOTICE, (source.id,), "retract-source")
        learning.record(retraction); result = learning.consolidate_once()
        assert result.batch.applied_count == 2
        for entity in (a, b):
            state = store.state(LearningTarget(entity.id).key)
            assert state.retraction_flag and state.utility_delta < 0.5
        assert memory.iter_entities() == entities_before
        assert memory.get(a.id).extraction_confidence == confidence_before
        assert any(event[0] == "consolidation.completed" for event in store.audit(str(result.batch.id)))


def test_ledger_queries_duplicate_and_schema_mismatch(tmp_path):
    memory, _, _, a, _, _ = setup_memory()
    path = tmp_path / "learning.sqlite3"
    first = make_signal(LearningSignalKind.POSITIVE_OUTCOME, (a.id,), "same-key", correlation="corr")
    with SQLiteLearningStore(path) as store:
        service = LearningService(memory, store)
        assert service.record(first)
        duplicate = make_signal(LearningSignalKind.POSITIVE_OUTCOME, (a.id,), "same-key", correlation="corr")
        assert not service.record(duplicate)
        assert store.get(first.id) == first and store.pending(10) == (first,)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE metadata SET value='999' WHERE key='schema_version'"); db.commit()
    with pytest.raises(LearningError): SQLiteLearningStore(path)


def test_consolidation_failure_rolls_back_overlay_and_processed_marker(tmp_path):
    memory, _, _, a, _, _ = setup_memory()
    with SQLiteLearningStore(tmp_path / "learning.sqlite3") as store:
        learning = LearningService(memory, store)
        item = make_signal(LearningSignalKind.POSITIVE_OUTCOME, (a.id,), "atomic-failure")
        learning.record(item)
        store._db.execute("CREATE TRIGGER fail_proposal BEFORE INSERT ON proposals BEGIN SELECT RAISE(ABORT,'forced'); END")
        with pytest.raises(sqlite3.IntegrityError): learning.consolidate_once()
        assert store.snapshot() == ()
        assert store.pending(10) == (item,)
        assert store.proposal_audit(LearningTarget(a.id).key) == ()
