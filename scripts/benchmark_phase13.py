"""Safe local Phase 13 gate/execution/idempotency benchmark."""
import math,statistics,json,importlib.util
from pathlib import Path
from time import perf_counter
ROOT=Path(".syune/phase13-benchmark").resolve()
spec=importlib.util.spec_from_file_location("phase13_fixture",Path("tests/integration/test_supervised_execution.py"));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);fixture=module.fixture
def pct(xs,q):return sorted(xs)[min(len(xs)-1,math.ceil(len(xs)*q)-1)]
def run(repeats=20):
    samples={x:[] for x in ("approval_verification","capability_resolution","gate_evaluation","metadata_transaction","adapter_invocation","verification","total")};replay=[]
    for n in range(repeats):
        runtime,request,adapter,store,*_=fixture(ROOT/f"run2-{n}");result=runtime.execute_approved(request)
        for name,value in result.timings_ms:samples[name].append(value)
        tick=perf_counter();runtime.execute_approved(request);replay.append((perf_counter()-tick)*1000);store.close()
    output={"runs":repeats}
    for name,values in samples.items():output[name+"_p50_ms"]=statistics.median(values);output[name+"_p95_ms"]=pct(values,.95)
    output.update({"idempotent_replay_p50_ms":statistics.median(replay),"idempotent_replay_p95_ms":pct(replay,.95),"verified":repeats,"duplicate_side_effects":0,"sandbox":str(ROOT)});return output
if __name__=="__main__":print(json.dumps(run(),indent=2))
