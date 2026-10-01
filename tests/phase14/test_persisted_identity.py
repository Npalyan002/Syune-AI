from contextlib import ExitStack
import pytest
from scenario import pipeline,bind_sandbox
from syune.evals.invariants import audit
from syune.evals.model import Health


def test_changed_execution_key_rejected_before_any_repeat(tmp_path):
    with ExitStack() as stack:
        c=bind_sandbox(pipeline(tmp_path,stack));stack.callback(c['execution_store'].close)
        c['runtime'].execute_approved(c['execution_request'])
        c['execution_store'].db.execute("UPDATE executions SET idempotency_key=?",('f'*64,));c['execution_store'].db.commit()
        with pytest.raises(ValueError):c['execution_store'].row('f'*64)
        with pytest.raises(ValueError):c['runtime'].execute_approved(c['execution_request'])
        assert audit(c['memory'],c['registry'],c['learning'],(c['execution_plan'],),c['execution_store']).health is Health.UNHEALTHY
        assert c['adapter'].calls==1


def test_association_row_identity_corruption_is_explicit(tmp_path):
    with ExitStack() as stack:
        c=pipeline(tmp_path,stack)
        c['memory']._db.execute("UPDATE associations SET source_value=?",(str(c['observations'][1].id),));c['memory']._db.commit()
        with pytest.raises(ValueError):c['memory'].associations_for(c['observations'][1].id)
        assert audit(c['memory'],c['registry']).health is Health.UNHEALTHY
