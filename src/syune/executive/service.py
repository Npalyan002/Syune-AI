"""Executive L2 planning orchestration. The public surface contains planning only."""
from dataclasses import replace
from hashlib import sha256
from time import perf_counter
from uuid import NAMESPACE_URL,uuid5
from syune.core import ApprovalEnvelopeId
from .errors import ExecutiveError,ExecutiveErrorCode
from .model import *
from .planner import PlannerEngine
from .policy import PolicyEvaluator
from .validation import PlanValidator,constraint_conflicts

class InMemoryPlanRepository:
    def __init__(self):self._plans={};self._envelopes={}
    def save(self,plan,validation,envelope):
        key=(plan.id,plan.version)
        if key in self._plans:
            if self._plans[key]==(plan,validation) and self._envelopes[key]==envelope:return
            raise ExecutiveError(ExecutiveErrorCode.PLAN_REVISION_CONFLICT,"plan version already exists with different content")
        self._plans[key]=(plan,validation);self._envelopes[key]=envelope
    def versions(self,plan_id):return tuple(self._plans[x][0] for x in sorted(self._plans,key=lambda k:k[1]) if x[0]==plan_id)
    def get(self,plan_id,version):return self._plans[(plan_id,version)][0]
    def envelope(self,plan_id,version):return self._envelopes[(plan_id,version)]
    def invalidate_envelope(self,plan_id,version):
        key=(plan_id,version);self._envelopes[key]=replace(self._envelopes[key],valid=False)

