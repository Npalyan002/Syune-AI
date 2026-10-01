"""Immutable L2 planning contracts. Plans and proposals have no execution authority."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from syune.core import *
from syune.memory.model import NodeId
from syune.cognition import CognitiveResult
from syune.council import CouncilResult

PLANNER_VERSION="1"
class GoalSource(str,Enum): HUMAN="HUMAN";HOST="HOST";TEST="TEST";FUTURE_EXECUTIVE="FUTURE_EXECUTIVE"
class GoalStatus(str,Enum): DRAFT="DRAFT";VALID="VALID";AMBIGUOUS="AMBIGUOUS";BLOCKED="BLOCKED";PLANNED="PLANNED"
class TimeHorizon(str,Enum): IMMEDIATE="IMMEDIATE";SHORT="SHORT";MEDIUM="MEDIUM";LONG="LONG";UNSPECIFIED="UNSPECIFIED"
class Priority(str,Enum): LOW="LOW";NORMAL="NORMAL";HIGH="HIGH";CRITICAL="CRITICAL"
class ConstraintKind(str,Enum): HARD="HARD";SOFT="SOFT";SAFETY="SAFETY";RESOURCE="RESOURCE";TIME="TIME";DEPENDENCY="DEPENDENCY";SCOPE="SCOPE";POLICY="POLICY";APPROVAL="APPROVAL";CAPABILITY="CAPABILITY"
class ConstraintSource(str,Enum): USER="USER";HOST="HOST";GOVERNANCE="GOVERNANCE";COGNITIVE_RESULT="COGNITIVE_RESULT";COUNCIL_RESULT="COUNCIL_RESULT";SYSTEM_HARD_LIMIT="SYSTEM_HARD_LIMIT"
class PlanStatus(str,Enum): DRAFT="DRAFT";VALID="VALID";PARTIAL="PARTIAL";BLOCKED="BLOCKED";REQUIRES_APPROVAL="REQUIRES_APPROVAL";READY_FOR_REVIEW="READY_FOR_REVIEW";REJECTED="REJECTED"
class StepStatus(str,Enum): PROPOSED="PROPOSED";BLOCKED="BLOCKED";READY_FOR_REVIEW="READY_FOR_REVIEW";REQUIRES_APPROVAL="REQUIRES_APPROVAL"
class PreconditionKind(str,Enum): INFORMATION_AVAILABLE="INFORMATION_AVAILABLE";APPROVAL_GRANTED="APPROVAL_GRANTED";RESOURCE_AVAILABLE="RESOURCE_AVAILABLE";PRIOR_STEP_VALIDATED="PRIOR_STEP_VALIDATED";CAPABILITY_AVAILABLE="CAPABILITY_AVAILABLE";TIME_WINDOW_OPEN="TIME_WINDOW_OPEN"
class ActionType(str,Enum): READ="READ";ANALYZE="ANALYZE";CREATE="CREATE";UPDATE="UPDATE";DELETE="DELETE";SEND="SEND";EXECUTE_TOOL="EXECUTE_TOOL";CALL_AGENT="CALL_AGENT";EXTERNAL_REQUEST="EXTERNAL_REQUEST";HUMAN_DECISION="HUMAN_DECISION"
class SideEffectClass(str,Enum): NONE="NONE";LOCAL_REVERSIBLE="LOCAL_REVERSIBLE";LOCAL_IRREVERSIBLE="LOCAL_IRREVERSIBLE";EXTERNAL_REVERSIBLE="EXTERNAL_REVERSIBLE";EXTERNAL_IRREVERSIBLE="EXTERNAL_IRREVERSIBLE";UNKNOWN="UNKNOWN"
class RiskLevel(str,Enum): LOW="LOW";MEDIUM="MEDIUM";HIGH="HIGH";CRITICAL="CRITICAL";UNKNOWN="UNKNOWN"
class BudgetUncertainty(str,Enum): EXACT="EXACT";ESTIMATED="ESTIMATED";UNKNOWN="UNKNOWN"
class ApprovalKind(str,Enum): NONE="NONE";HUMAN="HUMAN";HOST="HOST";SECURITY_REVIEW="SECURITY_REVIEW";BUDGET_REVIEW="BUDGET_REVIEW";POLICY_REVIEW="POLICY_REVIEW";FUTURE_CONTROL_CORE="FUTURE_CONTROL_CORE"
class PolicyOutcome(str,Enum): ALLOW_FOR_REVIEW="ALLOW_FOR_REVIEW";REQUIRES_APPROVAL="REQUIRES_APPROVAL";BLOCK="BLOCK";INVALID="INVALID"
class ExecutiveStatus(str,Enum): PLAN_READY_FOR_REVIEW="PLAN_READY_FOR_REVIEW";PLAN_PARTIAL="PLAN_PARTIAL";PLAN_BLOCKED="PLAN_BLOCKED";MORE_CONTEXT_REQUIRED="MORE_CONTEXT_REQUIRED";APPROVAL_REQUIRED="APPROVAL_REQUIRED";INVALID_REQUEST="INVALID_REQUEST"
class Availability(str,Enum): AVAILABLE="AVAILABLE";UNAVAILABLE="UNAVAILABLE";UNKNOWN="UNKNOWN"

@dataclass(frozen=True,slots=True)
class PlannerLimits:
    max_steps:int=32;max_dependencies:int=96;max_proposals:int=64;max_assumptions:int=32;max_risks:int=64;max_checkpoints:int=64;max_revisions:int=16;max_iterations:int=2;max_wall_time_ms:float=1000;max_depth:int=8
    def __post_init__(self):
        if any(type(x) is not int or x<1 for x in (self.max_steps,self.max_dependencies,self.max_proposals,self.max_assumptions,self.max_risks,self.max_checkpoints,self.max_revisions,self.max_iterations,self.max_depth)) or not isfinite(self.max_wall_time_ms) or self.max_wall_time_ms<=0:raise ValueError("positive bounded planning limits required")
GLOBAL_PLANNER_LIMITS=PlannerLimits()
@dataclass(frozen=True,slots=True)
class ResourceBudget:
    max_time_minutes:float|None=None;max_compute_units:float|None=None;max_tokens:int|None=None;max_money:float|None=None;currency:str|None=None;max_external_calls:int|None=None;max_tool_calls:int|None=None;max_agent_calls:int|None=None;max_human_reviews:int|None=None;max_storage_bytes:int|None=None
    def __post_init__(self):
        values=(self.max_time_minutes,self.max_compute_units,self.max_tokens,self.max_money,self.max_external_calls,self.max_tool_calls,self.max_agent_calls,self.max_human_reviews,self.max_storage_bytes)
        if any(x is not None and (isinstance(x,bool) or x<0) for x in values):raise ValueError("resource limits must be nonnegative")
        if self.max_money is not None and not self.currency:raise ValueError("currency required for monetary budget")
@dataclass(frozen=True,slots=True)
class Goal:
    id:GoalId;statement:str;success_criteria:tuple[str,...]=();constraints:tuple[ConstraintId,...]=();priority:Priority=Priority.NORMAL;horizon:TimeHorizon=TimeHorizon.UNSPECIFIED;source:GoalSource=GoalSource.HUMAN;correlation_id:str|None=None;created_at:datetime|None=None;status:GoalStatus=GoalStatus.DRAFT;ambiguity_flags:tuple[str,...]=()
    def __post_init__(self):
        if type(self.id) is not GoalId:raise TypeError("GoalId required")
        if not self.statement.strip():raise ValueError("goal statement required")
        if self.source is GoalSource.FUTURE_EXECUTIVE:raise ValueError("self-generated goals are reserved")
        if self.created_at is not None:require_utc(self.created_at)
@dataclass(frozen=True,slots=True)
class PlanningAssumption:
    id:PlanningAssumptionId;statement:str;source_reason:str;readiness:float;effect_if_false:str;validation_need:str;entity_ids:tuple[NodeId,...]=();source_ids:tuple[SourceId,...]=()
    def __post_init__(self):
        if not 0<=self.readiness<=1:raise ValueError("assumption readiness must be within [0,1]")
@dataclass(frozen=True,slots=True)
class Constraint:
    id:ConstraintId;kind:ConstraintKind;source:ConstraintSource;subject:str;requirement:str;satisfied:bool|None=None;prohibits:bool=False;explanation:str=""
@dataclass(frozen=True,slots=True)
class ExecutiveRequest:
    id:ExecutiveRequestId;goal:Goal|None;cognitive_result:CognitiveResult|None=None;council_result:CouncilResult|None=None;constraints:tuple[Constraint,...]=();deadline:datetime|None=None;resource_budget:ResourceBudget|None=None;allowed_action_categories:tuple[ActionType,...]=();prohibited_action_categories:tuple[ActionType,...]=();priority:Priority=Priority.NORMAL;correlation_id:str|None=None;diagnostics:bool=True;limits:PlannerLimits=PlannerLimits()
    def __post_init__(self):
        if type(self.id) is not ExecutiveRequestId:raise TypeError("ExecutiveRequestId required")
        if self.deadline is not None:require_utc(self.deadline)
@dataclass(frozen=True,slots=True)
class ExecutiveContext:
    cognitive_request_id:CognitiveRequestId|None;council_request_id:CouncilRequestId|None;entity_ids:tuple[NodeId,...];source_ids:tuple[SourceId,...];inference_ids:tuple[InferenceId,...];unresolved_gaps:tuple[str,...];uncertainties:tuple[str,...];conflicts:tuple[str,...];agreement_ids:tuple[CouncilAgreementId,...];disagreement_ids:tuple[CouncilDisagreementId,...];minority_entity_ids:tuple[NodeId,...];shared_state_fingerprint:str;limitations:tuple[str,...]
@dataclass(frozen=True,slots=True)
class Precondition:
    kind:PreconditionKind;description:str;satisfied:bool|None
@dataclass(frozen=True,slots=True)
class PlanDependency:
    predecessor_id:PlanStepId;successor_id:PlanStepId;critical:bool=True;reason:str=""
@dataclass(frozen=True,slots=True)
class BudgetEstimate:
    time_minutes:float|None;compute_units:float|None;tokens:int|None;money:float|None;currency:str|None;external_calls:int;tool_calls:int;agent_calls:int;human_reviews:int;storage_bytes:int|None;uncertainty:BudgetUncertainty;basis:str
@dataclass(frozen=True,slots=True)
class ApprovalRequirement:
    kind:ApprovalKind;reason:str;mandatory:bool;reviewer:str|None=None
@dataclass(frozen=True,slots=True)
class RiskAssessment:
    id:RiskAssessmentId;level:RiskLevel;drivers:tuple[str,...];description:str;proposal_ids:tuple[ActionProposalId,...];mitigations:tuple[str,...]=();probability_claimed:bool=False
@dataclass(frozen=True,slots=True)
class CapabilityDescriptor:
    id:CapabilityId;category:ActionType;description:str;side_effect_class:SideEffectClass;input_schema_ref:str|None;availability:Availability;approval_class:ApprovalKind;source:str
@dataclass(frozen=True,slots=True)
class ActionProposal:
    id:ActionProposalId;step_id:PlanStepId;action_type:ActionType;target_descriptor:str;parameters:tuple[tuple[str,str],...];preconditions:tuple[Precondition,...];expected_effect:str;reversible:bool|None;reversibility_notes:str;estimated_risk:RiskLevel;estimated_cost:BudgetEstimate;required_approval:ApprovalRequirement;capability_requirement:CapabilityDescriptor|None;idempotency_requirement:str;side_effect_class:SideEffectClass;explanation:str;entity_ids:tuple[NodeId,...]=();source_ids:tuple[SourceId,...]=()
    def __post_init__(self):
        if type(self.id) is not ActionProposalId or type(self.step_id) is not PlanStepId:raise TypeError("typed proposal identifiers required")
        if not isinstance(self.parameters,tuple) or any(not isinstance(x,tuple) or len(x)!=2 or any(type(v) is not str for v in x) for x in self.parameters):raise TypeError("proposal parameters must be immutable string pairs")
@dataclass(frozen=True,slots=True)
class PlanCheckpoint:
    id:PlanCheckpointId;step_id:PlanStepId;description:str;blocking:bool;verification_criteria:tuple[str,...]
@dataclass(frozen=True,slots=True)
class PlanStep:
    id:PlanStepId;objective:str;description:str;dependencies:tuple[PlanStepId,...];preconditions:tuple[Precondition,...];expected_output:str;verification_criteria:tuple[str,...];action_proposals:tuple[ActionProposal,...];risk_ids:tuple[RiskAssessmentId,...];budget_estimate:BudgetEstimate;approval_requirements:tuple[ApprovalRequirement,...];status:StepStatus;criterion_refs:tuple[str,...]
@dataclass(frozen=True,slots=True)
class PolicyDecisionRecord:
    id:PolicyDecisionId;outcome:PolicyOutcome;rule_ids:tuple[str,...];proposal_ids:tuple[ActionProposalId,...];reasons:tuple[str,...];severity:RiskLevel;policy_version:str;inputs_used:tuple[str,...]
@dataclass(frozen=True,slots=True)
class PlanValidationResult:
    valid:bool;errors:tuple[str,...];warnings:tuple[str,...];uncovered_criteria:tuple[str,...];blocked_step_ids:tuple[PlanStepId,...];topological_order:tuple[PlanStepId,...];policy_decisions:tuple[PolicyDecisionRecord,...]
@dataclass(frozen=True,slots=True)
class ApprovalEnvelope:
    id:ApprovalEnvelopeId;plan_id:PlanId;plan_version:int;proposal_ids:tuple[ActionProposalId,...];risk_ids:tuple[RiskAssessmentId,...];side_effects:tuple[SideEffectClass,...];budget_estimate:BudgetEstimate;unresolved_gaps:tuple[str,...];required_reviewers:tuple[ApprovalKind,...];approval_scope:str;valid:bool=True
@dataclass(frozen=True,slots=True)
class Plan:
    id:PlanId;goal_id:GoalId;version:int;status:PlanStatus;steps:tuple[PlanStep,...];dependencies:tuple[PlanDependency,...];checkpoints:tuple[PlanCheckpoint,...];assumptions:tuple[PlanningAssumption,...];constraints:tuple[Constraint,...];risks:tuple[RiskAssessment,...];budget_estimate:BudgetEstimate;resource_budget:ResourceBudget|None;unresolved_gaps:tuple[str,...];approval_requirements:tuple[ApprovalRequirement,...];entity_ids:tuple[NodeId,...];source_ids:tuple[SourceId,...];inference_ids:tuple[InferenceId,...];planner_version:str;config_fingerprint:str;prior_version:int|None=None;revision_reason:str|None=None
@dataclass(frozen=True,slots=True)
class PlanDiff:
    from_version:int;to_version:int;steps_added:tuple[PlanStepId,...];steps_removed:tuple[PlanStepId,...];steps_modified:tuple[PlanStepId,...];dependencies_changed:bool;risks_changed:bool;approvals_changed:bool;budget_changed:bool;assumptions_changed:bool
@dataclass(frozen=True,slots=True)
class ExecutiveDiagnostics:
    timings_ms:tuple[tuple[str,float],...];counts:tuple[tuple[str,int],...];truncated:tuple[str,...];iterations:int
@dataclass(frozen=True,slots=True)
class ExecutiveResult:
    request_id:ExecutiveRequestId;status:ExecutiveStatus;goal:Goal|None;context:ExecutiveContext|None;plan:Plan|None;validation:PlanValidationResult|None;approval_envelope:ApprovalEnvelope|None;plan_diff:PlanDiff|None;diagnostics:ExecutiveDiagnostics;limitations:tuple[str,...]
