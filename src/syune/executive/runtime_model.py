"""Typed Phase 13 supervised execution contracts."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from syune.core import *
from .model import ActionProposal,ActionProposalId,ApprovalEnvelopeId,ApprovalKind,PlanId,RiskLevel,SideEffectClass,ActionType
class ApprovalSource(str,Enum):HUMAN="HUMAN";HOST="HOST";TEST="TEST";FUTURE_CONTROL_CORE="FUTURE_CONTROL_CORE"
class RuntimeApprovalStatus(str,Enum):VALID="VALID";EXPIRED="EXPIRED";REVOKED="REVOKED";MISMATCHED="MISMATCHED";INSUFFICIENT_SCOPE="INSUFFICIENT_SCOPE";INVALID="INVALID"
class CapabilityStatus(str,Enum):AVAILABLE="AVAILABLE";UNAVAILABLE="UNAVAILABLE";DEGRADED="DEGRADED";DISABLED="DISABLED"
class CapabilityHealth(str,Enum):HEALTHY="HEALTHY";DEGRADED="DEGRADED";UNAVAILABLE="UNAVAILABLE"
class IdempotencyMode(str,Enum):SUPPORTED="SUPPORTED";REQUIRED="REQUIRED";UNSUPPORTED="UNSUPPORTED"
class RollbackMode(str,Enum):SUPPORTED="SUPPORTED";REQUIRES_APPROVAL="REQUIRES_APPROVAL";UNSUPPORTED="UNSUPPORTED"
class VerificationMode(str,Enum):NONE_REQUIRED="NONE_REQUIRED";RETURN_VALUE="RETURN_VALUE";READ_BACK="READ_BACK";STATE_COMPARISON="STATE_COMPARISON";CHECKSUM="CHECKSUM";EXPLICIT_CONFIRMATION="EXPLICIT_CONFIRMATION"
class GateOutcome(str,Enum):ALLOW="ALLOW";WAIT="WAIT";BLOCK="BLOCK";INVALID="INVALID"
class IdempotencyState(str,Enum):NOT_SEEN="NOT_SEEN";IN_PROGRESS="IN_PROGRESS";SUCCEEDED="SUCCEEDED";FAILED_RETRYABLE="FAILED_RETRYABLE";FAILED_FINAL="FAILED_FINAL";ROLLED_BACK="ROLLED_BACK";UNKNOWN_OUTCOME="UNKNOWN_OUTCOME"
class ExecutionStatus(str,Enum):PENDING="PENDING";GATED="GATED";RUNNING="RUNNING";SUCCEEDED_UNVERIFIED="SUCCEEDED_UNVERIFIED";SUCCEEDED_VERIFIED="SUCCEEDED_VERIFIED";FAILED_RETRYABLE="FAILED_RETRYABLE";FAILED_FINAL="FAILED_FINAL";UNKNOWN_OUTCOME="UNKNOWN_OUTCOME";ROLLBACK_REQUIRED="ROLLBACK_REQUIRED";ROLLED_BACK="ROLLED_BACK";BLOCKED="BLOCKED"
class VerificationStatus(str,Enum):PASSED="PASSED";FAILED="FAILED";UNAVAILABLE="UNAVAILABLE";NOT_REQUIRED="NOT_REQUIRED"
class CircuitState(str,Enum):CLOSED="CLOSED";OPEN="OPEN";HALF_OPEN="HALF_OPEN"
class RuntimeResultStatus(str,Enum):EXECUTION_READY="EXECUTION_READY";EXECUTION_BLOCKED="EXECUTION_BLOCKED";EXECUTION_PARTIAL="EXECUTION_PARTIAL";REPLAN_REQUIRED="REPLAN_REQUIRED";COMPLETED_VERIFIED="COMPLETED_VERIFIED";COMPLETED_WITH_WARNINGS="COMPLETED_WITH_WARNINGS"
@dataclass(frozen=True,slots=True)
class RuntimeBudget:
    max_actions:int=1;max_retries:int=0;max_wall_time_ms:float=5000;max_external_calls:int=0;max_compute_units:float|None=None;max_tokens:int|None=None;max_money:float|None=None;currency:str|None=None;max_write_delete_operations:int=1
    def __post_init__(self):
        if any(type(x) is not int or x<0 for x in (self.max_actions,self.max_retries,self.max_external_calls,self.max_write_delete_operations)) or not isfinite(self.max_wall_time_ms) or self.max_wall_time_ms<=0:raise ValueError("bounded runtime budget required")
        if self.max_actions>64 or self.max_retries>3 or self.max_write_delete_operations>64 or self.max_wall_time_ms>60000:
            raise ValueError("runtime global ceiling exceeded")
@dataclass(frozen=True,slots=True)
class RetryPolicy:
    max_attempts:int=1;retryable_errors:tuple[str,...]=("RetryableCapabilityError",);backoff_ms:tuple[int,...]=();requires_idempotency:bool=True;new_approval_required:bool=False
    def __post_init__(self):
        if not 1<=self.max_attempts<=3:raise ValueError("retry attempts bounded to 1..3")
@dataclass(frozen=True,slots=True)
class ApprovalToken:
    id:ApprovalTokenId;source:ApprovalSource;status:RuntimeApprovalStatus;plan_id:PlanId;plan_version:int;envelope_id:ApprovalEnvelopeId;proposal_ids:tuple[ActionProposalId,...];parameter_hashes:tuple[tuple[ActionProposalId,str],...];risk_ceiling:RiskLevel;side_effect_classes:tuple[SideEffectClass,...];budget:RuntimeBudget;issued_at:datetime;expires_at:datetime;approver_ref:str;fingerprint:str;allow_rollback:bool=False;revoked_at:datetime|None=None
    def __post_init__(self):
        if not isinstance(self.source,ApprovalSource) or self.source is ApprovalSource.FUTURE_CONTROL_CORE or not self.proposal_ids:raise ValueError("explicit human/host/test scoped approval required")
        if type(self.id) is not ApprovalTokenId or type(self.plan_id) is not PlanId or type(self.envelope_id) is not ApprovalEnvelopeId:raise TypeError("typed approval identities required")
        if any(type(p) is not ActionProposalId for p in self.proposal_ids) or len(set(self.proposal_ids))!=len(self.proposal_ids):raise ValueError("distinct typed proposal scope required")
        if len(dict(self.parameter_hashes))!=len(self.parameter_hashes) or set(dict(self.parameter_hashes))!=set(self.proposal_ids):raise ValueError("exact parameter hash scope required")
        if not isinstance(self.status,RuntimeApprovalStatus) or not isinstance(self.risk_ceiling,RiskLevel):raise TypeError("typed approval state required")
        require_utc(self.issued_at);require_utc(self.expires_at)
        if self.expires_at<=self.issued_at or not self.approver_ref.strip():raise ValueError("bounded approval lifetime and approver reference required")
@dataclass(frozen=True,slots=True)
class ApprovalVerification:
    status:RuntimeApprovalStatus;rule_ids:tuple[str,...];reasons:tuple[str,...];fingerprint:str
@dataclass(frozen=True,slots=True)
class RuntimeCapabilityDescriptor:
    id:CapabilityId;name:str;category:ActionType;version:str;status:CapabilityStatus;health:CapabilityHealth;side_effect_class:SideEffectClass;input_fields:tuple[str,...];output_fields:tuple[str,...];idempotency_mode:IdempotencyMode;rollback_mode:RollbackMode;verification_mode:VerificationMode;approval_requirement:ApprovalKind;risk_floor:RiskLevel;execution_location:str;adapter_id:str;adapter_version:str;config_source:str
@dataclass(frozen=True,slots=True)
class CapabilityInvocation:
    capability_id:CapabilityId;proposal_id:ActionProposalId;parameters:tuple[tuple[str,str],...];idempotency_key:str;expected_side_effect_class:SideEffectClass;expected_output_fields:tuple[str,...];runtime_deadline:datetime|None;correlation_id:str|None
@dataclass(frozen=True,slots=True)
class ApprovedProposal:
    proposal:ActionProposal;approval:ApprovalVerification;capability:RuntimeCapabilityDescriptor;invocation:CapabilityInvocation
@dataclass(frozen=True,slots=True)
class ExecutionGateDecision:
    outcome:GateOutcome;rule_ids:tuple[str,...];reasons:tuple[str,...];evaluated_risk:RiskLevel;idempotency_state:IdempotencyState
@dataclass(frozen=True,slots=True)
class ExecutionOutcome:
    status:str;observed_effect:str;output_data:tuple[tuple[str,str],...];side_effect_confirmed:bool|None;target_identity:str;adapter_metadata:tuple[tuple[str,str],...];warnings:tuple[str,...];uncertainty:tuple[str,...];verification_requirement:VerificationMode
@dataclass(frozen=True,slots=True)
class VerificationResult:
    id:VerificationId;status:VerificationStatus;mode:VerificationMode;expected:str;observed:str;reasons:tuple[str,...]
@dataclass(frozen=True,slots=True)
class RollbackPlan:
    id:RollbackPlanId;original_execution_id:ExecutionId;capability_id:CapabilityId;parameters:tuple[tuple[str,str],...];approval_required:bool;reversibility_confidence:str;verification_mode:VerificationMode;deadline:datetime|None;limitations:tuple[str,...]
@dataclass(frozen=True,slots=True)
class RollbackResult:
    id:RollbackResultId;plan_id:RollbackPlanId;status:ExecutionStatus;verification:VerificationResult;audit_message:str
@dataclass(frozen=True,slots=True)
class ExecutionRecord:
    id:ExecutionId;request_id:ExecutionRequestId;plan_id:PlanId;plan_version:int;proposal_id:ActionProposalId;capability_id:CapabilityId;capability_version:str;approval_id:ApprovalTokenId;approval_fingerprint:str;invocation_fingerprint:str;gate:ExecutionGateDecision;started_at:datetime;completed_at:datetime|None;status:ExecutionStatus;outcome:ExecutionOutcome|None;verification:VerificationResult|None;retry_count:int;rollback_status:ExecutionStatus|None;error_code:str|None;error_message:str|None;idempotency_key:str
@dataclass(frozen=True,slots=True)
class ExecutionReceipt:
    id:ExecutionReceiptId;execution_id:ExecutionId;plan_id:PlanId;plan_version:int;proposal_id:ActionProposalId;status:ExecutionStatus;outcome:ExecutionOutcome|None;verification:VerificationResult|None;idempotent_replay:bool;created_at:datetime
@dataclass(frozen=True,slots=True)
class LearningSignalDraft:
    category:str;execution_id:ExecutionId;proposal_id:ActionProposalId;summary:str;committed:bool=False
@dataclass(frozen=True,slots=True)
class ExecutionFeedback:
    execution_id:ExecutionId;category:str;description:str;replan_required:bool
@dataclass(frozen=True,slots=True)
class ExecutionRequest:
    id:ExecutionRequestId;plan_id:PlanId;plan_version:int;approval_envelope_id:ApprovalEnvelopeId;proposal_ids:tuple[ActionProposalId,...];approval:ApprovalToken|None;runtime_budget:RuntimeBudget=RuntimeBudget();retry_policy:RetryPolicy=RetryPolicy();satisfied_checkpoint_ids:tuple[PlanCheckpointId,...]=();parameter_overrides:tuple[tuple[ActionProposalId,tuple[tuple[str,str],...]],...]=();correlation_id:str|None=None;diagnostics:bool=True
    def __post_init__(self):
        if not self.proposal_ids or len(set(self.proposal_ids))!=len(self.proposal_ids):raise ValueError("explicit distinct proposal scope required")
@dataclass(frozen=True,slots=True)
class SupervisedExecutionResult:
    request_id:ExecutionRequestId;status:RuntimeResultStatus;receipts:tuple[ExecutionReceipt,...];gate_decisions:tuple[ExecutionGateDecision,...];feedback:tuple[ExecutionFeedback,...];learning_drafts:tuple[LearningSignalDraft,...];timings_ms:tuple[tuple[str,float],...];stop_reason:str|None=None
