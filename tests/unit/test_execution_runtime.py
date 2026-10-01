from dataclasses import replace
from datetime import datetime,timedelta,timezone
import pytest
from syune.core import *
from syune.executive import *
def test_registry_metadata_duplicate_and_degraded_gate(tmp_path):
    cid=CapabilityId.new();d=RuntimeCapabilityDescriptor(cid,"safe",ActionType.UPDATE,"1",CapabilityStatus.AVAILABLE,CapabilityHealth.HEALTHY,SideEffectClass.LOCAL_REVERSIBLE,("path",),("path",),IdempotencyMode.REQUIRED,RollbackMode.SUPPORTED,VerificationMode.READ_BACK,ApprovalKind.HUMAN,RiskLevel.LOW,"sandbox","adapter","1","test");r=CapabilityRegistry();a=LocalSandboxFileAdapter(tmp_path);r.register(d,a)
    with pytest.raises(ValueError):r.register(d,a)
    assert r.resolve(cid)[0].rollback_mode is RollbackMode.SUPPORTED
def test_runtime_budget_retry_and_no_wildcard_approval():
    with pytest.raises(ValueError):RuntimeBudget(max_actions=-1)
    with pytest.raises(ValueError):RetryPolicy(max_attempts=4)
    now=datetime.now(timezone.utc)
    with pytest.raises(ValueError):ApprovalToken(ApprovalTokenId.new(),ApprovalSource.TEST,RuntimeApprovalStatus.VALID,PlanId.new(),1,ApprovalEnvelopeId.new(),(),(),RiskLevel.LOW,(SideEffectClass.NONE,),RuntimeBudget(),now,now+timedelta(days=1),"test","x")
