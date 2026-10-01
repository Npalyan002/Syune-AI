from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import pytest
from scenario import pipeline
from syune.core import *
from syune.executive import *
from test_supervised_execution import fixture


def test_fresh_process_restart_semantic_determinism(tmp_path):
    with ExitStack() as stack: pipeline(tmp_path,stack)
    code='''
from pathlib import Path
import sys
from hashlib import sha256
from uuid import UUID
from syune.core import CognitiveRequestId
from syune.memory import SQLiteMemoryRepository
from syune.retrieval import InvertedSeedIndex,RetrievalService
from syune.cognition import CognitiveRequest,CognitiveService
with SQLiteMemoryRepository(Path(sys.argv[1])) as memory:
    index=InvertedSeedIndex(memory);index.rebuild()
    result=CognitiveService(memory,RetrievalService(memory,index)).process(CognitiveRequest(CognitiveRequestId(UUID(int=99)),text='Amber'))
    semantic=(result.status,result.context,result.inferences,result.assessment,result.responses)
    print(sha256(repr(semantic).encode()).hexdigest())
'''
    command=[sys.executable,'-c',code,str(tmp_path/'memory.sqlite3')]
    first=subprocess.run(command,capture_output=True,text=True,check=True,timeout=30).stdout.strip()
    second=subprocess.run(command,capture_output=True,text=True,check=True,timeout=30).stdout.strip()
    assert len(first)==64 and first==second


@pytest.mark.parametrize('mutation',['params','target','risk','scope','budget','expiry','revoked'])
def test_exact_approval_scope_blocks_fresh_invocations(tmp_path,mutation):
    runtime,request,adapter,store,plan,envelope,proposal,descriptor=fixture(tmp_path)
    try:
        if mutation=='params':request=replace(request,parameter_overrides=((proposal.id,(('path','case/other.txt'),('content','amber'),('operation','write'),('mode',''))),))
        if mutation in ('target','risk'):
            modified=replace(proposal,target_descriptor='widened target') if mutation=='target' else replace(proposal,estimated_risk=RiskLevel.HIGH)
            modified_plan=replace(plan,steps=(replace(plan.steps[0],action_proposals=(modified,)),))
            plans=InMemoryPlanRepository();plans.save(modified_plan,None,envelope);runtime.plans=plans
        if mutation=='scope':
            other=ActionProposalId.new();request=replace(request,approval=replace(request.approval,proposal_ids=(other,),parameter_hashes=((other,'0'*64),)))
        if mutation=='budget':request=replace(request,runtime_budget=replace(request.runtime_budget,max_actions=10))
        if mutation=='expiry':
            from datetime import timedelta
            request=replace(request,approval=replace(request.approval,expires_at=request.approval.issued_at+timedelta(seconds=1)))
        if mutation=='revoked':request=replace(request,approval=replace(request.approval,status=RuntimeApprovalStatus.REVOKED))
        result=runtime.execute_approved(request)
        assert result.status is RuntimeResultStatus.EXECUTION_BLOCKED and adapter.calls==0
    finally:store.close()
