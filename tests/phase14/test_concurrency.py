from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from threading import Barrier
from scenario import pipeline
from syune.core import *
from syune.memory import SQLiteMemoryRepository
from syune.study import StudyService,SqliteStudyRegistry
from syune.learning import *
from syune.retrieval import *


def test_read_with_explicit_learning_writer_separate_connections(tmp_path):
    with ExitStack() as stack:
        c=pipeline(tmp_path,stack);target=c['observations'][0];before=c['canonical']
        barrier=Barrier(2)
        def writer():
            with SQLiteMemoryRepository(tmp_path/'memory.sqlite3') as memory, SQLiteLearningStore(tmp_path/'learning.sqlite3') as learning:
                service=LearningService(memory,learning);barrier.wait()
                for n in range(20):
                    service.record(LearningSignal(LearningSignalId.new(),LearningSignalKind.POSITIVE_OUTCOME,utc_now(),
                        (LearningTarget(target.id),),LearningSource.SYSTEM_TEST,f'concurrent-{n}',target.provenance.id))
                    service.consolidate_once()
        def reader():
            with SQLiteMemoryRepository(tmp_path/'memory.sqlite3') as memory, SQLiteLearningStore(tmp_path/'learning.sqlite3') as learning:
                index=InvertedSeedIndex(memory);index.rebuild();service=RetrievalService(memory,index,plasticity=StorePlasticityView(learning));barrier.wait()
                for _ in range(100):
                    result=service.recall(RecallRequest(RecallCue(text='Amber')))
                    assert target.id in {x.entity_id for x in result.candidates}
                    assert all(abs(dict(x.components)['learned_utility'])<=.5 for x in result.candidates)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(writer),pool.submit(reader)]
            for future in futures:future.result(timeout=60)
        assert c['memory'].iter_entities()==before and c['learning'].count_signals()==20


def test_study_writer_with_existing_index_reader_is_explicitly_eventual(tmp_path):
    with ExitStack() as stack:
        c=pipeline(tmp_path,stack);barrier=Barrier(2)
        def writer():
            with SQLiteMemoryRepository(tmp_path/'memory.sqlite3') as memory, SqliteStudyRegistry(tmp_path/'study.sqlite3') as registry:
                barrier.wait()
                for n in range(3):
                    source=tmp_path/f'new{n}.txt';source.write_text(f'newmarker{n} source')
                    StudyService(registry,memory,tmp_path).study(source)
        def reader():
            with SQLiteMemoryRepository(tmp_path/'memory.sqlite3') as memory:
                index=InvertedSeedIndex(memory);index.rebuild();service=RetrievalService(memory,index);barrier.wait()
                for _ in range(100): assert service.recall(RecallRequest(RecallCue(text='Amber'))).candidates
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(writer),pool.submit(reader)]
            for future in futures:future.result(timeout=60)
        c['index'].sync()
        assert c['retrieval'].recall(RecallRequest(RecallCue(text='newmarker2'))).candidates
