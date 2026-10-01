from contextlib import ExitStack
from dataclasses import replace
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from scenario import pipeline, bind_sandbox
from faults import InjectedCrash, crash_after, crash_before
from test_supervised_execution import fixture
from syune.evals.invariants import audit
from syune.evals.model import Health
from syune.executive import *
from syune.memory import SQLiteMemoryRepository
from syune.retrieval import InvertedSeedIndex, RetrievalService, RecallRequest, RecallCue


@pytest.mark.parametrize('point', ['after_gate','after_effect','before_verification','after_verification','after_commit'])
def test_crash_boundaries_reopen_reconcile_without_side_effect_repetition(tmp_path, point):
    runtime, request, adapter, store, plan, envelope, proposal, descriptor = fixture(tmp_path)
    if point == 'after_gate': store.begin = crash_after(store.begin)
    if point == 'after_effect': adapter.invoke = crash_after(adapter.invoke)
    if point == 'before_verification': runtime.verifier.verify = crash_before(runtime.verifier.verify)
    if point == 'after_verification': store.finish = crash_before(store.finish)
    if point == 'after_commit': store.finish = crash_after(store.finish)
    with pytest.raises(InjectedCrash): runtime.execute_approved(request)
    effects = int((adapter.root/'case/value.txt').exists())
    store.close()
    reopened = SQLiteExecutionRepository(tmp_path/'execution.sqlite3')
    fresh_adapter = LocalSandboxFileAdapter(adapter.root)
    capabilities = CapabilityRegistry(); capabilities.register(descriptor, fresh_adapter)
    recovered_runtime = SupervisedExecutiveService(runtime.plans, capabilities, reopened)
    try:
        recovered = recovered_runtime.recover_incomplete()
        replay = recovered_runtime.execute_approved(request)
        assert fresh_adapter.calls == 0
        assert int((adapter.root/'case/value.txt').exists()) == effects
        if point == 'after_gate':
            assert recovered[0].status is ExecutionStatus.UNKNOWN_OUTCOME
            assert replay.status is RuntimeResultStatus.EXECUTION_BLOCKED
        else:
            assert replay.status is RuntimeResultStatus.COMPLETED_VERIFIED
    finally: reopened.close()


@pytest.mark.parametrize('corruption', ['memory_json','missing_entity','source_hash','perception_run','execution_record','overlay_bound'])
def test_corruption_explicit_diagnostic_preserves_unaffected_rows(tmp_path, corruption):
    with ExitStack() as stack:
        c = bind_sandbox(pipeline(tmp_path, stack)); stack.callback(c['execution_store'].close)
        c['runtime'].execute_approved(c['execution_request'])
        unaffected = c['memory'].get(c['observations'][1].id)
        if corruption == 'memory_json':
            c['memory']._db.execute("UPDATE entities SET payload='{' WHERE id_value=?",(str(c['observations'][0].id),)); c['memory']._db.commit()
        elif corruption == 'missing_entity':
            c['memory']._db.execute('DELETE FROM entities WHERE id_value=?',(str(c['observations'][0].id),)); c['memory']._db.commit()
        elif corruption == 'source_hash':
            c['registry']._db.execute("UPDATE revisions SET sha256='invalid'"); c['registry']._db.commit()
            with pytest.raises(ValueError): c['registry'].status(c['studied'].status.revision_id)
        elif corruption == 'perception_run':
            c['registry']._db.execute("UPDATE perception_runs SET status='INVALID'"); c['registry']._db.commit()
            with pytest.raises(ValueError): c['registry'].perception_summary(c['studied'].status.revision_id)
        elif corruption == 'execution_record':
            c['execution_store'].db.execute("UPDATE executions SET payload='{}'"); c['execution_store'].db.commit()
            with pytest.raises(ValueError): c['execution_store'].state(c['execution_store'].db.execute('SELECT idempotency_key FROM executions').fetchone()[0])
        elif corruption == 'overlay_bound':
            c['learning']._db.execute("INSERT INTO overlay VALUES ('test','ENTITY',9,0,0,0,1,NULL,'1')"); c['learning']._db.commit()
        checked = audit(c['memory'],c['registry'],c['learning'],(c['execution_plan'],),c['execution_store'])
        assert checked.health is Health.UNHEALTHY and checked.issues
        assert c['memory'].get(unaffected.id) == unaffected


def test_atomic_idempotency_claim_and_schema_compatibility(tmp_path):
    runtime, request, adapter, store, *_ = fixture(tmp_path)
    try:
        runtime.execute_approved(request)
        key = store.db.execute('SELECT idempotency_key FROM executions').fetchone()[0]
        row = store.row(key)
        with pytest.raises(ValueError): store.begin(key,row[1],row[2])
        assert adapter.calls == 1 and store.row(key) == row
        assert store.db.execute('PRAGMA user_version').fetchone()[0] == 1
        store.db.execute('PRAGMA user_version=99'); store.db.commit()
    finally: store.close()
    with pytest.raises(ValueError,match='schema'): SQLiteExecutionRepository(tmp_path/'execution.sqlite3')


def test_independent_connection_concurrent_reads_are_deterministic(tmp_path):
    with ExitStack() as stack:
        c = pipeline(tmp_path, stack)
        expected = tuple(x.entity_id for x in c['recalled'].candidates)
        def read(_):
            with SQLiteMemoryRepository(tmp_path/'memory.sqlite3') as memory:
                index = InvertedSeedIndex(memory); index.rebuild()
                service = RetrievalService(memory,index)
                return [tuple(x.entity_id for x in service.recall(RecallRequest(RecallCue(text='Amber'))).candidates) for _ in range(20)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(read,range(8)))
        assert all(value == expected for group in results for value in group)
        assert c['memory'].iter_entities() == c['canonical']
