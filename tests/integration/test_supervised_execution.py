from dataclasses import replace
from datetime import datetime,timedelta,timezone
from uuid import NAMESPACE_URL,uuid5
from hashlib import sha256
import pytest
from syune.core import *
from syune.executive import *

NOW=datetime(2026,1,1,tzinfo=timezone.utc)
def fixture(tmp_path,mode="",content="amber",stop=None):
    planner=ExecutiveService();goal=Goal(GoalId.new(),"update sandbox file",("file verified",),source=GoalSource.TEST);planned=planner.plan(ExecutiveRequest(ExecutiveRequestId.new(),goal));original=next(p for s in planned.plan.steps for p in s.action_proposals if p.action_type is ActionType.UPDATE)
    params=(("path","case/value.txt"),("content",content),("operation","write"),("mode",mode));proposal=replace(original,parameters=params,target_descriptor="sandbox:case/value.txt",side_effect_class=SideEffectClass.LOCAL_REVERSIBLE,estimated_risk=RiskLevel.MEDIUM)
    step=next(s for s in planned.plan.steps if original in s.action_proposals);step=replace(step,dependencies=(),action_proposals=(proposal,),status=StepStatus.REQUIRES_APPROVAL)
    checkpoint=PlanCheckpoint(PlanCheckpointId.new(),step.id,"human review",True,("scope confirmed",));plan=replace(planned.plan,steps=(step,),dependencies=(),checkpoints=(checkpoint,),risks=(),status=PlanStatus.REQUIRES_APPROVAL)
    envelope=planner._envelope(plan);plans=InMemoryPlanRepository();plans.save(plan,None,envelope)
    descriptor=RuntimeCapabilityDescriptor(proposal.capability_requirement.id,"LOCAL_SANDBOX_WRITE",ActionType.UPDATE,"1",CapabilityStatus.AVAILABLE,CapabilityHealth.HEALTHY,SideEffectClass.LOCAL_REVERSIBLE,("path","content","operation","mode"),("path","content","operation","mode"),IdempotencyMode.REQUIRED,RollbackMode.REQUIRES_APPROVAL,VerificationMode.READ_BACK,ApprovalKind.HUMAN,RiskLevel.MEDIUM,"SYUNE_EXECUTION_SANDBOX","local-file","1","Phase13 test fixture")
    adapter=LocalSandboxFileAdapter(tmp_path/"execution-sandbox");registry=CapabilityRegistry();registry.register(descriptor,adapter);store=SQLiteExecutionRepository(tmp_path/"execution.sqlite3");runtime=SupervisedExecutiveService(plans,registry,store,stop)
    budget=RuntimeBudget(max_actions=3,max_retries=1,max_write_delete_operations=3);hashes=((proposal.id,parameter_hash(proposal,params)),);fingerprint=approval_fingerprint(plan.id,plan.version,(proposal.id,),hashes,RiskLevel.MEDIUM,(SideEffectClass.LOCAL_REVERSIBLE,),budget)
    approval=ApprovalToken(ApprovalTokenId.new(),ApprovalSource.TEST,RuntimeApprovalStatus.VALID,plan.id,plan.version,envelope.id,(proposal.id,),hashes,RiskLevel.MEDIUM,(SideEffectClass.LOCAL_REVERSIBLE,),budget,NOW,NOW+timedelta(days=3650),"pytest",fingerprint,True)
    request=ExecutionRequest(ExecutionRequestId.new(),plan.id,plan.version,envelope.id,(proposal.id,),approval,budget,RetryPolicy(2), (checkpoint.id,))
    return runtime,request,adapter,store,plan,envelope,proposal,descriptor

def test_approved_action_exactly_once_verified_and_persisted(tmp_path):
    runtime,request,adapter,store,*_=fixture(tmp_path);first=runtime.execute_approved(request);second=runtime.execute_approved(request)
    assert first.status is RuntimeResultStatus.COMPLETED_VERIFIED and first.receipts[0].status is ExecutionStatus.SUCCEEDED_VERIFIED
    assert second.receipts[0].idempotent_replay and adapter.calls==1
    assert (tmp_path/"execution-sandbox/case/value.txt").read_text()=="amber"
    assert first.learning_drafts and not first.learning_drafts[0].committed
    assert store.row(next(iter(store.db.execute("SELECT idempotency_key FROM executions")))[0])[1]["record"]["gate_outcome"]=="ALLOW"
    assert {x[0] for x in first.timings_ms}>={"approval_verification","capability_resolution","gate_evaluation","metadata_transaction","adapter_invocation","verification","total"}
    store.close()

