from contextlib import ExitStack
from dataclasses import replace
from hashlib import sha256
from scenario import pipeline, bind_sandbox
from syune.evals.invariants import audit
from syune.evals.model import Health
from syune.executive import RuntimeResultStatus


def test_golden_path_trace_provenance_integrity_and_no_implicit_learning(tmp_path):
    with ExitStack() as stack:
        c = bind_sandbox(pipeline(tmp_path, stack))
        stack.callback(c['execution_store'].close)
        assert c['planned'].validation.valid and c['planned'].context.entity_ids
        result = c['runtime'].execute_approved(c['execution_request'])
        assert result.status is RuntimeResultStatus.COMPLETED_VERIFIED
        receipt = result.receipts[0]
        assert receipt.proposal_id == c['proposal'].id
        assert c['proposal'].step_id == c['execution_plan'].steps[0].id
        assert c['execution_plan'].goal_id == c['goal'].id
        assert set(c['proposal'].entity_ids) <= set(c['council'].evidence_map.union_entity_ids) | set(c['cognitive'].context.entity_ids)
        assert c['studied'].status.sha256 == sha256(c['source'].read_bytes()).hexdigest()
        checked = audit(c['memory'], c['registry'], c['learning'], (c['execution_plan'],), c['execution_store'])
        assert checked.health is Health.HEALTHY, checked.issues
        assert c['memory'].iter_entities() == c['canonical']
        assert c['learning'].count_signals() == 0 and c['learning'].snapshot() == ()
        replay = c['runtime'].execute_approved(c['execution_request'])
        assert replay.receipts[0].idempotent_replay and c['adapter'].calls == 1
        assert c['execution_request'].correlation_id == c['goal'].correlation_id == c['trace']


def test_failure_path_exact_gate_no_side_effect_and_recovery(tmp_path):
    with ExitStack() as stack:
        c = bind_sandbox(pipeline(tmp_path, stack))
        stack.callback(c['execution_store'].close)
        request = c['execution_request']
        bad = replace(request, approval=replace(request.approval, plan_version=1))
        blocked = c['runtime'].execute_approved(bad)
        assert blocked.status is RuntimeResultStatus.EXECUTION_BLOCKED
        assert blocked.gate_decisions[0].rule_ids == ('APR-004',)
        assert c['adapter'].calls == 0 and not (c['adapter'].root/'result.txt').exists()
        assert c['runtime'].execute_approved(request).status is RuntimeResultStatus.COMPLETED_VERIFIED
        assert c['memory'].iter_entities() == c['canonical']
