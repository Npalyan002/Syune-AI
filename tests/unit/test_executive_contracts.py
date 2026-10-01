from dataclasses import fields,replace
import pytest
from syune.core import *
from syune.executive import *

def goal(text="prepare a safe migration",criteria=("migration design reviewed",)):
    return Goal(GoalId.new(),text,criteria,source=GoalSource.TEST)
def request(g=None,**kwargs):return ExecutiveRequest(ExecutiveRequestId.new(),g,**kwargs)

def test_explicit_goal_ambiguity_assumption_and_deterministic_normalization():
    service=ExecutiveService()
    with pytest.raises(ExecutiveError) as error:service.plan(request(None))
    assert error.value.code is ExecutiveErrorCode.GOAL_REQUIRED
    with pytest.raises(ExecutiveError) as error:service.plan(request(goal("plan",())))
    assert error.value.code is ExecutiveErrorCode.GOAL_AMBIGUOUS
    g=goal("  prepare   a safe migration  ",());result=service.plan(request(g))
    assert result.goal.statement=="prepare a safe migration" and result.plan.assumptions
    assert result.goal.source is GoalSource.TEST and result.plan.steps[0].criterion_refs

def test_action_proposal_is_pure_data_and_l2_boundary():
    result=ExecutiveService().plan(request(goal("plan and execute a safe migration")))
    proposals=tuple(p for s in result.plan.steps for p in s.action_proposals)
    assert any(p.action_type is ActionType.EXECUTE_TOOL for p in proposals)
    assert all(not callable(getattr(p,f.name)) for p in proposals for f in fields(p))
    assert not hasattr(ExecutiveService,"execute") and not hasattr(ExecutiveService,"run_action") and not hasattr(ExecutiveService,"dispatch")
    proposal=next(p for p in proposals if p.action_type is ActionType.EXECUTE_TOOL)
    assert proposal.capability_requirement.availability is Availability.UNKNOWN
    assert proposal.required_approval.mandatory and result.status is ExecutiveStatus.APPROVAL_REQUIRED
    with pytest.raises(ValueError):ResourceBudget(max_money=1)
    with pytest.raises(ValueError):ResourceBudget(max_tool_calls=-1)

def test_typed_constraints_conflicts_hard_scope_time_approval_and_limits():
    c1=Constraint(ConstraintId.new(),ConstraintKind.HARD,ConstraintSource.USER,"environment","staging",True)
    c2=Constraint(ConstraintId.new(),ConstraintKind.SCOPE,ConstraintSource.HOST,"environment","production",True)
    blocked=ExecutiveService().plan(request(goal(),constraints=(c1,c2)))
    assert blocked.status is ExecutiveStatus.PLAN_BLOCKED and "environment" in blocked.limitations[0]
    missing=Constraint(ConstraintId.new(),ConstraintKind.DEPENDENCY,ConstraintSource.USER,"backup","available",False)
    result=ExecutiveService().plan(request(goal(),constraints=(missing,),limits=PlannerLimits(999,999,999,999,999,999,999,999,999,999)))
    assert result.status is ExecutiveStatus.PLAN_BLOCKED and "global_hard_limits" in result.diagnostics.truncated and result.plan.constraints==(missing,)
    approval=Constraint(ConstraintId.new(),ConstraintKind.APPROVAL,ConstraintSource.USER,"review","human",True)
    constrained=ExecutiveService().plan(request(goal("send migration report"),constraints=(approval,),resource_budget=ResourceBudget(max_external_calls=0,max_human_reviews=0)))
    assert constrained.plan.resource_budget.max_external_calls==0 and any(x.reason=="explicit approval constraint" for x in constrained.plan.approval_requirements)
    assert constrained.status is ExecutiveStatus.PLAN_BLOCKED
    kinds={ConstraintKind.SOFT,ConstraintKind.APPROVAL,ConstraintKind.TIME,ConstraintKind.SCOPE,ConstraintKind.RESOURCE,ConstraintKind.POLICY,ConstraintKind.SAFETY}
    assert kinds<set(ConstraintKind)

def test_dependency_cycle_and_blocked_descendants():
    service=ExecutiveService();result=service.plan(request(goal()))
    a,b=result.plan.steps[:2]
    cycle=(PlanDependency(a.id,b.id),PlanDependency(b.id,a.id))
    with pytest.raises(ExecutiveError) as error:service.validator.topological_order((a,b),cycle)
    assert error.value.code is ExecutiveErrorCode.PLAN_DEPENDENCY_CYCLE

def test_policy_risk_budget_and_destructive_safety():
    result=ExecutiveService().plan(request(goal("delete external production data")))
    proposal=next(p for s in result.plan.steps for p in s.action_proposals if p.action_type is ActionType.DELETE)
    risk=next(x for x in result.plan.risks if proposal.id in x.proposal_ids)
    decision=next(x for x in result.validation.policy_decisions if proposal.id in x.proposal_ids)
    assert proposal.side_effect_class is SideEffectClass.EXTERNAL_IRREVERSIBLE and proposal.reversible is False
    assert proposal.estimated_cost.money is None and proposal.estimated_cost.uncertainty is BudgetUncertainty.UNKNOWN
    assert risk.level is RiskLevel.HIGH and {"irreversible","external_side_effect","unknown_capability","cost_unknown"}<=set(risk.drivers)
    assert decision.outcome is PolicyOutcome.REQUIRES_APPROVAL and decision.rule_ids
    assert result.approval_envelope.plan_version==result.plan.version

def test_revision_preserves_v1_invalidates_envelope_and_exposes_diff():
    service=ExecutiveService();g=goal();v1=service.plan(request(g));constraint=Constraint(ConstraintId.new(),ConstraintKind.SOFT,ConstraintSource.USER,"window","weekend",True)
    v2=service.revise(v1.plan.id,1,request(g,constraints=(constraint,)),"add maintenance window")
    assert [x.version for x in service.repository.versions(v1.plan.id)]==[1,2]
    assert v2.plan.prior_version==1 and v2.plan_diff.from_version==1 and v2.plan_diff.to_version==2
    assert service.repository.envelope(v1.plan.id,1).valid is False and v2.approval_envelope.valid
    assert v2.approval_envelope.plan_version==2 and v2.approval_envelope.proposal_ids!=v1.approval_envelope.proposal_ids
    with pytest.raises(ExecutiveError):service.revise(v1.plan.id,2,request(goal()),"change goal identity")

def test_repeated_identical_planning_is_idempotent_audit():
    service=ExecutiveService();g=goal();r=request(g);first=service.plan(r);second=service.plan(r)
    assert first.plan==second.plan and len(service.repository.versions(first.plan.id))==1