def test_no_approval_stale_scope_parameter_and_capability_blocks(tmp_path):
    runtime,request,adapter,store,plan,envelope,proposal,descriptor=fixture(tmp_path)
    no=runtime.execute_approved(replace(request,approval=None));assert no.status is RuntimeResultStatus.EXECUTION_BLOCKED and adapter.calls==0
    stale=replace(request.approval,plan_version=2);stale_result=runtime.execute_approved(replace(request,id=ExecutionRequestId.new(),approval=stale));assert stale_result.status is RuntimeResultStatus.EXECUTION_BLOCKED and adapter.calls==0
    drift=((proposal.id,(("path","other.txt"),("content","amber"),("operation","write"),("mode",""))),)
    drifted=runtime.execute_approved(replace(request,id=ExecutionRequestId.new(),parameter_overrides=drift));assert drifted.status is RuntimeResultStatus.EXECUTION_BLOCKED and adapter.calls==0
    widened=runtime.execute_approved(replace(request,id=ExecutionRequestId.new(),runtime_budget=replace(request.runtime_budget,max_actions=2)));assert widened.status is RuntimeResultStatus.EXECUTION_BLOCKED and adapter.calls==0
    revoked=replace(request.approval,status=RuntimeApprovalStatus.REVOKED,revoked_at=NOW);revoked_result=runtime.execute_approved(replace(request,id=ExecutionRequestId.new(),approval=revoked));assert revoked_result.status is RuntimeResultStatus.EXECUTION_BLOCKED and adapter.calls==0
    expired=replace(request.approval,issued_at=NOW-timedelta(days=2),expires_at=NOW-timedelta(days=1));expired_result=runtime.execute_approved(replace(request,id=ExecutionRequestId.new(),approval=expired));assert expired_result.status is RuntimeResultStatus.EXECUTION_BLOCKED and adapter.calls==0
    descriptor_disabled=replace(descriptor,status=CapabilityStatus.DISABLED);registry=CapabilityRegistry();registry.register(descriptor_disabled,adapter);blocked=SupervisedExecutiveService(runtime.plans,registry,store).execute_approved(replace(request,id=ExecutionRequestId.new()));assert blocked.status is RuntimeResultStatus.EXECUTION_BLOCKED
    store.close()

def test_verification_failure_unknown_outcome_and_bounded_retry(tmp_path):
    runtime,request,adapter,store,*_=fixture(tmp_path/"vf",mode="verify_fail");result=runtime.execute_approved(request);assert result.receipts[0].status is ExecutionStatus.ROLLBACK_REQUIRED and adapter.calls==1;store.close()
    runtime,request,adapter,store,*_=fixture(tmp_path/"unknown",mode="unknown");result=runtime.execute_approved(request);again=runtime.execute_approved(request);assert result.receipts[0].status is ExecutionStatus.UNKNOWN_OUTCOME and not again.receipts and adapter.calls==1;store.close()
    runtime,request,adapter,store,*_=fixture(tmp_path/"retry",mode="retryable");result=runtime.execute_approved(request);assert result.receipts[0].status is ExecutionStatus.SUCCEEDED_VERIFIED and adapter.calls==2;store.close()

def test_rollback_requires_scope_and_restores(tmp_path):
    runtime,request,adapter,store,*_=fixture(tmp_path);result=runtime.execute_approved(request);path=tmp_path/"execution-sandbox/case/value.txt";assert path.exists()
    plan,rolled=runtime.rollback(request,result.receipts[0]);assert rolled.status is ExecutionStatus.ROLLED_BACK and not path.exists()
    with pytest.raises(ExecutionError):runtime.rollback(replace(request,approval=replace(request.approval,allow_rollback=False)),result.receipts[0])
    store.close()

