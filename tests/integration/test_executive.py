from syune.core import *
from syune.cognition import CognitiveBudget,CognitiveRequest,CognitiveService,ProfileName,ProfileRegistry
from syune.council import CouncilMemberSpec,CouncilRequest,CouncilService
from syune.executive import *
from syune.learning import SQLiteLearningStore,StorePlasticityView
from syune.memory import InMemoryReferenceRepository,Observation,Provenance,Source
from syune.retrieval import InvertedSeedIndex,RetrievalService

def setup(tmp_path):
    memory=InMemoryReferenceRepository();now=utc_now();source=Source(SourceId.new(),"synthetic","executive",now);provenance=Provenance(ProvenanceId.new(),source.id,now);items=[]
    for text in ("migration needs backup","migration may conflict","migration review"):
        item=Observation(ObservationId.new(),text,"text",provenance,now,now,Confidence(.6));memory.put(item);items.append(item)
    index=InvertedSeedIndex(memory);index.rebuild();store=SQLiteLearningStore(tmp_path/"learning.sqlite3");cognitive=CognitiveService(memory,RetrievalService(memory,index,plasticity=StorePlasticityView(store)));return memory,index,store,cognitive,items
def goal():return Goal(GoalId.new(),"prepare a safe migration",("migration design reviewed",),source=GoalSource.TEST)

def test_cognition_council_uncertainty_provenance_and_neutrality(tmp_path):
    memory,index,store,cognitive,items=setup(tmp_path);before=(memory.iter_entities(),tuple(index.entries.items()),store.snapshot(),store.count_signals(),cognitive.profiles.list())
    cognition=cognitive.process(CognitiveRequest(CognitiveRequestId.new(),entity_ids=(items[0].id,items[2].id)))
    registry=ProfileRegistry();members=tuple(CouncilMemberSpec(registry.by_name(x).id) for x in (ProfileName.GENERAL,ProfileName.RESEARCH,ProfileName.STRATEGY));council=CouncilService(cognitive).run(CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),text="migration",budget=CognitiveBudget(max_active_entities=1)),members))
    request=ExecutiveRequest(ExecutiveRequestId.new(),goal(),cognition,council);service=ExecutiveService();first=service.plan(request)
    assert first.context.entity_ids and first.context.source_ids and first.context.inference_ids
    assert first.context.agreement_ids and first.context.disagreement_ids
    assert first.context.minority_entity_ids==tuple(sorted((x.entity_id for x in council.minority_insights),key=lambda x:(type(x).__name__,str(x))))
    assert first.plan.entity_ids==first.context.entity_ids and first.plan.source_ids==first.context.source_ids
    assert set(x.explanation for x in council.disagreements)<=set(first.context.conflicts)
    assert (memory.iter_entities(),tuple(index.entries.items()),store.snapshot(),store.count_signals(),cognitive.profiles.list())==before
    store.close()

def test_determinism_blocked_gap_and_zero_execution(tmp_path):
    memory,index,store,cognitive,items=setup(tmp_path);isolated=cognitive.process(CognitiveRequest(CognitiveRequestId.new(),entity_ids=(items[0].id,)))
    g=goal();a=ExecutiveService().plan(ExecutiveRequest(ExecutiveRequestId.new(),g,isolated));b=ExecutiveService().plan(ExecutiveRequest(a.request_id,g,isolated))
    semantic=lambda x:(x.status,x.goal,x.context,x.plan,x.validation,x.approval_envelope,x.limitations)
    assert semantic(a)==semantic(b) and a.status is ExecutiveStatus.PLAN_BLOCKED
    assert a.plan.unresolved_gaps and any("no action pathway" in x for x in a.limitations)
    store.close()
