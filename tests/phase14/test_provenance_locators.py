from syune.memory import SQLiteMemoryRepository,Observation
from syune.study import SqliteStudyRegistry,StudyService


def test_repeated_text_has_distinct_exact_segment_locations(tmp_path):
    source=tmp_path/'repeat.txt';source.write_bytes(b'same\n\nsame\n')
    with SQLiteMemoryRepository(tmp_path/'memory.sqlite3') as memory,SqliteStudyRegistry(tmp_path/'study.sqlite3') as registry:
        StudyService(registry,memory,tmp_path).study(source)
        rows=registry._db.execute('SELECT segment_id,locator FROM perception_segments').fetchall()
        assert len(rows)==2 and len({r[0] for r in rows})==2
        assert {r[1] for r in rows}=={'TextLocator(start=0, end=5)','TextLocator(start=6, end=11)'}
        observations=[x for x in memory.iter_entities() if isinstance(x,Observation)]
        assert len({x.provenance.process_id for x in observations})==2
        StudyService(registry,memory,tmp_path).study(source)
        assert len([x for x in memory.iter_entities() if isinstance(x,Observation)])==2
