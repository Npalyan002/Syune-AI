"""Curated correctness judgments over real services, with explicit fixture expectations."""
from contextlib import ExitStack
from dataclasses import replace
import pytest
from scenario import pipeline
from test_cognitive_core import fixture as cognitive_fixture, semantic
from test_profile_cognition import setup as profile_fixture
from test_multimodal_study import Provider, png, mp4, make_wav
from test_study_service import pdf_bytes
from syune.core import *
from syune.cognition import *
from syune.memory import Observation, InMemoryReferenceRepository, SQLiteMemoryRepository
from syune.study import StudyService, SqliteStudyRegistry, Classification
from syune.perception import PerceptionRouter
from syune.retrieval import *
from syune.learning import *
from syune.evals.metrics import retrieval_metrics
from syune.evals.invariants import audit
from syune.evals.model import *
from syune.evals.runner import run_suite
from syune.evals.reporting import report


def test_curated_retrieval_judgments_and_metrics(tmp_path):
    with ExitStack() as stack:
        c = pipeline(tmp_path, stack)
        expected = {o.id for o in c['observations']}
        distractor = Observation(ObservationId.new(),'unrelated orchard rainfall','text',c['observations'][0].provenance,utc_now(),utc_now())
        c['memory'].put(distractor);c['index'].sync()
        for cue in ('Amber','safety','verification'):
            result = c['retrieval'].recall(RecallRequest(RecallCue(text=cue)))
            metrics = retrieval_metrics([x.entity_id for x in result.candidates],expected,2)
            assert metrics == dict(recall_at_k=1,precision_at_k=1,mrr=1,coverage=1,false_positive_rate=0)
        absent = c['retrieval'].recall(RecallRequest(RecallCue(text='absent-lexeme-zxy')))
        assert absent.candidates == ()


def test_learning_many_updates_adversarial_sequence_rollback_and_no_canonical_drift(tmp_path):
    with ExitStack() as stack:
        c=pipeline(tmp_path,stack);target=c['observations'][0];service=LearningService(c['memory'],c['learning'])
        deltas=[]
        for n in range(1000):
            service.record(LearningSignal(LearningSignalId.new(),LearningSignalKind.POSITIVE_OUTCOME,utc_now(),
                (LearningTarget(target.id),),LearningSource.SYSTEM_TEST,f'explicit-{n}',target.provenance.id))
            if n<3 or n%100==99:
                service.consolidate_once();deltas.append(c['learning'].state(LearningTarget(target.id).key).utility_delta)
        assert 0<deltas[1]-deltas[0]<deltas[0] and max(deltas)<=.5
        before=c['learning'].snapshot()
        negative=LearningSignal(LearningSignalId.new(),LearningSignalKind.NEGATIVE_OUTCOME,utc_now(),
            (LearningTarget(target.id),),LearningSource.SYSTEM_TEST,'negative',target.provenance.id)
        service.record(negative);batch=service.consolidate_once();assert c['learning'].state(LearningTarget(target.id).key).utility_delta<.5
        service.rollback(batch.batch.id);assert c['learning'].snapshot()==before
        retraction=replace(negative,id=LearningSignalId.new(),kind=LearningSignalKind.SOURCE_RETRACTION_NOTICE,
            targets=(LearningTarget(c['studied'].status.source_id),),idempotency_key='retraction')
        service.record(retraction);batch=service.consolidate_once()
        assert all(x.retraction_flag for x in c['learning'].snapshot())
        service.rollback(batch.batch.id)
        assert c['memory'].iter_entities()==c['canonical']
        assert c['learning'].count_signals()==1002 and len(c['learning'].audit())>1002
        assert set(x.entity_id for x in c['retrieval'].recall(RecallRequest(RecallCue(text='Amber'))).candidates)=={o.id for o in c['observations']}


