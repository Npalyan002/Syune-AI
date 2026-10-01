"""Deterministic bounded Cognitive Core orchestration."""
from dataclasses import replace
from datetime import datetime,timezone
from time import perf_counter
from uuid import NAMESPACE_URL,uuid5
from syune.core import ResponseCandidateId
from syune.memory import MemoryRepository
from syune.retrieval import RecallCue,RecallRequest,RetrievalError,RetrievalService
from .errors import CognitiveError,CognitiveErrorCode
from .inference import InferenceEngine
from .metacognition import MetacognitionService
from .model import *
from .profiles import GLOBAL_RETRIEVAL_HARD_LIMITS,ProfileActivation,ProfileDiagnostics,ProfileRegistry,ProfileSelectionSource,effective_budget

class CognitiveService:
    def __init__(self,memory:MemoryRepository,retrieval:RetrievalService,profiles:ProfileRegistry|None=None):
        self.memory=memory;self.retrieval=retrieval;self.inference=InferenceEngine(memory);self.metacognition=MetacognitionService();self.profiles=profiles or ProfileRegistry()
    def process(self,request:CognitiveRequest)->CognitiveResult:
        total=perf_counter(); timings=[]; truncated=[]
        tick=perf_counter();profile=self.profiles.resolve(request.activation_profile);budget,clipped=effective_budget(request.budget,profile)
        retrieval_hops=min(profile.retrieval.max_hops,GLOBAL_RETRIEVAL_HARD_LIMITS.max_hops,budget.max_inference_depth)
        retrieval_fanout=min(profile.retrieval.max_fanout,GLOBAL_RETRIEVAL_HARD_LIMITS.max_fanout)
        retrieval_results=min(profile.retrieval.max_results,GLOBAL_RETRIEVAL_HARD_LIMITS.max_results,budget.max_recall_candidates)
        clipped=(*clipped,*(("retrieval.max_hops",) if retrieval_hops<profile.retrieval.max_hops else ()),*(("retrieval.max_fanout",) if retrieval_fanout<profile.retrieval.max_fanout else ()),*(("retrieval.max_results",) if retrieval_results<profile.retrieval.max_results else ()))
        source=ProfileSelectionSource.EXPLICIT_CALLER if request.activation_profile else ProfileSelectionSource.DEFAULT_GENERAL
        activation=ProfileActivation(profile.id,profile.name,profile.version,source,request.temporal_context or datetime(1970,1,1,tzinfo=timezone.utc),profile.fingerprint,budget,clipped)
        timings.append(("profile_activation",(perf_counter()-tick)*1000))
        tick=perf_counter()
        for entity_id in (*request.entity_ids,*request.context_ids):
            if not self.memory.exists(entity_id):raise CognitiveError(CognitiveErrorCode.MISSING_ENTITY,f"missing explicit entity {entity_id}")
        normalized=" ".join(request.text.split()) if request.text else None
        timings.append(("intake",(perf_counter()-tick)*1000))
        tick=perf_counter()
        try:
            weights=dict(self.retrieval.config.weights);weights["provenance"]=profile.retrieval.provenance_weight;weights["pattern"]=profile.retrieval.pattern_weight
            retrieval_config=replace(self.retrieval.config,max_hops=retrieval_hops,max_fanout=retrieval_fanout,max_results=retrieval_results,weights=tuple(weights.items()))
            retrieval=RetrievalService(self.retrieval.memory,self.retrieval.index,retrieval_config,self.retrieval.materialization_check,self.retrieval.plasticity)
            recalled=retrieval.recall(RecallRequest(RecallCue(normalized,request.entity_ids,request.source_ids,request.context_ids,request.temporal_context,request.correlation_id,access_context=request.access_context),max_results=budget.max_recall_candidates))
        except RetrievalError as exc:raise CognitiveError(CognitiveErrorCode.RETRIEVAL_FAILED,str(exc)) from exc
        rounds=1; candidates=list(recalled.candidates);truncated.extend(f"retrieval:{x}" for x in recalled.truncated)
        if candidates and len(candidates)<2 and budget.max_recall_rounds>1:
            follow=retrieval.recall(RecallRequest(RecallCue(entity_ids=(candidates[0].entity_id,)),max_results=budget.max_recall_candidates))
            known={x.entity_id for x in candidates};candidates.extend(x for x in follow.candidates if x.entity_id not in known);rounds=2
            truncated.extend(f"follow_up:{x}" for x in follow.truncated)
        timings.append(("recall",(perf_counter()-tick)*1000))
        tick=perf_counter(); attention=[]
        first_source=candidates[0].source_id if candidates else None
        for candidate in candidates:
            comp=dict(candidate.components); learned=comp.get("learned_salience",0)+comp.get("learned_utility",0)
            direct=1.0 if candidate.entity_id in request.entity_ids or any(r.startswith("lexical") for r in candidate.seed_reasons) else .5
            diversity=1.0 if candidate.source_id and candidate.source_id!=first_source else 0
            cfg=profile.attention;score=max(0,min(1,cfg.direct_weight*direct+cfg.activation_weight*min(1,candidate.activation)+cfg.learned_weight*max(-1,min(1,learned))+cfg.diversity_bonus*diversity))
            attention.append(AttentionItem(candidate.entity_id,0,score,(('cue_directness',direct),('activation',candidate.activation),('learned_relevance',learned),('profile_diversity',cfg.diversity_bonus*diversity)),
                                           ";".join(candidate.seed_reasons) or "structural activation",candidate.source_id))
        attention.sort(key=lambda x:(-x.score,type(x.entity_id).__name__,str(x.entity_id)))
        attention=tuple(AttentionItem(x.entity_id,n,x.score,x.components,x.reason,x.source_id) for n,x in enumerate(attention[:budget.max_active_entities],1))
        if len(candidates)>len(attention):truncated.append("working_context")
        source_ids=tuple(sorted({x.source_id for x in attention if x.source_id},key=str))
        context=WorkingContext(tuple(x.entity_id for x in attention),source_ids,attention,tuple(truncated),rounds)
        timings.append(("attention_context",(perf_counter()-tick)*1000))
        tick=perf_counter(); inferences,paths=self.inference.infer(request.id,context.entity_ids,budget.max_inference_depth,min(budget.max_inference_paths,budget.max_graph_edges),budget.max_inference_records)
        order={name:n for n,name in enumerate(profile.inference.priorities)};inferences=tuple(sorted(inferences,key=lambda x:(order[x.type.value],str(x.id))))
        if len(inferences)>=budget.max_inference_records:truncated.append("inferences")
        timings.append(("inference",(perf_counter()-tick)*1000))
        tick=perf_counter()
        if (perf_counter()-total)*1000>budget.max_cycle_ms:truncated.append("time_budget")
        confidences=tuple(x.confidence for x in candidates if x.entity_id in context.entity_ids and x.confidence is not None)
        meta=profile.metacognition;assessment=self.metacognition.assess(active_count=len(attention),active_capacity=budget.max_active_entities,
            source_count=len(source_ids),inferences=inferences,confidence_values=confidences,truncated=tuple(truncated),ready_threshold=meta.ready_threshold,single_source_penalty=meta.single_source_penalty,conflict_penalty=meta.conflict_penalty,missing_penalty=meta.missing_penalty)
        status=assessment.status;readiness=assessment.readiness;conflicts=assessment.conflict_count;gaps=assessment.gap_count;uncertainties=assessment.uncertainties
        timings.append(("metacognition",(perf_counter()-tick)*1000))
        tick=perf_counter()
        response_type=ResponseType.REPORT_CONFLICT if status is CognitiveStatus.CONFLICTED else ResponseType.REPORT_INSUFFICIENT_EVIDENCE if status is CognitiveStatus.INSUFFICIENT_EVIDENCE else ResponseType.REQUEST_MORE_CONTEXT if status is CognitiveStatus.PARTIAL else ResponseType.ANSWER_SUMMARY
        content=("Conflicting structural evidence requires review." if status is CognitiveStatus.CONFLICTED else
                 "Available memory is insufficient; request more context." if status is CognitiveStatus.INSUFFICIENT_EVIDENCE else
                 f"Structured memory supports {len(inferences)} bounded inference record(s).")
        rid=ResponseCandidateId(uuid5(NAMESPACE_URL,f"{request.id}:{response_type.value}"))
        response=ResponseCandidate(rid,response_type,content,context.entity_ids,tuple(x.id for x in inferences),source_ids,status,readiness,tuple(x.value for x in uncertainties),"deterministic metacognitive status")
        responses=[response]
        for n in range(1,min(profile.response.max_candidates,budget.max_response_candidates)):
            alt_type=ResponseType.SUGGEST_RECALL_FOCUS
            alt_id=ResponseCandidateId(uuid5(NAMESPACE_URL,f"{request.id}:{profile.id}:{alt_type.value}:{n}"))
            responses.append(ResponseCandidate(alt_id,alt_type,f"{profile.name.value} emphasis: {profile.response.emphasis}.",context.entity_ids,tuple(x.id for x in inferences),source_ids,status,readiness,tuple(x.value for x in uncertainties),profile.response.emphasis))
        responses=tuple(responses)
        timings.append(("response",(perf_counter()-tick)*1000)); elapsed=(perf_counter()-total)*1000
        timings.append(("total",elapsed))
        diagnostics=(("memory_entities_considered",len(candidates)),("paths_explored",paths),("inference_count",len(inferences)),("recall_rounds",rounds))
        stages=(CognitiveStage.CREATED,CognitiveStage.INTAKE_COMPLETE,CognitiveStage.RECALL_COMPLETE,CognitiveStage.ATTENTION_COMPLETE,
                CognitiveStage.CONTEXT_READY,CognitiveStage.INFERENCE_COMPLETE,CognitiveStage.METACOGNITION_COMPLETE,CognitiveStage.RESULT_READY)
        modified=("attention","retrieval","inference","metacognition","response","budget")
        effective_weights=(("attention.direct",profile.attention.direct_weight),("attention.activation",profile.attention.activation_weight),("attention.learned",profile.attention.learned_weight),("attention.diversity",profile.attention.diversity_bonus),("retrieval.max_hops",retrieval_hops),("retrieval.max_fanout",retrieval_fanout),("metacognition.ready_threshold",profile.metacognition.ready_threshold))
        profile_diagnostics=ProfileDiagnostics(activation,modified,effective_weights)
        return CognitiveResult(request.id,status,CognitiveCycle(request.id,stages),context,inferences,assessment,responses,tuple("missing canonical link" for _ in range(gaps)),bool(conflicts),source_ids,tuple(timings),diagnostics,tuple(truncated),profile_diagnostics)

    def compare_profiles(self,request:CognitiveRequest,profile_ids):
        return tuple(self.process(replace(request,activation_profile=profile_id)) for profile_id in profile_ids)
