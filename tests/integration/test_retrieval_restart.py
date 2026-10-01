from datetime import datetime, timezone
from uuid import UUID

from syune.core import AssociationId, ConceptId, Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import Association, Concept, Observation, Provenance, Source, SourceLocator, SQLiteMemoryRepository
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService


def test_restart_rebuild_determinism_and_no_durable_mutation(tmp_path):
    path = tmp_path / "memory.sqlite3"
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    sid = SourceId(UUID(int=1))
    oid = ObservationId(UUID(int=2))
    cid = ConceptId(UUID(int=3))
    provenance = Provenance(ProvenanceId(UUID(int=4)), sid, at, locator=SourceLocator(page=1))
    cue = RecallCue(text="forest planning")
    with SQLiteMemoryRepository(path) as repo:
        repo.put(Source(sid, "file", "synthetic", at))
        repo.put(Observation(oid, "forest planning", "paragraph", provenance, at, at))
        repo.put(Concept(cid, "strategy", provenance, Confidence(0.4), at))
        repo.add_association(Association(AssociationId(UUID(int=5)), oid, cid,
                                         "associated_with", provenance, Confidence(0.5), at))
        index = InvertedSeedIndex(repo)
        index.rebuild()
        before = tuple(repo._db.execute("SELECT * FROM entities ORDER BY id_type,id_value"))
        before_edges = tuple(repo._db.execute("SELECT * FROM associations ORDER BY id_value"))
        first = RetrievalService(repo, index).recall(RecallRequest(cue))
        assert len(first.candidates) >= 2
        assert tuple(repo._db.execute("SELECT * FROM entities ORDER BY id_type,id_value")) == before
        assert tuple(repo._db.execute("SELECT * FROM associations ORDER BY id_value")) == before_edges
    with SQLiteMemoryRepository(path) as repo:
        index = InvertedSeedIndex(repo)
        index.rebuild()
        second = RetrievalService(repo, index).recall(RecallRequest(cue))
        assert [(x.entity_id, x.score) for x in first.candidates] == [(x.entity_id, x.score) for x in second.candidates]
        assert tuple(repo._db.execute("SELECT * FROM entities ORDER BY id_type,id_value")) == before
        assert tuple(repo._db.execute("SELECT * FROM associations ORDER BY id_value")) == before_edges
