from syune.core import AssociationId,Confidence,CognitiveRequestId,CouncilRequestId,ObservationId,ProvenanceId,SourceId,utc_now
from dataclasses import replace
from syune.cognition import CognitiveBudget,CognitiveRequest,CognitiveService,ProfileName,ProfileRegistry
from syune.council import CouncilBudget,CouncilError,CouncilErrorCode,CouncilMemberSpec,CouncilRequest,CouncilService,CouncilStatus,GapKind,MemberStatus,SynthesisMode
from syune.learning import SQLiteLearningStore,StorePlasticityView
from syune.memory import Association,InMemoryReferenceRepository,Observation,Provenance,Source,SourceLocator
from syune.retrieval import InvertedSeedIndex,RetrievalService

def fixture(count=12,plasticity=None):
    memory=InMemoryReferenceRepository();now=utc_now();sources=[Source(SourceId.new(),"synthetic",f"s{n}",now) for n in range(3)];provs=[Provenance(ProvenanceId.new(),s.id,now,locator=SourceLocator(region=f"r{n}")) for n,s in enumerate(sources)];items=[]
    for n in range(count):
        locator=SourceLocator(timestamp_seconds=float(n),region=f"region-{n}");p=Provenance(ProvenanceId.new(),sources[n%3].id,now,locator=locator);item=Observation(ObservationId.new(),f"council shared evidence {n}","caption" if n%3==0 else "transcript" if n%3==1 else "text",p,now,now,Confidence(.6));memory.put(item);items.append(item)
    for n in range(count-1):memory.add_association(Association(AssociationId.new(),items[n].id,items[n+1].id,"contradicted_by" if n==0 else "supports",items[n].provenance,Confidence(.5),now,.5))
    index=InvertedSeedIndex(memory);index.rebuild();return memory,index,items,CognitiveService(memory,RetrievalService(memory,index,plasticity=plasticity))
def specs(*names):
    registry=ProfileRegistry();return tuple(CouncilMemberSpec(registry.by_name(name).id) for name in names)
def stable(result):
    members=tuple((x.profile_id,x.profile_version,x.profile_fingerprint,x.status,x.evidence_ids,x.source_ids,x.inference_ids,x.error_code,x.error_message,
        None if x.cognitive_result is None else (x.cognitive_result.status,x.cognitive_result.context,x.cognitive_result.inferences,x.cognitive_result.assessment,x.cognitive_result.responses,x.cognitive_result.profile_diagnostics)) for x in result.members)
    return result.status,result.run,members,result.evidence_map,result.agreements,result.disagreements,result.gaps,result.minority_insights,result.synthesis

def test_convergence_divergence_minority_multimodal_neutrality_and_determinism(tmp_path):
    with SQLiteLearningStore(tmp_path/"learning.sqlite3") as store:
        memory,index,items,cognitive=fixture(plasticity=StorePlasticityView(store));before=(memory.iter_entities(),store.count_signals(),store.snapshot(),cognitive.profiles.list())
        request=CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),text="council shared evidence",budget=CognitiveBudget(max_active_entities=1)),specs(ProfileName.CREATIVE,ProfileName.GENERAL,ProfileName.RESEARCH),synthesis_mode=SynthesisMode.DIVERGENCE_FIRST)
        first=CouncilService(cognitive).run(request);second=CouncilService(cognitive).run(request)
        assert stable(first)==stable(second)
        assert first.agreements and first.disagreements and first.minority_insights
        assert all(entry.source_id for entry in first.evidence_map.entries)
        used={memory.get(x.entity_id).content_kind for x in first.evidence_map.entries};assert {"caption","transcript","text"}&used
        assert "truth probability" in first.synthesis.limitations[0]
        assert (memory.iter_entities(),store.count_signals(),store.snapshot(),cognitive.profiles.list())==before

