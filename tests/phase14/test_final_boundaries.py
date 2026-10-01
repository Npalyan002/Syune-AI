from contextlib import ExitStack
from dataclasses import replace
import pytest
from scenario import pipeline
from test_supervised_execution import fixture
from syune.core import *
from syune.learning import *
from syune.executive import *


def test_learning_rollback_cannot_erase_later_update(tmp_path):
    with ExitStack() as stack:
        c=pipeline(tmp_path,stack);service=LearningService(c['memory'],c['learning']);entity=c['observations'][0]
        batches=[]
        for n in range(2):
            service.record(LearningSignal(LearningSignalId.new(),LearningSignalKind.POSITIVE_OUTCOME,utc_now(),
                (LearningTarget(entity.id),),LearningSource.SYSTEM_TEST,str(n),entity.provenance.id))
            batches.append(service.consolidate_once().batch)
        before=c['learning'].snapshot()
        with pytest.raises(LearningError):service.rollback(batches[0].id)
        assert c['learning'].snapshot()==before
        service.rollback(batches[1].id);service.rollback(batches[0].id)
        assert c['learning'].snapshot()==() and c['memory'].iter_entities()==c['canonical']


@pytest.mark.parametrize('kwargs',[{'max_actions':65},{'max_retries':4},{'max_write_delete_operations':65},{'max_wall_time_ms':60001}])
def test_runtime_global_ceilings(kwargs):
    with pytest.raises(ValueError):RuntimeBudget(**kwargs)


def test_blocked_plan_cannot_be_made_executable_by_token(tmp_path):
    runtime,request,adapter,store,plan,envelope,*_=fixture(tmp_path)
    try:
        plans=InMemoryPlanRepository();plans.save(replace(plan,status=PlanStatus.BLOCKED),None,envelope);runtime.plans=plans
        with pytest.raises(ExecutionError):runtime.execute_approved(request)
        assert adapter.calls==0
    finally:store.close()