@pytest.mark.parametrize('conflict',[False,True])
def test_cognitive_inferences_are_supported_and_repeatable(conflict):
    memory,index,a,b,c=cognitive_fixture(conflict)
    service=CognitiveService(memory,RetrievalService(memory,index))
    request=CognitiveRequest(CognitiveRequestId.new(),entity_ids=(a.id,c.id))
    result=service.process(request)
    types={x.type for x in result.inferences}
    assert InferenceType.DIRECT_RELATION in types
    assert InferenceType.MULTI_HOP_SUPPORT in types
    assert InferenceType.SOURCE_OVERLAP in types
    if conflict: assert InferenceType.CONFLICT_SIGNAL in types and result.conflict
    edges={str(e.id) for entity in memory.iter_entities() for e in memory.associations_for(entity.id)}
    for inference in result.inferences:
        assert set(inference.entity_ids)<={x.id for x in memory.iter_entities()}
        assert set(inference.association_ids)<=edges
    assert semantic(service.process(request))==semantic(result)
    empty=service.process(CognitiveRequest(CognitiveRequestId.new(),text='zxy-nothing'))
    assert empty.status is CognitiveStatus.INSUFFICIENT_EVIDENCE and empty.unresolved_gaps


def test_profile_collapse_threshold_uses_structure_not_profile_names():
    memory,index,items=profile_fixture();before=memory.iter_entities()
    service=CognitiveService(memory,RetrievalService(memory,index));registry=ProfileRegistry()
    structures=set()
    for name in ProfileName:
        result=service.process(CognitiveRequest(CognitiveRequestId.new(),text='shared profile',activation_profile=registry.by_name(name).id))
        structures.add((tuple(x.type for x in result.inferences),tuple(x.score for x in result.context.attention)))
        assert set(result.context.entity_ids)<={x.id for x in before}
    assert len(structures)>=3, 'profile structure collapsed below 3 distinct configurations'
    assert memory.iter_entities()==before


def test_multimodal_cross_retrieval_locator_integrity_and_duplicate_identities(tmp_path):
    paths=[tmp_path/'text.txt',tmp_path/'document.pdf',tmp_path/'image.png',tmp_path/'audio.wav',tmp_path/'video.mp4']
    paths[0].write_text('shared bridge text');paths[1].write_bytes(pdf_bytes('shared bridge PDF'))
    paths[2].write_bytes(png());make_wav(paths[3]);paths[4].write_bytes(mp4())
    router=PerceptionRouter(image_provider=Provider('image'),audio_provider=Provider('audio'),video_provider=Provider('video'))
    with SQLiteMemoryRepository(tmp_path/'memory.sqlite3') as memory, SqliteStudyRegistry(tmp_path/'study.sqlite3') as registry:
        service=StudyService(registry,memory,tmp_path,router)
        results=[service.study(p) for p in paths];before=memory.iter_entities()
        for path,result in zip(paths,results):
            repeat=service.study(path);alias=tmp_path/('alias-'+path.name);alias.write_bytes(path.read_bytes());renamed=service.study(alias)
            assert repeat.classification is renamed.classification is Classification.ALREADY_STUDIED
            assert renamed.status.source_id==result.status.source_id
        assert memory.iter_entities()==before
        index=InvertedSeedIndex(memory);index.rebuild()
        found=RetrievalService(memory,index).recall(RecallRequest(RecallCue(text='bridge')))
        assert {x.source_id for x in found.candidates}=={x.status.source_id for x in results}
        kinds={memory.get(x.entity_id).content_kind for x in found.candidates}
        assert {'caption','transcript','scene_description'}<=kinds
        assert all(x.locator is not None for x in found.candidates)
        checked=audit(memory,registry);assert checked.health is Health.HEALTHY,checked.issues


def test_eval_contract_fail_closed_missing_metrics_and_sanitized_errors():
    case=EvalCase('fixture-integrity',Category.MEMORY,'verify shared fixture','local',
        (EvalExpectation('no broken references','errors',0,0),),('synthetic-reference',))
    suite=EvalSuite('unit-contract',(case,))
    result=run_suite(suite,{'fixture-integrity':lambda:((EvalMetric('errors',0),),('audit:passed',))},'trace-contract')
    assert report(result,required_cases=(case.id,)).readiness is Readiness.READY
    assert report(result,required_cases=('not-run',)).readiness is Readiness.BLOCKED
    failed=run_suite(suite,{},'trace-contract')
    assert failed.failures and report(failed,required_cases=(case.id,)).health is Health.UNHEALTHY
    assert len(Category)==15
