import pytest

from syune.core import MemoryTraceId, ObservationId
from syune.memory import MemoryTrace, Observation, SQLiteMemoryRepository
from syune.study import (
    Classification, MaterializationState, SqliteStudyRegistry,
    StudyError, StudyService, StudyState,
)


def test_durable_study_restart_rehydration_and_idempotency(tmp_path):
    source = tmp_path / "sample.md"
    source.write_text("# Heading\n\nAlpha\n\nBeta\n", encoding="utf-8")
    study_db = tmp_path / "state" / "study.sqlite3"
    memory_db = tmp_path / "state" / "memory.sqlite3"
    with SqliteStudyRegistry(study_db) as registry, SQLiteMemoryRepository(memory_db) as memory:
        service = StudyService(registry, memory, tmp_path)
        first = service.study(source)
        assert first.status.is_studied
        assert first.materialization is MaterializationState.MATERIALIZED
        revision = first.status.revision_id
        derived = first.status.derived_memory_ids
    with SqliteStudyRegistry(study_db) as registry, SQLiteMemoryRepository(memory_db) as memory:
        service = StudyService(registry, memory, tmp_path)
        assert service.materialization_status(revision) is MaterializationState.MATERIALIZED
        for index, value in enumerate(derived):
            item = memory.get(ObservationId.parse(value) if index % 2 == 0 else MemoryTraceId.parse(value))
            assert isinstance(item, Observation if index % 2 == 0 else MemoryTrace)
            assert item.provenance.source_id == first.status.source_id
            assert item.provenance.locator.block is not None
        duplicate = service.study(source)
        assert duplicate.classification is Classification.ALREADY_STUDIED
        assert duplicate.materialization is MaterializationState.MATERIALIZED
        assert duplicate.status.derived_memory_ids == derived
        assert memory._db.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 7


def test_missing_and_partial_materialization_detected(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("First\n\nSecond", encoding="utf-8")
    with SqliteStudyRegistry(tmp_path / "study.sqlite3") as registry, SQLiteMemoryRepository(tmp_path / "memory.sqlite3") as memory:
        service = StudyService(registry, memory, tmp_path)
        result = service.study(source)
        assert service.materialization_status(result.status.revision_id) is MaterializationState.MATERIALIZED
        trace_id = result.status.derived_memory_ids[1]
        memory._db.execute("DELETE FROM entities WHERE id_type='MemoryTraceId' AND id_value=?", (trace_id,))
        memory._db.commit()
        assert service.materialization_status(result.status.revision_id) is MaterializationState.PARTIAL_MEMORY
        duplicate = service.study(source)
        assert duplicate.materialization is MaterializationState.PARTIAL_MEMORY
        memory._db.execute("DELETE FROM entities")
        memory._db.commit()
        assert service.materialization_status(result.status.revision_id) is MaterializationState.MISSING_MEMORY


def test_failed_durable_batch_never_marks_encoded(tmp_path):
    class FailingMemory(SQLiteMemoryRepository):
        def put_many(self, entities):
            if any(isinstance(item, Observation) for item in entities):
                raise RuntimeError("synthetic durable write failure")
            super().put_many(entities)

    source = tmp_path / "source.txt"
    source.write_text("A block", encoding="utf-8")
    with SqliteStudyRegistry(tmp_path / "study.sqlite3") as registry, FailingMemory(tmp_path / "memory.sqlite3") as memory:
        service = StudyService(registry, memory, tmp_path)
        with pytest.raises(StudyError):
            service.study(source)
        status = registry.by_locator(str(source.resolve()))
        assert status.state is StudyState.FAILED
        assert not status.is_studied
        assert status.blocks_encoded == 0
        assert service.materialization_status(status.revision_id) is MaterializationState.NOT_ENCODED
