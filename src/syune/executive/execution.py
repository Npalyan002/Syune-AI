"""Explicit supervised L3 entry point; no background execution or replanning."""
from dataclasses import replace
from datetime import datetime,timezone
from hashlib import sha256
from time import perf_counter
from uuid import NAMESPACE_URL,uuid5
from syune.core import *
from .approval_runtime import ApprovalVerifier,parameter_hash
from .capabilities import RetryableCapabilityError,UnknownCapabilityOutcome
from .errors import ExecutionError,ExecutionErrorCode
from .execution_store import receipt_payload,attach_record
from .model import RiskLevel,SideEffectClass,PlanStatus,StepStatus
from .runtime_gate import CircuitBreaker,ExecutionGate,ExecutionStopController
from .runtime_model import *
from .verification import OutcomeVerifier
def _now():return datetime.now(timezone.utc)
def _invocation_key(plan,proposal,capability,parameters):return sha256(repr((plan.id,plan.version,proposal.id,capability.id,parameters)).encode()).hexdigest()
def _risk_rank(value):return {RiskLevel.LOW:0,RiskLevel.MEDIUM:1,RiskLevel.HIGH:2,RiskLevel.CRITICAL:3,RiskLevel.UNKNOWN:4}[value]
class SupervisedExecutiveService:
    def __init__(self,plans,registry,executions,stop_controller=None,circuit_breaker=None):
        self.plans=plans;self.registry=registry;self.executions=executions;self.stop=stop_controller or ExecutionStopController();self.circuit=circuit_breaker or CircuitBreaker();self.approvals=ApprovalVerifier();self.gate=ExecutionGate();self.verifier=OutcomeVerifier()
    def _load(self,request):
        try:plan=self.plans.get(request.plan_id,request.plan_version);envelope=self.plans.envelope(request.plan_id,request.plan_version)
        except KeyError as exc:raise ExecutionError(ExecutionErrorCode.PLAN_NOT_FOUND,"exact plan version not found") from exc
        if plan.id!=request.plan_id or plan.version!=request.plan_version:raise ExecutionError(ExecutionErrorCode.PLAN_VERSION_MISMATCH,"plan identity mismatch")
        if envelope.id!=request.approval_envelope_id or not envelope.valid:raise ExecutionError(ExecutionErrorCode.APPROVAL_INVALID,"approval envelope missing, stale, or invalid")
        if plan.status in (PlanStatus.BLOCKED,PlanStatus.REJECTED) or any(s.status is StepStatus.BLOCKED for s in plan.steps):
            raise ExecutionError(ExecutionErrorCode.APPROVAL_INVALID,"blocked plan is not executable")
        proposals={p.id:(step,p) for step in plan.steps for p in step.action_proposals}
        if any(x not in proposals for x in request.proposal_ids):raise ExecutionError(ExecutionErrorCode.PROPOSAL_NOT_FOUND,"requested proposal not in plan")
        return plan,envelope,proposals
    def execute_approved(self,request:ExecutionRequest):
        if not isinstance(request,ExecutionRequest):raise ExecutionError(ExecutionErrorCode.INVALID_EXECUTION_REQUEST,"ExecutionRequest required")
        started=perf_counter();metrics={x:0.0 for x in ("approval_verification","capability_resolution","gate_evaluation","metadata_transaction","adapter_invocation","verification")};plan,envelope,proposals=self._load(request);receipts=[];decisions=[];feedback=[];drafts=[];completed_steps=set();actions=writes=retries=0;overrides=dict(request.parameter_overrides)
        if request.approval and request.runtime_budget!=request.approval.budget:
            decision=ExecutionGateDecision(GateOutcome.BLOCK,("RUN-008",),("runtime budget differs from approved ceiling",),RiskLevel.UNKNOWN,IdempotencyState.NOT_SEEN)
            return SupervisedExecutionResult(request.id,RuntimeResultStatus.EXECUTION_BLOCKED,(),(decision,),(),(),(('total',(perf_counter()-started)*1000),),None)
        for proposal_id in request.proposal_ids:
            if (perf_counter()-started)*1000>=request.runtime_budget.max_wall_time_ms:
                decisions.append(ExecutionGateDecision(GateOutcome.BLOCK,("RUN-010",),("runtime wall-time budget exhausted",),RiskLevel.UNKNOWN,IdempotencyState.NOT_SEEN));break
            if self.stop.stopped:return SupervisedExecutionResult(request.id,RuntimeResultStatus.EXECUTION_PARTIAL if receipts else RuntimeResultStatus.EXECUTION_BLOCKED,tuple(receipts),tuple(decisions),tuple(feedback),tuple(drafts),(('total',(perf_counter()-started)*1000),),self.stop.reason)
            step,proposal=proposals[proposal_id];parameters=overrides.get(proposal.id,proposal.parameters)
            if any(dep not in completed_steps for dep in step.dependencies):
                feedback.append(ExecutionFeedback(ExecutionId.new(),"dependency_missing","verified predecessor required",False));break
            required={x.id for x in plan.checkpoints if x.step_id==step.id and x.blocking}
            if not required.issubset(set(request.satisfied_checkpoint_ids)):
                decisions.append(ExecutionGateDecision(GateOutcome.WAIT,("RUN-020",),("blocking checkpoint unsatisfied",),proposal.estimated_risk,IdempotencyState.NOT_SEEN));break
            if not proposal.capability_requirement:raise ExecutionError(ExecutionErrorCode.CAPABILITY_NOT_FOUND,"proposal has no executable registered capability descriptor")
            tick=perf_counter();descriptor,adapter=self.registry.resolve(proposal.capability_requirement.id);metrics["capability_resolution"]+=(perf_counter()-tick)*1000
            if set(dict(parameters))!=set(descriptor.input_fields) or descriptor.side_effect_class is not proposal.side_effect_class:
                decisions.append(ExecutionGateDecision(GateOutcome.INVALID,("RUN-009",),("capability schema or side-effect metadata mismatch",),descriptor.risk_floor,IdempotencyState.NOT_SEEN));break
            key=_invocation_key(plan,proposal,descriptor,parameters);prior=self.executions.state(key)
            approval=self.approvals.verify(plan,envelope,request.approval,proposal,parameters,_now())
            if approval.status is not RuntimeApprovalStatus.VALID:
                decisions.append(ExecutionGateDecision(GateOutcome.BLOCK,approval.rule_ids,approval.reasons,proposal.estimated_risk,prior));break
            if prior is IdempotencyState.FAILED_FINAL:
                decisions.append(ExecutionGateDecision(GateOutcome.BLOCK,("RUN-011",),("terminal failure requires explicit recovery or rollback",),proposal.estimated_risk,prior));break
            if prior in (IdempotencyState.SUCCEEDED,IdempotencyState.ROLLED_BACK):receipts.append(self.executions.receipt(key,True));completed_steps.add(step.id);continue
            if prior in (IdempotencyState.IN_PROGRESS,IdempotencyState.UNKNOWN_OUTCOME):
                decisions.append(ExecutionGateDecision(GateOutcome.WAIT,("RUN-006",),("prior outcome requires reconciliation",),proposal.estimated_risk,prior));break
            now=_now();tick=perf_counter();approval=self.approvals.verify(plan,envelope,request.approval,proposal,parameters,now);metrics["approval_verification"]+=(perf_counter()-tick)*1000
            invocation=CapabilityInvocation(descriptor.id,proposal.id,parameters,key,proposal.side_effect_class,descriptor.output_fields,None,request.correlation_id)
            approved=ApprovedProposal(proposal,approval,descriptor,invocation)
            if self.circuit.state(descriptor.id) is CircuitState.OPEN:
                decisions.append(ExecutionGateDecision(GateOutcome.BLOCK,("RUN-030",),("capability circuit open",),descriptor.risk_floor,prior));feedback.append(ExecutionFeedback(ExecutionId.new(),"capability_unavailable","replan required",True));break
            if request.approval and (_risk_rank(descriptor.risk_floor)>_risk_rank(request.approval.risk_ceiling) or descriptor.side_effect_class not in request.approval.side_effect_classes):
                decisions.append(ExecutionGateDecision(GateOutcome.WAIT,("RUN-003",),("runtime risk or side effect exceeds approval",),descriptor.risk_floor,prior));break
            attempt=0;receipt=None
            while attempt<request.retry_policy.max_attempts:
                tick=perf_counter();approval=self.approvals.verify(plan,envelope,request.approval,proposal,parameters,_now());metrics["approval_verification"]+=(perf_counter()-tick)*1000;approved=replace(approved,approval=approval)
                tick=perf_counter();decision=self.gate.evaluate(approved,request.runtime_budget,actions,writes,retries,prior,self.stop.stopped);metrics["gate_evaluation"]+=(perf_counter()-tick)*1000;decisions.append(decision)
                if decision.outcome is not GateOutcome.ALLOW:break
                attempt+=1;execution_id=ExecutionId(uuid5(NAMESPACE_URL,key));receipt_id=ExecutionReceiptId(uuid5(NAMESPACE_URL,key+":receipt"));payload={"execution_id":str(execution_id),"plan_id":str(plan.id),"plan_version":plan.version,"proposal_id":str(proposal.id),"capability_id":str(descriptor.id),"approval_id":str(request.approval.id) if request.approval else None}
                payload["record"]={"execution_id":str(execution_id),"request_id":str(request.id),"plan_id":str(plan.id),"plan_version":plan.version,"proposal_id":str(proposal.id),"approval_id":str(request.approval.id),"approval_fingerprint":approval.fingerprint,"gate_outcome":decision.outcome.value,"gate_rules":decision.rule_ids,"correlation_id":request.correlation_id}
                payload["goal_id"]=str(plan.goal_id)
                payload["evidence_ids"]=tuple(f"{type(x).__name__}:{x}" for x in proposal.entity_ids)
                action_started=_now();tick=perf_counter();self.executions.begin(key,payload,{"capability_id":str(descriptor.id),"proposal_id":str(proposal.id),"parameters":parameters,"side_effect":proposal.side_effect_class.value,"output_fields":descriptor.output_fields,"correlation_id":request.correlation_id});metrics["metadata_transaction"]+=(perf_counter()-tick)*1000
                actions+=1;writes+=descriptor.side_effect_class is not SideEffectClass.NONE
                try:
                    tick=perf_counter();raw=adapter.invoke(invocation);metrics["adapter_invocation"]+=(perf_counter()-tick)*1000
                except UnknownCapabilityOutcome as exc:
                    outcome=ExecutionOutcome("UNKNOWN","adapter reported uncertain effect",(),None,proposal.target_descriptor,(("adapter",descriptor.adapter_id),),(type(exc).__name__,),("side effect may have occurred",),descriptor.verification_mode);receipt=ExecutionReceipt(receipt_id,execution_id,plan.id,plan.version,proposal.id,ExecutionStatus.UNKNOWN_OUTCOME,outcome,None,False,_now());self.executions.finish(key,IdempotencyState.UNKNOWN_OUTCOME,receipt_payload(receipt));feedback.append(ExecutionFeedback(execution_id,"unknown_outcome","reconciliation required",True));self.circuit.failure(descriptor.id);break
                except RetryableCapabilityError as exc:
                    retries+=1;prior=IdempotencyState.FAILED_RETRYABLE
                    if attempt>=request.retry_policy.max_attempts or retries>request.runtime_budget.max_retries or descriptor.idempotency_mode is IdempotencyMode.UNSUPPORTED:
                        receipt=ExecutionReceipt(receipt_id,execution_id,plan.id,plan.version,proposal.id,ExecutionStatus.FAILED_RETRYABLE,None,None,False,_now());self.executions.finish(key,IdempotencyState.FAILED_RETRYABLE,receipt_payload(receipt));self.circuit.failure(descriptor.id);break
                    self.executions.finish(key,IdempotencyState.FAILED_RETRYABLE,payload)
                    continue
                except Exception as exc:
                    receipt=ExecutionReceipt(receipt_id,execution_id,plan.id,plan.version,proposal.id,ExecutionStatus.UNKNOWN_OUTCOME,None,None,False,_now());self.executions.finish(key,IdempotencyState.UNKNOWN_OUTCOME,receipt_payload(receipt));feedback.append(ExecutionFeedback(execution_id,"unknown_outcome",type(exc).__name__,True));self.circuit.failure(descriptor.id);break
                outcome=ExecutionOutcome("RETURNED","adapter returned structured output",tuple(raw),True,proposal.target_descriptor,(("adapter",descriptor.adapter_id),("version",descriptor.adapter_version)),(),(),descriptor.verification_mode);tick=perf_counter();verification=self.verifier.verify(descriptor,adapter,invocation,raw);metrics["verification"]+=(perf_counter()-tick)*1000;status=ExecutionStatus.SUCCEEDED_VERIFIED if verification.status in (VerificationStatus.PASSED,VerificationStatus.NOT_REQUIRED) else ExecutionStatus.ROLLBACK_REQUIRED;state=IdempotencyState.SUCCEEDED if status is ExecutionStatus.SUCCEEDED_VERIFIED else IdempotencyState.FAILED_FINAL;receipt=ExecutionReceipt(receipt_id,execution_id,plan.id,plan.version,proposal.id,status,outcome,verification,False,_now());tick=perf_counter();self.executions.finish(key,state,receipt_payload(receipt));metrics["metadata_transaction"]+=(perf_counter()-tick)*1000
                if status is ExecutionStatus.SUCCEEDED_VERIFIED:self.circuit.success(descriptor.id);completed_steps.add(step.id);drafts.append(LearningSignalDraft("POSITIVE_OUTCOME",execution_id,proposal.id,"verified supervised outcome",False))
                else:self.circuit.failure(descriptor.id);feedback.append(ExecutionFeedback(execution_id,"verification_failed","rollback or replan required",True))
                break
            if receipt:
                record=ExecutionRecord(receipt.execution_id,request.id,plan.id,plan.version,proposal.id,descriptor.id,descriptor.version,request.approval.id,approval.fingerprint,key,decision,action_started,receipt.created_at,receipt.status,receipt.outcome,receipt.verification,retries,receipt.status if receipt.status in (ExecutionStatus.ROLLBACK_REQUIRED,ExecutionStatus.ROLLED_BACK) else None,None,None,key)
                state=self.executions.state(key);tick=perf_counter();self.executions.finish(key,state,attach_record(receipt_payload(receipt),record));metrics["metadata_transaction"]+=(perf_counter()-tick)*1000;receipts.append(receipt)
            if not receipt or receipt.status is not ExecutionStatus.SUCCEEDED_VERIFIED:break
        status=RuntimeResultStatus.COMPLETED_VERIFIED if len(receipts)==len(request.proposal_ids) and all(x.status is ExecutionStatus.SUCCEEDED_VERIFIED for x in receipts) else RuntimeResultStatus.EXECUTION_PARTIAL if receipts else RuntimeResultStatus.EXECUTION_BLOCKED
        return SupervisedExecutionResult(request.id,status,tuple(receipts),tuple(decisions),tuple(feedback),tuple(drafts),tuple(metrics.items())+(('total',(perf_counter()-started)*1000),),self.stop.reason)
    def rollback(self,execution_request,receipt):
        if not execution_request.approval or not execution_request.approval.allow_rollback:raise ExecutionError(ExecutionErrorCode.APPROVAL_SCOPE_MISMATCH,"rollback not approved")
        plan,envelope,proposals=self._load(execution_request)
        if (receipt.plan_id,receipt.plan_version)!=(plan.id,plan.version) or receipt.proposal_id not in execution_request.proposal_ids:
            raise ExecutionError(ExecutionErrorCode.APPROVAL_SCOPE_MISMATCH,"rollback receipt outside request scope")
        _,proposal=proposals[receipt.proposal_id]
        verification=self.approvals.verify(plan,envelope,execution_request.approval,proposal,proposal.parameters,_now())
        if verification.status is not RuntimeApprovalStatus.VALID:
            raise ExecutionError(ExecutionErrorCode.APPROVAL_INVALID,"rollback approval invalid")
        # Locate persisted invocation by stable receipt identity.
        candidates=self.executions.db.execute("SELECT idempotency_key,invocation FROM executions").fetchall()
        import json
        key,inv_data=next((k,json.loads(i)) for k,i in candidates if self.executions.receipt(k) and self.executions.receipt(k).execution_id==receipt.execution_id)
        saved=self.executions.row(key)[1]
        if saved.get("record",{}).get("approval_id")!=str(execution_request.approval.id) or self.executions.receipt(key)!=receipt:
            raise ExecutionError(ExecutionErrorCode.APPROVAL_SCOPE_MISMATCH,"rollback requires original receipt and approval identity")
        descriptor,adapter=self.registry.resolve(CapabilityId.parse(inv_data["capability_id"]));invocation=CapabilityInvocation(descriptor.id,ActionProposalId.parse(inv_data["proposal_id"]),tuple(map(tuple,inv_data["parameters"])),key,SideEffectClass(inv_data["side_effect"]),tuple(inv_data["output_fields"]),None,inv_data["correlation_id"])
        if descriptor.rollback_mode is RollbackMode.UNSUPPORTED:raise ExecutionError(ExecutionErrorCode.ROLLBACK_FAILED,"capability is not reversible")
        ok,observed=adapter.rollback(invocation);verification=VerificationResult(VerificationId(uuid5(NAMESPACE_URL,key+":rollback")),VerificationStatus.PASSED if ok else VerificationStatus.FAILED,descriptor.verification_mode,"restored prior state",observed,("rollback verified",) if ok else ("rollback mismatch",));plan=RollbackPlan(RollbackPlanId(uuid5(NAMESPACE_URL,key+":rollback-plan")),receipt.execution_id,descriptor.id,invocation.parameters,True,"adapter snapshot",descriptor.verification_mode,None,("rollback is a separate approved side effect",));result=RollbackResult(RollbackResultId(uuid5(NAMESPACE_URL,key+":rollback-result")),plan.id,ExecutionStatus.ROLLED_BACK if ok else ExecutionStatus.FAILED_FINAL,verification,"original receipt retained")
        if ok:self.executions.finish(key,IdempotencyState.ROLLED_BACK,receipt_payload(replace(receipt,status=ExecutionStatus.ROLLED_BACK)))
        return plan,result
    def recover_incomplete(self):
        results=[]
        for key,payload,data in self.executions.incomplete():
            descriptor,adapter=self.registry.resolve(CapabilityId.parse(data["capability_id"]))
            invocation=CapabilityInvocation(descriptor.id,ActionProposalId.parse(data["proposal_id"]),tuple(map(tuple,data["parameters"])),key,SideEffectClass(data["side_effect"]),tuple(data["output_fields"]),None,data["correlation_id"])
            try:
                ok,observed=adapter.verify(invocation,())
                verification_status=VerificationStatus.PASSED if ok else VerificationStatus.FAILED
            except Exception:
                ok=False;observed="verification unavailable";verification_status=VerificationStatus.UNAVAILABLE
            verification=VerificationResult(VerificationId(uuid5(NAMESPACE_URL,key+":reconcile")),verification_status,descriptor.verification_mode,"approved target state",str(observed),("reconciliation read-back; no invocation",))
            execution_id=ExecutionId.parse(payload["execution_id"])
            receipt=ExecutionReceipt(ExecutionReceiptId(uuid5(NAMESPACE_URL,key+":receipt")),execution_id,PlanId.parse(payload["plan_id"]),payload["plan_version"],ActionProposalId.parse(payload["proposal_id"]),ExecutionStatus.SUCCEEDED_VERIFIED if ok else ExecutionStatus.UNKNOWN_OUTCOME,None,verification,False,_now())
            self.executions.finish(key,IdempotencyState.SUCCEEDED if ok else IdempotencyState.UNKNOWN_OUTCOME,receipt_payload(receipt))
            results.append(receipt)
        return tuple(results)
