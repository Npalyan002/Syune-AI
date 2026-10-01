"""Sequential bounded Council orchestration over one CognitiveService."""
from dataclasses import replace
from hashlib import sha256
from time import perf_counter
from uuid import NAMESPACE_URL,uuid5
from syune.core import CouncilRunId
from syune.cognition import CORE_VERSION,ProfileError,ProfileErrorCode
from .analysis import CouncilAnalyzer
from .errors import CouncilError,CouncilErrorCode
from .model import *
from .synthesis import CouncilSynthesizer

def _hash(parts):return sha256("|".join(parts).encode()).hexdigest()
class CouncilService:
    def __init__(self,cognitive):self.cognitive=cognitive;self.analyzer=CouncilAnalyzer();self.synthesizer=CouncilSynthesizer()
    def snapshot(self):
        memory=self.cognitive.memory;entities=memory.iter_entities();associations={}
        for entity in entities:
            for edge in memory.associations_for(entity.id):associations[str(edge.id)]=edge
        memory_fp=_hash([repr(x) for x in entities]+[repr(associations[x]) for x in sorted(associations)])
        index=self.cognitive.retrieval.index;entries=getattr(index,"entries",{});retrieval_fp=_hash([getattr(index,"version","unknown")]+[repr(entries[x]) for x in sorted(entries,key=str)])
        plasticity=self.cognitive.retrieval.plasticity;store=getattr(plasticity,"store",None);states=store.snapshot() if store is not None else ();learning_fp=_hash([type(plasticity).__name__]+[repr(x) for x in states])
        profiles=self.cognitive.profiles.list();profiles_fp=_hash([x.fingerprint for x in profiles])
        return CouncilCognitiveSnapshot(memory_fp,retrieval_fp,learning_fp,profiles_fp,CORE_VERSION)
    def run(self,request:CouncilRequest):
        if not isinstance(request,CouncilRequest):raise CouncilError(CouncilErrorCode.INVALID_COUNCIL_REQUEST,"CouncilRequest required")
        hard=GLOBAL_COUNCIL_HARD_LIMITS
        budget=CouncilBudget(*(min(getattr(request.budget,name),getattr(hard,name)) for name in CouncilBudget.__dataclass_fields__))
        total=perf_counter();baseline=self.snapshot();resolved=[]
        for spec in request.members:
            try:resolved.append(self.cognitive.profiles.resolve(spec.profile_id))
            except ProfileError as exc:
                code=CouncilErrorCode.MEMBER_PROFILE_INCOMPATIBLE if exc.code is ProfileErrorCode.PROFILE_INCOMPATIBLE else CouncilErrorCode.INVALID_MEMBER_PROFILE
                raise CouncilError(code,str(exc)) from exc
        member_start=perf_counter();members=[];recalls=candidates=inferences=0;truncated=[]
        for index,profile in enumerate(resolved):
            elapsed=(perf_counter()-total)*1000
            if elapsed>budget.max_wall_time or recalls>=budget.max_total_recall_rounds or candidates>=budget.max_total_retrieval_candidates or inferences>=budget.max_total_inference_records:
                truncated.append("council_budget")
                for pending in resolved[index:]:members.append(CouncilMemberResult(pending.id,pending.version,pending.fingerprint,MemberStatus.NOT_RUN,None,(),(),(),(),CouncilErrorCode.COUNCIL_BUDGET_EXCEEDED.value,"Council aggregate budget exhausted"))
                break
            cycle_budget=replace(request.cognitive_request.budget,max_cycle_ms=min(request.cognitive_request.budget.max_cycle_ms,budget.max_per_member_cycle_ms))
            member_request=replace(request.cognitive_request,activation_profile=profile.id,budget=cycle_budget)
            tick=perf_counter()
            try:
                result=self.cognitive.process(member_request);times=(('member_total',(perf_counter()-tick)*1000),)
                members.append(CouncilMemberResult(profile.id,profile.version,profile.fingerprint,MemberStatus.COMPLETE,result,result.context.entity_ids,result.provenance_source_ids,tuple(x.id for x in result.inferences),times))
                diag=dict(result.diagnostics);recalls+=int(diag.get("recall_rounds",0));candidates+=int(diag.get("memory_entities_considered",0));inferences+=len(result.inferences)
            except Exception as exc:
                members.append(CouncilMemberResult(profile.id,profile.version,profile.fingerprint,MemberStatus.FAILED,None,(),(),(),(('member_total',(perf_counter()-tick)*1000),),CouncilErrorCode.MEMBER_EXECUTION_FAILED.value,type(exc).__name__))
            if self.snapshot()!=baseline:raise CouncilError(CouncilErrorCode.SHARED_STATE_MISMATCH,"shared Memory/Retrieval/Learning/Profile state changed during Council run")
        member_ms=(perf_counter()-member_start)*1000;analysis_start=perf_counter()
        try:evidence,agreements,disagreements,gaps,minority=self.analyzer.analyze(request.id,tuple(members),budget.max_evidence_map_entries)
        except Exception as exc:raise CouncilError(CouncilErrorCode.ANALYSIS_FAILED,str(exc)) from exc
        analysis_ms=(perf_counter()-analysis_start)*1000;synthesis_start=perf_counter()
        synthesis=self.synthesizer.synthesize(request.id,request.synthesis_mode,tuple(members),evidence,agreements,disagreements,gaps,minority,budget.max_synthesis_records)
        synthesis_ms=(perf_counter()-synthesis_start)*1000
        run_id=CouncilRunId(uuid5(NAMESPACE_URL,f"syune:council:{request.id}:{'|'.join(str(x.profile_id) for x in request.members)}"));stages=(CouncilStage.CREATED,CouncilStage.MEMBERS_RESOLVED,CouncilStage.MEMBERS_RUNNING,CouncilStage.MEMBERS_COMPLETE,CouncilStage.ANALYSIS_COMPLETE,CouncilStage.SYNTHESIS_COMPLETE,CouncilStage.RESULT_READY);run=CouncilRun(run_id,request.id,stages,baseline,tuple(x.profile_id for x in request.members))
        failed=sum(x.status is not MemberStatus.COMPLETE for x in members);status=CouncilStatus.LIMIT_REACHED if any(x.status is MemberStatus.NOT_RUN for x in members) else CouncilStatus.PARTIAL if failed else synthesis.status
        if budget!=request.budget:truncated.append("global_hard_limits")
        diagnostics=CouncilDiagnostics(member_ms,analysis_ms,synthesis_ms,(perf_counter()-total)*1000,len(evidence.entries),len(agreements),len(disagreements),len(members)-failed,failed,tuple(truncated))
        return CouncilResult(request.id,status,run,tuple(members),evidence,agreements,disagreements,gaps,minority,replace(synthesis,status=status),diagnostics)
