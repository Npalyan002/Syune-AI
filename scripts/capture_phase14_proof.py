"""Capture synthetic final-output provenance without source bodies or authority tokens."""
from contextlib import ExitStack
from pathlib import Path
import sys,json,tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/phase14'))
from scenario import pipeline,bind_sandbox
from syune.evals.invariants import audit
from dataclasses import asdict,replace
with tempfile.TemporaryDirectory(dir=ROOT/'.syune/phase14-runs') as directory, ExitStack() as stack:
    c=bind_sandbox(pipeline(Path(directory),stack));stack.callback(c['execution_store'].close)
    request=c['execution_request'];blocked=c['runtime'].execute_approved(replace(request,approval=replace(request.approval,plan_version=1)))
    assert c['adapter'].calls==0
    result=c['runtime'].execute_approved(request);receipt=result.receipts[0]
    chain=[]
    for mid in c['proposal'].entity_ids:
        entity=c['memory'].get(mid)
        _,_,run,segment,method=entity.provenance.process_id.split(':',4)
        row=c['registry']._db.execute('SELECT locator,fingerprint FROM perception_segments WHERE segment_id=?',(segment,)).fetchone()
        chain.append(dict(memory_entity_id=str(mid),entity_type=type(entity).__name__,observation_id=str(entity.id),
            provenance_id=str(entity.provenance.id),perception_run_id=run,perceived_segment_id=segment,method=method,
            exact_locator=row[0],segment_fingerprint=row[1],source_id=str(entity.provenance.source_id),
            source_revision_id=str(c['studied'].status.revision_id),source_version_id=str(entity.provenance.source_version_id),
            source_sha256=c['studied'].status.sha256))
    proof=dict(trace_id=c['trace'],receipt_id=str(receipt.id),execution_id=str(receipt.execution_id),receipt_status=receipt.status.value,
        verification=receipt.verification.status.value,proposal_id=str(c['proposal'].id),plan_step_id=str(c['proposal'].step_id),
        plan_id=str(c['execution_plan'].id),plan_version=c['execution_plan'].version,goal_id=str(c['goal'].id),
        cognitive_request_id=str(c['cognitive'].request_id),council_request_id=str(c['council'].request_id),chain=chain,
        audit=asdict(audit(c['memory'],c['registry'],c['learning'],(c['execution_plan'],),c['execution_store'])),
        failure_path=dict(status=blocked.status.value,gate_rules=blocked.gate_decisions[0].rule_ids,side_effects=0),
        explicit_test_host_binding='generic L2 draft -> reviewed sandbox v2; no automatic runtime replanning',learning_signals=c['learning'].count_signals())
    destination=ROOT/'docs/evals';destination.mkdir(exist_ok=True)
    (destination/'phase14_e2e_proof_v1.json').write_text(json.dumps(proof,indent=2))
print('provenance proof captured')
