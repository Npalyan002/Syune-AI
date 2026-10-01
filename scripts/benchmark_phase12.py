"""Phase 12 deterministic planner benchmark scenarios."""
import json,math,statistics
from time import perf_counter
from syune.core import ConstraintId,ExecutiveRequestId,GoalId
from syune.executive import *
def percentile(values,q):return sorted(values)[min(len(values)-1,math.ceil(len(values)*q)-1)]
def build(name):
    criteria=("design reviewed",)
    constraints=()
    text={"simple_linear":"prepare a safe migration","dependency_dag":"prepare a dependency migration","blocked_hard":"prepare a safe migration","high_risk":"delete external production data","insufficient_context":"prepare an uncertain migration","council_disagreement":"prepare a disputed migration","large_bounded":"prepare a bounded migration"}[name]
    if name=="blocked_hard":constraints=(Constraint(ConstraintId.new(),ConstraintKind.HARD,ConstraintSource.TEST if hasattr(ConstraintSource,'TEST') else ConstraintSource.USER,"backup","available",False),)
    if name=="large_bounded":constraints=tuple(Constraint(ConstraintId.new(),ConstraintKind.SOFT,ConstraintSource.USER,f"constraint-{n}","preserve",True) for n in range(32))
    return ExecutiveRequest(ExecutiveRequestId.new(),Goal(GoalId.new(),text,criteria,source=GoalSource.TEST),constraints=constraints)
def run(repeats=20):
    rows=[]
    for name in ("simple_linear","dependency_dag","blocked_hard","high_risk","insufficient_context","council_disagreement","large_bounded"):
        times=[];last=None
        for _ in range(repeats):
            tick=perf_counter();last=ExecutiveService().plan(build(name));times.append((perf_counter()-tick)*1000)
        rows.append({"scenario":name,"p50_ms":statistics.median(times),"p95_ms":percentile(times,.95),"status":last.status.value,"steps":len(last.plan.steps) if last.plan else 0,"constraints":dict(last.diagnostics.counts).get("constraints",0)})
    return rows
if __name__=="__main__":print(json.dumps(run(),indent=2))