def test_crash_recovery_verifies_before_deciding_and_never_reexecutes(tmp_path):
    runtime,request,adapter,store,plan,envelope,proposal,descriptor=fixture(tmp_path);key=sha256(repr((plan.id,plan.version,proposal.id,descriptor.id,proposal.parameters)).encode()).hexdigest();execution_id=ExecutionId(uuid5(NAMESPACE_URL,key));payload={"execution_id":str(execution_id),"plan_id":str(plan.id),"plan_version":plan.version,"proposal_id":str(proposal.id),"capability_id":str(descriptor.id),"approval_id":str(request.approval.id)};inv={"capability_id":str(descriptor.id),"proposal_id":str(proposal.id),"parameters":proposal.parameters,"side_effect":proposal.side_effect_class.value,"output_fields":descriptor.output_fields,"correlation_id":None};store.begin(key,payload,inv)
    invocation=CapabilityInvocation(descriptor.id,proposal.id,proposal.parameters,key,proposal.side_effect_class,descriptor.output_fields,None,None);adapter.invoke(invocation);calls=adapter.calls;recovered=runtime.recover_incomplete();assert recovered[0].status is ExecutionStatus.SUCCEEDED_VERIFIED and adapter.calls==calls;store.close()

def test_checkpoint_budget_stop_and_circuit_breaker(tmp_path):
    stop=ExecutionStopController();runtime,request,adapter,store,*_=fixture(tmp_path,stop=stop)
    wait=runtime.execute_approved(replace(request,satisfied_checkpoint_ids=()));assert wait.gate_decisions[-1].outcome is GateOutcome.WAIT and adapter.calls==0
    blocked=runtime.execute_approved(replace(request,id=ExecutionRequestId.new(),runtime_budget=RuntimeBudget(max_actions=0,max_write_delete_operations=0)));assert blocked.status is RuntimeResultStatus.EXECUTION_BLOCKED and adapter.calls==0
    stop.stop("operator stop");stopped=runtime.execute_approved(replace(request,id=ExecutionRequestId.new()));assert stopped.stop_reason=="operator stop" and adapter.calls==0
    store.close()

def test_emergency_stop_after_first_verified_step_blocks_second(tmp_path):
    stop=ExecutionStopController();runtime,request,adapter,store,plan,envelope,proposal,descriptor=fixture(tmp_path,stop=stop)
    original_invoke=adapter.invoke
    def invoke_then_stop(invocation):
        value=original_invoke(invocation);stop.stop("operator stop after first");return value
    adapter.invoke=invoke_then_stop
    second_step_id=PlanStepId.new();second_proposal=replace(proposal,id=ActionProposalId.new(),step_id=second_step_id,parameters=(("path","case/second.txt"),("content","second"),("operation","write"),("mode","")))
    second_step=replace(plan.steps[0],id=second_step_id,dependencies=(plan.steps[0].id,),action_proposals=(second_proposal,));second_checkpoint=PlanCheckpoint(PlanCheckpointId.new(),second_step_id,"second review",True,("scope confirmed",));plan=replace(plan,steps=(plan.steps[0],second_step),dependencies=(PlanDependency(plan.steps[0].id,second_step_id),),checkpoints=(*plan.checkpoints,second_checkpoint));planner=ExecutiveService();envelope=planner._envelope(plan);plans=InMemoryPlanRepository();plans.save(plan,None,envelope);runtime.plans=plans
    budget=replace(request.runtime_budget,max_actions=2,max_write_delete_operations=2);hashes=((proposal.id,parameter_hash(proposal)),(second_proposal.id,parameter_hash(second_proposal)));fp=approval_fingerprint(plan.id,plan.version,(proposal.id,second_proposal.id),hashes,RiskLevel.MEDIUM,(SideEffectClass.LOCAL_REVERSIBLE,),budget);approval=replace(request.approval,envelope_id=envelope.id,proposal_ids=(proposal.id,second_proposal.id),parameter_hashes=hashes,budget=budget,fingerprint=fp)
    result=runtime.execute_approved(ExecutionRequest(ExecutionRequestId.new(),plan.id,plan.version,envelope.id,(proposal.id,second_proposal.id),approval,budget,RetryPolicy(1),(plan.checkpoints[0].id,second_checkpoint.id)))
    assert len(result.receipts)==1 and result.stop_reason=="operator stop after first" and adapter.calls==1
    assert not (tmp_path/"execution-sandbox/case/second.txt").exists();store.close()