class ExecutiveService:
    def __init__(self,repository=None):self.repository=repository or InMemoryPlanRepository();self.planner=PlannerEngine();self.validator=PlanValidator();self.policy=PolicyEvaluator()
    def _limits(self,requested):
        hard=GLOBAL_PLANNER_LIMITS
        return PlannerLimits(*(min(getattr(requested,n),getattr(hard,n)) for n in PlannerLimits.__dataclass_fields__))
    def _context(self,request):
        cognitive=request.cognitive_result;council=request.council_result
        entities=[];sources=[];inferences=[];gaps=[];uncertainties=[];conflicts=[];agreements=[];disagreements=[];minority=[];parts=[]
        if cognitive:
            entities.extend(cognitive.context.entity_ids);sources.extend(cognitive.provenance_source_ids);inferences.extend(x.id for x in cognitive.inferences);gaps.extend(cognitive.unresolved_gaps);uncertainties.extend(x.value for x in cognitive.assessment.uncertainties)
            if cognitive.conflict:conflicts.append("cognitive structural conflict")
            parts.append(repr((cognitive.request_id,cognitive.status,cognitive.context.entity_ids,cognitive.inferences)))
        if council:
            entities.extend(council.evidence_map.union_entity_ids);sources.extend(x[0] for x in council.evidence_map.source_counts);agreements.extend(x.id for x in council.agreements);disagreements.extend(x.id for x in council.disagreements);minority.extend(x.entity_id for x in council.minority_insights);gaps.extend(x.description for x in council.gaps)
            conflicts.extend(x.explanation for x in council.disagreements);parts.append(repr((council.request_id,council.run.snapshot,council.synthesis)))
        unique=lambda xs:tuple(sorted(set(xs),key=lambda x:(type(x).__name__,str(x))))
        fp=sha256("|".join(parts or ["explicit-goal-only"]).encode()).hexdigest()
        return ExecutiveContext(cognitive.request_id if cognitive else None,council.request_id if council else None,unique(entities),unique(sources),unique(inferences),tuple(sorted(set(gaps))),tuple(sorted(set(uncertainties))),tuple(sorted(set(conflicts))),unique(agreements),unique(disagreements),unique(minority),fp,("Council convergence is not authority","planning context is bounded and read-only"))
    def _envelope(self,plan):
        proposals=tuple(p for s in plan.steps for p in s.action_proposals);proposal_ids=tuple(p.id for p in proposals);risk_ids=tuple(x.id for x in plan.risks);effects=tuple(sorted(set((p.side_effect_class for p in proposals)),key=lambda x:x.value));reviewers=tuple(sorted(set((x.kind for x in plan.approval_requirements if x.mandatory)),key=lambda x:x.value));material=f"{plan.id}:{plan.version}:{'|'.join(map(str,proposal_ids))}"
        return ApprovalEnvelope(ApprovalEnvelopeId(uuid5(NAMESPACE_URL,material)),plan.id,plan.version,proposal_ids,risk_ids,effects,plan.budget_estimate,plan.unresolved_gaps,reviewers,"review of this exact immutable plan version and proposal set",True)
    def _diff(self,old,new):
        a={x.id:x for x in old.steps};b={x.id:x for x in new.steps};common=set(a)&set(b)
        return PlanDiff(old.version,new.version,tuple(sorted(set(b)-set(a),key=str)),tuple(sorted(set(a)-set(b),key=str)),tuple(sorted((x for x in common if a[x]!=b[x]),key=str)),old.dependencies!=new.dependencies,old.risks!=new.risks,old.approval_requirements!=new.approval_requirements,old.budget_estimate!=new.budget_estimate,old.assumptions!=new.assumptions)
    def plan(self,request:ExecutiveRequest,*,_version=1,_prior=None,_reason=None):
        start=perf_counter();timings=[]
        if not isinstance(request,ExecutiveRequest):raise ExecutiveError(ExecutiveErrorCode.INVALID_EXECUTIVE_REQUEST,"ExecutiveRequest required")
        if request.goal is None:raise ExecutiveError(ExecutiveErrorCode.GOAL_REQUIRED,"explicit goal required")
        goal=request.goal
        if goal.ambiguity_flags or len(goal.statement.split())<2:raise ExecutiveError(ExecutiveErrorCode.GOAL_AMBIGUOUS,"goal is ambiguous: "+",".join(goal.ambiguity_flags or ("statement_too_short",)))
        tick=perf_counter();normalized=replace(goal,statement=" ".join(goal.statement.split()),status=GoalStatus.VALID);timings.append(("goal_normalization",(perf_counter()-tick)*1000))
        tick=perf_counter();context=self._context(request);timings.append(("context_assembly",(perf_counter()-tick)*1000))
        conflicts=constraint_conflicts(request.constraints)
        if conflicts:
            diag=ExecutiveDiagnostics(tuple(timings),(('constraints',len(request.constraints)),),(),0)
            return ExecutiveResult(request.id,ExecutiveStatus.PLAN_BLOCKED,replace(normalized,status=GoalStatus.BLOCKED),context,None,None,None,None,diag,conflicts)
        limits=self._limits(request.limits);truncated=("global_hard_limits",) if limits!=request.limits else ()
        tick=perf_counter();draft=self.planner.draft(normalized,context,request.constraints,limits,request.resource_budget,_version,_prior,_reason);timings.append(("draft_generation",(perf_counter()-tick)*1000))
        proposals=tuple(p for s in draft.steps for p in s.action_proposals);hard_violation=any(c.satisfied is False and c.kind in (ConstraintKind.HARD,ConstraintKind.SAFETY,ConstraintKind.POLICY) for c in request.constraints)
        if request.resource_budget:
            estimate=draft.budget_estimate;cap=request.resource_budget
            budget_exceeded=any(limit is not None and used>limit for used,limit in ((estimate.external_calls,cap.max_external_calls),(estimate.tool_calls,cap.max_tool_calls),(estimate.agent_calls,cap.max_agent_calls),(estimate.human_reviews,cap.max_human_reviews)))
            hard_violation=hard_violation or budget_exceeded
        disallowed=tuple(set(request.prohibited_action_categories)|({p.action_type for p in proposals if request.allowed_action_categories and p.action_type not in request.allowed_action_categories and p.action_type is not ActionType.HUMAN_DECISION}))
        tick=perf_counter();decisions=self.policy.evaluate(proposals,disallowed,hard_violation,bool(context.unresolved_gaps));timings.append(("policy_evaluation",(perf_counter()-tick)*1000))
        tick=perf_counter();validation=self.validator.validate(normalized,draft.steps,draft.dependencies,request.constraints,decisions,limits);timings.append(("dependency_validation",(perf_counter()-tick)*1000))
        blocked=not validation.valid or draft.status is PlanStatus.BLOCKED;approval=any(x.outcome is PolicyOutcome.REQUIRES_APPROVAL for x in decisions)
        status=ExecutiveStatus.PLAN_BLOCKED if blocked else ExecutiveStatus.APPROVAL_REQUIRED if approval else ExecutiveStatus.PLAN_READY_FOR_REVIEW
        plan_status=PlanStatus.BLOCKED if blocked else PlanStatus.REQUIRES_APPROVAL if approval else PlanStatus.READY_FOR_REVIEW;draft=replace(draft,status=plan_status)
        tick=perf_counter();envelope=self._envelope(draft);timings.append(("approval_envelope",(perf_counter()-tick)*1000))
        elapsed=(perf_counter()-start)*1000
        if elapsed>limits.max_wall_time_ms:truncated+=("max_planning_wall_time",)
        counts=(('steps',len(draft.steps)),('dependencies',len(draft.dependencies)),('proposals',len(proposals)),('constraints',len(request.constraints)),('risks',len(draft.risks)),('assumptions',len(draft.assumptions)))
        diagnostics=ExecutiveDiagnostics(tuple(timings)+(("total",elapsed),),counts,truncated,1);self.repository.save(draft,validation,envelope)
        return ExecutiveResult(request.id,status,replace(normalized,status=GoalStatus.BLOCKED if blocked else GoalStatus.PLANNED),context,draft,validation,envelope,None,diagnostics,("L2 planning only","approval does not execute or authorize execution","no action pathway exists"))
    def revise(self,plan_id,expected_version,request,reason):
        old=self.repository.get(plan_id,expected_version);versions=self.repository.versions(plan_id)
        if not versions or versions[-1].version!=expected_version:raise ExecutiveError(ExecutiveErrorCode.PLAN_REVISION_CONFLICT,"revision must target latest plan version")
        if request.goal is None or request.goal.id!=old.goal_id:raise ExecutiveError(ExecutiveErrorCode.PLAN_REVISION_CONFLICT,"revision must preserve goal identity")
        if expected_version>=GLOBAL_PLANNER_LIMITS.max_revisions:raise ExecutiveError(ExecutiveErrorCode.PLAN_LIMIT_EXCEEDED,"revision limit reached")
        result=self.plan(request,_version=expected_version+1,_prior=expected_version,_reason=reason)
        if result.plan.id!=plan_id:raise ExecutiveError(ExecutiveErrorCode.PLAN_REVISION_CONFLICT,"goal changed plan identity")
        self.repository.invalidate_envelope(plan_id,expected_version);return replace(result,plan_diff=self._diff(old,result.plan))
