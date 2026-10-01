"""Study, Learning, gate and already-studied full pipeline latency observations."""
from contextlib import ExitStack
from pathlib import Path
from time import perf_counter
import json
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/phase14'));sys.path.insert(0,str(ROOT/'scripts'))
from scenario import pipeline,bind_sandbox
from benchmark_phase07 import run as learning_benchmark
from benchmark_phase14 import resources
from syune.evals.metrics import percentiles
from syune.executive import RuntimeResultStatus
from syune.study import StudyService

samples={};before=resources()
with tempfile.TemporaryDirectory(dir=ROOT/'.syune/phase14-runs') as directory:
    for n in range(20):
        with ExitStack() as stack:
            c=pipeline(Path(directory)/str(n),stack)
            tick=perf_counter();StudyService(c['registry'],c['memory'],c['root']).study(c['source'])
            samples.setdefault('Study_duplicate',[]).append((perf_counter()-tick)*1000)
            c=bind_sandbox(c);stack.callback(c['execution_store'].close)
            tick=perf_counter();result=c['runtime'].execute_approved(c['execution_request']);execute_ms=(perf_counter()-tick)*1000
            assert result.status is RuntimeResultStatus.COMPLETED_VERIFIED
            cognitive=dict(c['cognitive'].timings_ms)['total']
            recall=dict(c['recalled'].timings_ms)['total']
            council=c['council'].diagnostics.total_ms
            planning=dict(c['planned'].diagnostics.timings_ms)['total']
            times=dict(result.timings_ms)
            for name,value in {'Retrieval':recall,'Cognition':cognitive,'Council':council,'Planning':planning,
                'Execution_gate':times['gate_evaluation'],'Capability':times['adapter_invocation'],
                'Execution_overhead':execute_ms-times['adapter_invocation'],'Verification':times['verification'],
                'E2E_service_sum':recall+cognitive+council+planning+execute_ms}.items():samples.setdefault(name,[]).append(value)
    learning=[learning_benchmark(n,repeats=3) for n in (100,1000,10000)]
result={'samples':{k:percentiles(v) for k,v in samples.items()},'learning':learning,'before':before,'after':resources(),
    'limitations':['E2E_service_sum excludes host review delay and fixture setup','synthetic data; empirical percentiles from small sample sizes']}
(ROOT/'.syune/phase14-subsystems.json').write_text(json.dumps(result,indent=2))
print('subsystem measurements complete')
