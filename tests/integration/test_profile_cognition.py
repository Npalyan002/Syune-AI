from syune.core import ActivationProfileId,AssociationId,CognitiveRequestId,Confidence,LearningSignalId,ObservationId,ProvenanceId,SourceId,utc_now
from syune.cognition import CognitiveBudget,CognitiveRequest,CognitiveService,GLOBAL_HARD_LIMITS,ProfileError,ProfileName,ProfileRegistry
from syune.learning import LearningService,LearningSignal,LearningSignalKind,LearningSource,LearningTarget,SQLiteLearningStore,StorePlasticityView
from syune.memory import Association,InMemoryReferenceRepository,Observation,Provenance,Source
from syune.retrieval import InvertedSeedIndex,RetrievalService

def setup():
    memory=InMemoryReferenceRepository();at=utc_now();sources=[Source(SourceId.new(),"synthetic",f"s{n}",at) for n in range(3)];provs=[Provenance(ProvenanceId.new(),s.id,at) for s in sources]
    items=[Observation(ObservationId.new(),text,"text",provs[n%3],at,at,Confidence(.6)) for n,text in enumerate(("shared profile requirement","shared profile constraint","shared profile alternative","shared profile remote evidence","shared profile conflict"))]
    for x in (*sources,*items):memory.put(x)
    relations=("requires","depends_on","supports","contradicted_by")
    for n,relation in enumerate(relations):memory.add_association(Association(AssociationId.new(),items[n].id,items[n+1].id,relation,provs[n%3],Confidence(.5),at,.5))
    index=InvertedSeedIndex(memory);index.rebuild();return memory,index,items

def stable(result):
    return result.status,result.context,result.inferences,result.assessment,result.responses,result.profile_diagnostics

def test_all_profiles_differ_but_share_memory_learning_and_do_not_mutate(tmp_path):
    memory,index,items=setup();before=(memory.iter_entities(),tuple(memory.associations_for(items[0].id)))
    with SQLiteLearningStore(tmp_path/"learning.sqlite3") as store:
        learning=LearningService(memory,store);learning.record(LearningSignal(LearningSignalId.new(),LearningSignalKind.POSITIVE_OUTCOME,utc_now(),(LearningTarget(items[0].id),),LearningSource.SYSTEM_TEST,"p9-shared",items[0].provenance.id,outcome_value=1));learning.consolidate_once()
        learned_before=(store.count_signals(),store.snapshot())
        retrieval=RetrievalService(memory,index,plasticity=StorePlasticityView(store));service=CognitiveService(memory,retrieval);registry=ProfileRegistry()
        request=CognitiveRequest(CognitiveRequestId.new(),text="shared profile",entity_ids=(items[0].id,items[4].id))
        default=service.process(request);explicit=service.process(CognitiveRequest(request.id,text=request.text,entity_ids=request.entity_ids,activation_profile=registry.by_name(ProfileName.GENERAL).id))
        assert default.profile_diagnostics.activation.name is ProfileName.GENERAL
        assert default.context==explicit.context and default.inferences==explicit.inferences
        results={name:service.process(CognitiveRequest(request.id,text=request.text,entity_ids=request.entity_ids,activation_profile=registry.by_name(name).id)) for name in ProfileName}
        assert len({r.profile_diagnostics.activation.fingerprint for r in results.values()})==6
        assert len({r.responses[-1].content for r in results.values()})>=5
        assert any(dict(x.components)["profile_diversity"]>0 for x in results[ProfileName.CREATIVE].context.attention)
        assert all(dict(x.components)["profile_diversity"]==0 for x in results[ProfileName.GENERAL].context.attention)
        assert results[ProfileName.SYSTEMS].inferences[0].type.value=="DIRECT_RELATION"
        assert results[ProfileName.STRATEGY].inferences[0].type.value=="CONFLICT_SIGNAL"
        assert results[ProfileName.RESEARCH].inferences[0].type.value=="SOURCE_OVERLAP"
        assert all(dict(next(x for x in r.context.attention if x.entity_id==items[0].id).components).get("learned_relevance",0)>0 for r in results.values())
        assert (store.count_signals(),store.snapshot())==learned_before
        assert memory.iter_entities()==before[0] and tuple(memory.associations_for(items[0].id))==before[1]
        assert all(service.memory is memory and service.retrieval.plasticity.store is store for _ in results)

def test_invalid_profile_restart_determinism_and_no_auto_classification():
    memory,index,items=setup();request=CognitiveRequest(CognitiveRequestId.new(),text="creative systems research",entity_ids=(items[0].id,))
    first=CognitiveService(memory,RetrievalService(memory,index)).process(request)
    second=CognitiveService(memory,RetrievalService(memory,index),ProfileRegistry()).process(request)
    assert first.profile_diagnostics.activation.name is ProfileName.GENERAL and stable(first)==stable(second)
    huge=CognitiveBudget(9,999,999,999,999,9,999,999,9999)
    clipped=CognitiveService(memory,RetrievalService(memory,index)).process(CognitiveRequest(CognitiveRequestId.new(),text="cue",budget=huge))
    assert clipped.profile_diagnostics.activation.clipped_settings
    assert clipped.profile_diagnostics.activation.effective_budget.max_graph_edges<=GLOBAL_HARD_LIMITS.max_graph_edges
    try:CognitiveService(memory,RetrievalService(memory,index)).process(CognitiveRequest(CognitiveRequestId.new(),text="cue",activation_profile=ActivationProfileId.new()))
    except ProfileError as error:assert error.code.value=="INVALID_PROFILE"
    else:raise AssertionError("unknown profile accepted")
