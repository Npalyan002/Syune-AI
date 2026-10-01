"""Rule based bounded L2 plan construction; produces data and performs no action."""
from hashlib import sha256
from uuid import NAMESPACE_URL,uuid5
from syune.core import *
from .model import *
def _id(cls,text):return cls(uuid5(NAMESPACE_URL,text))
def _budget(action=ActionType.ANALYZE):
    side=action in (ActionType.SEND,ActionType.DELETE,ActionType.EXTERNAL_REQUEST,ActionType.EXECUTE_TOOL,ActionType.CALL_AGENT)
    return BudgetEstimate(10 if not side else None,1,None,None,None,1 if side else 0,1 if action is ActionType.EXECUTE_TOOL else 0,1 if action is ActionType.CALL_AGENT else 0,1 if side else 0,None,BudgetUncertainty.UNKNOWN if side else BudgetUncertainty.ESTIMATED,"static planning estimate; no resource is spent")
class PlannerEngine:
    version=PLANNER_VERSION
    def action_for(self,text):
        t=text.casefold()
        if "delete" in t:return ActionType.DELETE,SideEffectClass.EXTERNAL_IRREVERSIBLE,False
        if any(x in t for x in ("send","publish","message","submit")):return ActionType.SEND,SideEffectClass.EXTERNAL_IRREVERSIBLE,False
        if "call agent" in t:return ActionType.CALL_AGENT,SideEffectClass.UNKNOWN,None
        if "execute" in t or "tool" in t:return ActionType.EXECUTE_TOOL,SideEffectClass.UNKNOWN,None
        if any(x in t for x in ("migration","update","change","create")):return ActionType.UPDATE,SideEffectClass.LOCAL_REVERSIBLE,True
        return ActionType.ANALYZE,SideEffectClass.NONE,True
    def draft(self,goal,context,constraints,limits,resource_budget=None,version=1,prior_version=None,revision_reason=None):
        criteria=goal.success_criteria or (f"review confirms goal: {goal.statement}",)
        assumptions=()
        if not goal.success_criteria:
            assumptions=(PlanningAssumption(_id(PlanningAssumptionId,f"{goal.id}:criteria"),"reviewer confirms the derived success criterion","success criteria absent",.4,"plan may not match intended outcome","human validation required",context.entity_ids,context.source_ids),)
        if context.conflicts:
            assumptions+= (PlanningAssumption(_id(PlanningAssumptionId,f"{goal.id}:conflict"),"Council disagreement remains unresolved","CouncilResult disagreement",.2,"action selection may be unsafe","human decision required",context.minority_entity_ids,context.source_ids),)
        plan_id=_id(PlanId,f"executive:plan:{goal.id}");action,side,reversible=self.action_for(goal.statement)
        step_ids=tuple(_id(PlanStepId,f"{plan_id}:{version}:{n}") for n in range(3));proposal_ids=tuple(_id(ActionProposalId,f"{step_ids[n]}:proposal") for n in range(3))
        read_approval=ApprovalRequirement(ApprovalKind.NONE,"read-only analysis",False)
        side_approval=ApprovalRequirement(ApprovalKind.HUMAN,"side-effecting proposal requires a human or host",side is not SideEffectClass.NONE,"human/host")
        cap=None if action in (ActionType.ANALYZE,ActionType.READ,ActionType.HUMAN_DECISION) else CapabilityDescriptor(_id(CapabilityId,f"capability:{action.value}"),action,f"future {action.value} capability",side,None,Availability.UNKNOWN,side_approval.kind,"static planner descriptor")
        pre0=(Precondition(PreconditionKind.INFORMATION_AVAILABLE,"structured context available",bool(context.entity_ids or context.source_ids or not context.unresolved_gaps)),)
        p0=ActionProposal(proposal_ids[0],step_ids[0],ActionType.ANALYZE,"goal and supplied structured context",(),pre0,"bounded prerequisite analysis",True,"read-only",RiskLevel.LOW,_budget(),read_approval,None,"repeatable read-only analysis",SideEffectClass.NONE,"review inputs without retrieving or mutating",context.entity_ids,context.source_ids)
        risk_level=RiskLevel.HIGH if side in (SideEffectClass.EXTERNAL_IRREVERSIBLE,SideEffectClass.LOCAL_IRREVERSIBLE) else RiskLevel.UNKNOWN if side is SideEffectClass.UNKNOWN else RiskLevel.MEDIUM if side is not SideEffectClass.NONE else RiskLevel.LOW
        pre1=(Precondition(PreconditionKind.PRIOR_STEP_VALIDATED,"prerequisite analysis reviewed",False),Precondition(PreconditionKind.CAPABILITY_AVAILABLE,"future capability availability confirmed",None if cap else True))
        p1=ActionProposal(proposal_ids[1],step_ids[1],action,"goal target described by caller",(("goal",goal.statement),),pre1,"proposed goal progress only",reversible,"rollback must be supplied by future executor" if reversible is not True else "revert through future supervised mechanism",risk_level,_budget(action),side_approval,cap,"future executor must provide idempotency key",side,"pure data proposal; no invocation occurs",context.entity_ids,context.source_ids)
        human_needed=side is not SideEffectClass.NONE or bool(context.conflicts or context.unresolved_gaps)
        human_approval=ApprovalRequirement(ApprovalKind.HUMAN,"review uncertainty, risk, and proposal scope",human_needed,"human")
        p2=ActionProposal(proposal_ids[2],step_ids[2],ActionType.HUMAN_DECISION,"human/host review",(),(Precondition(PreconditionKind.PRIOR_STEP_VALIDATED,"draft validated",False),),"accept, reject, or request revision",True,"decision changes no external system",RiskLevel.LOW,_budget(),human_approval,None,"one version-bound decision",SideEffectClass.NONE,"human remains final authority",context.entity_ids,context.source_ids)
        blocked=any(c.satisfied is False and c.kind in (ConstraintKind.HARD,ConstraintKind.SAFETY,ConstraintKind.DEPENDENCY,ConstraintKind.CAPABILITY) for c in constraints) or bool(context.unresolved_gaps)
        steps=(
            PlanStep(step_ids[0],"Assess prerequisites","Inspect supplied goal, constraints, gaps, and provenance",(),pre0,"reviewable prerequisite record",("all gaps and conflicts visible",),(p0,),(),_budget(),(),StepStatus.BLOCKED if blocked else StepStatus.READY_FOR_REVIEW,criteria),
            PlanStep(step_ids[1],"Prepare action proposal","Describe a future action without invoking it",(step_ids[0],),pre1,"pure data ActionProposal",("proposal is version-bound and non-executable",),(p1,),(),_budget(action),(side_approval,),StepStatus.BLOCKED if blocked else StepStatus.REQUIRES_APPROVAL if side_approval.mandatory else StepStatus.READY_FOR_REVIEW,criteria),
            PlanStep(step_ids[2],"Review plan","Human or host reviews the complete plan",(step_ids[1],),(p2.preconditions),"recorded future decision",("reviewer explicitly decides",),(p2,),(),_budget(),(human_approval,),StepStatus.BLOCKED if blocked else StepStatus.REQUIRES_APPROVAL if human_needed else StepStatus.READY_FOR_REVIEW,criteria),)
        deps=(PlanDependency(step_ids[0],step_ids[1],True,"prerequisites precede proposal"),PlanDependency(step_ids[1],step_ids[2],True,"proposal precedes review"))
        checks=tuple(PlanCheckpoint(_id(PlanCheckpointId,f"{s.id}:checkpoint"),s.id,"verify "+s.objective.casefold(),True,s.verification_criteria) for s in steps)
        risks=[]
        for proposal in (p0,p1,p2):
            drivers=[]
            if proposal.side_effect_class in (SideEffectClass.EXTERNAL_IRREVERSIBLE,SideEffectClass.LOCAL_IRREVERSIBLE):drivers.append("irreversible")
            if proposal.side_effect_class.value.startswith("EXTERNAL"):drivers.append("external_side_effect")
            if proposal.capability_requirement and proposal.capability_requirement.availability is Availability.UNKNOWN:drivers.append("unknown_capability")
            if context.unresolved_gaps:drivers.append("insufficient_evidence")
            if context.conflicts:drivers.append("minority_or_council_disagreement")
            if any(x in goal.statement.casefold() for x in ("credential","secret","personal data","private file","upload")):drivers.append("sensitive_target")
            if proposal.estimated_cost.money is None and proposal.side_effect_class is not SideEffectClass.NONE:drivers.append("cost_unknown")
            risks.append(RiskAssessment(_id(RiskAssessmentId,f"{proposal.id}:risk"),proposal.estimated_risk,tuple(drivers),"; ".join(drivers) or "bounded read-only planning risk",(proposal.id,),("human review",) if drivers else ()))
        steps=tuple(PlanStep(s.id,s.objective,s.description,s.dependencies,s.preconditions,s.expected_output,s.verification_criteria,s.action_proposals,(risks[i].id,),s.budget_estimate,s.approval_requirements,s.status,s.criterion_refs) for i,s in enumerate(steps))
        config=sha256(repr((limits,self.version)).encode()).hexdigest();approvals=tuple(dict.fromkeys(x for s in steps for x in s.approval_requirements))
        if any(x.kind is ConstraintKind.APPROVAL for x in constraints):approvals+= (ApprovalRequirement(ApprovalKind.HUMAN,"explicit approval constraint",True,"human/host"),)
        status=PlanStatus.BLOCKED if blocked else PlanStatus.REQUIRES_APPROVAL if any(x.mandatory for x in approvals) else PlanStatus.READY_FOR_REVIEW
        return Plan(plan_id,goal.id,version,status,steps,deps,checks,assumptions,constraints,tuple(risks),_budget(action),resource_budget,context.unresolved_gaps,approvals,context.entity_ids,context.source_ids,context.inference_ids,self.version,config,prior_version,revision_reason)