def test_common_gap_and_conflict_preserved_without_truth_winner():
    memory,index,items,cognitive=fixture(3);isolated=Observation(ObservationId.new(),"isolated council gap","text",items[0].provenance,utc_now(),utc_now(),Confidence(.4));memory.put(isolated);index.rebuild()
    request=CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),entity_ids=(isolated.id,)),specs(ProfileName.GENERAL,ProfileName.STRATEGY,ProfileName.RESEARCH))
    result=CouncilService(cognitive).run(request)
    assert any(x.kind is GapKind.COMMON_GAP for x in result.gaps)
    assert result.synthesis.next_information_need and result.status in {CouncilStatus.INSUFFICIENT_EVIDENCE,CouncilStatus.PARTIAL}
    conflict=CouncilService(cognitive).run(CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),entity_ids=(items[0].id,items[1].id)),specs(ProfileName.SYSTEMS,ProfileName.STRATEGY,ProfileName.RESEARCH)))
    assert conflict.status is CouncilStatus.CONFLICTED and conflict.synthesis.unresolved_conflicts
    assert memory.get(items[0].id).extraction_confidence==Confidence(.6)

class FailingCognitive:
    def __init__(self,inner,failed):self.inner=inner;self.failed=failed;self.memory=inner.memory;self.retrieval=inner.retrieval;self.profiles=inner.profiles
    def process(self,request):
        if request.activation_profile==self.failed:raise RuntimeError("synthetic member failure")
        return self.inner.process(request)
class DriftingCognitive:
    def __init__(self,inner):self.inner=inner;self.memory=inner.memory;self.retrieval=inner.retrieval;self.profiles=inner.profiles;self.done=False
    def process(self,request):
        result=self.inner.process(request)
        if not self.done:self.done=True;self.memory.put(Source(SourceId.new(),"synthetic","drift",utc_now()))
        return result

def test_member_failure_unknown_profile_budget_and_state_drift():
    memory,index,items,cognitive=fixture(5);members=specs(ProfileName.GENERAL,ProfileName.SYSTEMS,ProfileName.RESEARCH)
    partial=CouncilService(FailingCognitive(cognitive,members[1].profile_id)).run(CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),text="council"),members))
    assert partial.status is CouncilStatus.PARTIAL and [x.status for x in partial.members].count(MemberStatus.FAILED)==1
    limited=CouncilService(cognitive).run(CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),text="council"),members,CouncilBudget(max_total_recall_rounds=1)))
    assert limited.status is CouncilStatus.LIMIT_REACHED and any(x.status is MemberStatus.NOT_RUN for x in limited.members)
    huge=CouncilBudget(6,999,999,999,999,999,999,999)
    clipped=CouncilService(cognitive).run(CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),text="council"),members,huge))
    assert "global_hard_limits" in clipped.diagnostics.truncated
    bad=(CouncilMemberSpec(__import__("syune.core",fromlist=["ActivationProfileId"]).ActivationProfileId.new()),members[0])
    try:CouncilService(cognitive).run(CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),text="council"),bad))
    except CouncilError as error:assert error.code is CouncilErrorCode.INVALID_MEMBER_PROFILE
    else:raise AssertionError("unknown member accepted")
    profiles=cognitive.profiles.list();general=cognitive.profiles.by_name(ProfileName.GENERAL);incompatible=replace(general,core_version="999")
    incompatible_registry=ProfileRegistry(tuple(incompatible if x.id==general.id else x for x in profiles));incompatible_cognitive=CognitiveService(memory,RetrievalService(memory,index),incompatible_registry)
    try:CouncilService(incompatible_cognitive).run(CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),text="council"),members))
    except CouncilError as error:assert error.code is CouncilErrorCode.MEMBER_PROFILE_INCOMPATIBLE
    else:raise AssertionError("incompatible member accepted")
    try:CouncilService(DriftingCognitive(cognitive)).run(CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),text="council"),members))
    except CouncilError as error:assert error.code is CouncilErrorCode.SHARED_STATE_MISMATCH
    else:raise AssertionError("state drift accepted")
