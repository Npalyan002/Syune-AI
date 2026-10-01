from datetime import timedelta
from syune.core import AssociationId,CognitiveRequestId,Confidence,EpisodeId,InferenceId,LearningSignalId,ObservationId,ProvenanceId,SourceId,utc_now
from syune.cognition import CognitiveBudget,CognitiveRequest,CognitiveService,CognitiveStatus,InferenceRecord,InferenceType,MetacognitionService,ResponseType
from syune.learning import LearningService,LearningSignal,LearningSignalKind,LearningSource,LearningTarget,SQLiteLearningStore,StorePlasticityView
from syune.memory import Association,Episode,InMemoryReferenceRepository,Observation,Provenance,Source
from syune.retrieval import InvertedSeedIndex,RetrievalService

def fixture(conflict=False):
    memory=InMemoryReferenceRepository();at=utc_now();s1=Source(SourceId.new(),"synthetic","s1",at);s2=Source(SourceId.new(),"synthetic","s2",at)
    p1=Provenance(ProvenanceId.new(),s1.id,at);p2=Provenance(ProvenanceId.new(),s2.id,at)
    a=Observation(ObservationId.new(),"cognitive amber marker", "text",p1,at,at,Confidence(.6))
    b=Observation(ObservationId.new(),"cognitive bridge marker", "text",p1,at,at,Confidence(.6))
    c=Observation(ObservationId.new(),"cognitive lattice marker", "text",p2,at,at,Confidence(.6))
    for x in (s1,s2,a,b,c):memory.put(x)
    rel="contradicted_by" if conflict else "supports"
    memory.add_association(Association(AssociationId.new(),a.id,b.id,rel,p1,Confidence(.5),at,.6))
    memory.add_association(Association(AssociationId.new(),b.id,c.id,"supports",p2,Confidence(.5),at,.6))
    index=InvertedSeedIndex(memory);index.rebuild();return memory,index,a,b,c

def semantic(result):return result.status,result.context,result.inferences,result.assessment,result.responses,result.unresolved_gaps,result.conflict,result.truncated

def test_ready_multihop_bounded_and_restart_deterministic():
    memory,index,a,b,c=fixture();service=CognitiveService(memory,RetrievalService(memory,index))
    request=CognitiveRequest(CognitiveRequestId.new(),entity_ids=(a.id,c.id),budget=CognitiveBudget(max_inference_depth=2,max_inference_paths=8))
    first=service.process(request);second=CognitiveService(memory,RetrievalService(memory,index)).process(request)
    assert first.status is CognitiveStatus.READY
    assert {InferenceType.DIRECT_RELATION,InferenceType.MULTI_HOP_SUPPORT,InferenceType.CONVERGENT_SUPPORT} & {x.type for x in first.inferences}
    assert all(len(x.association_ids)<=2 for x in first.inferences if x.type is InferenceType.MULTI_HOP_SUPPORT)
    assert first.responses[0].type is ResponseType.ANSWER_SUMMARY
    assert semantic(first)==semantic(second)

def test_insufficient_conflicted_budget_and_no_mutation(tmp_path):
    memory,index,a,b,c=fixture();canonical=(memory.iter_entities(),memory.associations_for(a.id))
    with SQLiteLearningStore(tmp_path/"learning.sqlite3") as store:
        service=CognitiveService(memory,RetrievalService(memory,index,plasticity=StorePlasticityView(store)))
        before=(store.count_signals(),store.snapshot())
        insufficient=service.process(CognitiveRequest(CognitiveRequestId.new(),text="absent lexical cue"))
        assert insufficient.status is CognitiveStatus.INSUFFICIENT_EVIDENCE
        assert insufficient.responses[0].type is ResponseType.REPORT_INSUFFICIENT_EVIDENCE
        for _ in range(20):service.process(CognitiveRequest(CognitiveRequestId.new(),text="cognitive marker"))
        assert (store.count_signals(),store.snapshot())==before
    conflict_memory,conflict_index,x,y,z=fixture(True)
    conflict=CognitiveService(conflict_memory,RetrievalService(conflict_memory,conflict_index)).process(CognitiveRequest(CognitiveRequestId.new(),entity_ids=(x.id,y.id)))
    assert conflict.status is CognitiveStatus.CONFLICTED and conflict.responses[0].type is ResponseType.REPORT_CONFLICT
    assert memory.iter_entities()==canonical[0] and memory.associations_for(a.id)==canonical[1]
    limited=CognitiveService(memory,RetrievalService(memory,index)).process(CognitiveRequest(CognitiveRequestId.new(),text="cognitive marker",budget=CognitiveBudget(max_active_entities=1)))
    assert "working_context" in limited.truncated and len(limited.context.entity_ids)==1

def test_learned_relevance_visible_in_attention(tmp_path):
    memory,index,a,b,c=fixture()
    with SQLiteLearningStore(tmp_path/"learning.sqlite3") as store:
        learning=LearningService(memory,store)
        learning.record(LearningSignal(LearningSignalId.new(),LearningSignalKind.POSITIVE_OUTCOME,utc_now(),(LearningTarget(a.id),),LearningSource.SYSTEM_TEST,"phase08-learned-relevance",a.provenance.id,outcome_value=1))
        learning.consolidate_once()
        result=CognitiveService(memory,RetrievalService(memory,index,plasticity=StorePlasticityView(store))).process(CognitiveRequest(CognitiveRequestId.new(),text="cognitive marker"))
        item=next(x for x in result.context.attention if x.entity_id==a.id)
        assert dict(item.components)["learned_relevance"]>0

def test_temporal_order_and_source_overlap():
    memory=InMemoryReferenceRepository();at=utc_now();source=Source(SourceId.new(),"synthetic","time",at);p=Provenance(ProvenanceId.new(),source.id,at)
    e1=Episode(EpisodeId.new(),"first",at,p,Confidence(.5),at);e2=Episode(EpisodeId.new(),"second",at+timedelta(microseconds=1),p,Confidence(.5),at)
    for x in (source,e1,e2):memory.put(x)
    index=InvertedSeedIndex(memory);index.rebuild();result=CognitiveService(memory,RetrievalService(memory,index)).process(CognitiveRequest(CognitiveRequestId.new(),entity_ids=(e1.id,e2.id)))
    assert InferenceType.TEMPORAL_ORDER in {x.type for x in result.inferences}
    assert InferenceType.SOURCE_OVERLAP in {x.type for x in result.inferences}

def test_metacognition_partial_degraded_and_limit_states():
    service=MetacognitionService();entity=ObservationId.new()
    gap=InferenceRecord(InferenceId.new(),InferenceType.MISSING_LINK,(entity,),(),(),"structural:missing_link:v1",0,"no link")
    partial=service.assess(active_count=1,active_capacity=8,source_count=1,inferences=(gap,),confidence_values=(.4,),truncated=())
    degraded=service.assess(active_count=1,active_capacity=8,source_count=1,inferences=(),confidence_values=(),truncated=(),degraded=True)
    limited=service.assess(active_count=1,active_capacity=8,source_count=1,inferences=(),confidence_values=(),truncated=("working_context",))
    assert partial.status is CognitiveStatus.PARTIAL
    assert degraded.status is CognitiveStatus.DEGRADED_MEMORY
    assert limited.status is CognitiveStatus.LIMIT_REACHED
