from .model import RiskLevel,SideEffectClass
from .runtime_model import *
_risk={RiskLevel.LOW:0,RiskLevel.MEDIUM:1,RiskLevel.HIGH:2,RiskLevel.CRITICAL:3,RiskLevel.UNKNOWN:4}
class ExecutionStopController:
    def __init__(self):self.stopped=False;self.reason=None
    def stop(self,reason):self.stopped=True;self.reason=reason
class CircuitBreaker:
    def __init__(self,threshold=2):self.threshold=threshold;self.failures={};self.states={}
    def state(self,capability_id):return self.states.get(capability_id,CircuitState.CLOSED)
    def success(self,capability_id):self.failures[capability_id]=0;self.states[capability_id]=CircuitState.CLOSED
    def failure(self,capability_id):
        n=self.failures.get(capability_id,0)+1;self.failures[capability_id]=n
        if n>=self.threshold:self.states[capability_id]=CircuitState.OPEN
class RuntimePolicyEvaluator:
    def evaluate(self,approved,budget,actions,writes,retries,state,stopped):
        rules=[];reasons=[];outcome=GateOutcome.ALLOW
        if approved.approval.status is not RuntimeApprovalStatus.VALID:outcome=GateOutcome.BLOCK;rules.append("RUN-001");reasons.append("approval invalid")
        d=approved.capability
        if d.status is not CapabilityStatus.AVAILABLE or d.health is not CapabilityHealth.HEALTHY:outcome=GateOutcome.BLOCK;rules.append("RUN-002");reasons.append("capability unavailable or degraded")
        if _risk[d.risk_floor]>_risk[approved.proposal.estimated_risk]:outcome=GateOutcome.WAIT;rules.append("RUN-003");reasons.append("runtime risk exceeds planned risk")
        is_write=d.side_effect_class is not SideEffectClass.NONE
        if actions>=budget.max_actions or retries>budget.max_retries or (is_write and writes>=budget.max_write_delete_operations):outcome=GateOutcome.BLOCK;rules.append("RUN-004");reasons.append("runtime budget exceeded")
        if state is IdempotencyState.SUCCEEDED:outcome=GateOutcome.BLOCK;rules.append("RUN-005");reasons.append("idempotency already completed")
        if state in (IdempotencyState.IN_PROGRESS,IdempotencyState.UNKNOWN_OUTCOME):outcome=GateOutcome.WAIT;rules.append("RUN-006");reasons.append("uncertain prior execution requires reconciliation")
        if stopped:outcome=GateOutcome.BLOCK;rules.append("RUN-007");reasons.append("emergency stop active")
        if not rules:rules=("RUN-100","RUN-101","RUN-102","RUN-103");reasons=("approval valid","capability available","risk and budget within scope","idempotency clear")
        return ExecutionGateDecision(outcome,tuple(rules),tuple(reasons),max(d.risk_floor,approved.proposal.estimated_risk,key=lambda x:_risk[x]),state)
class ExecutionGate:
    def __init__(self,policy=None):self.policy=policy or RuntimePolicyEvaluator()
    def evaluate(self,*args,**kwargs):return self.policy.evaluate(*args,**kwargs)
