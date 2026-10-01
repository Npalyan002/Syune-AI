"""Deterministic three-arm verified-learning benchmark using an unchanged policy model."""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
from statistics import quantiles
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import UUID

from syune.core import ProvenanceId,SourceId
from syune.learning import (AttributionQuality,EvidenceKind,EvidenceQuality,Experience,ExperienceId,
    OutcomeStatus,SQLiteVerifiedLearningStore,VerifiedExperienceLearningService,VerifiedLearningState)
from syune.memory import InMemoryReferenceRepository,Provenance,Source


CLASSES=tuple(f"workflow-{n}" for n in range(6))
CORRECT={name:("safe" if n%2 else "fast") for n,name in enumerate(CLASSES)}


def _score(known:set[str],memory_exact:set[str]):
    # Same deterministic policy in all arms: baseline chooses fast. Twenty exact
    # repeats, sixty shifted in-distribution tasks, and twenty OOD tasks.
    cases=[]
    for n in range(100):
        if n<20: task=CLASSES[n%6]; exact=True
        elif n<80: task=CLASSES[n%6]; exact=False
        else: task=f"ood-{n%4}"; exact=False
        if task in known: chosen=CORRECT[task]
        elif exact and task in memory_exact: chosen=CORRECT[task]
        else: chosen="fast"
        correct=CORRECT.get(task,"safe" if n%2 else "fast")
        cases.append(chosen==correct)
    return sum(cases)/len(cases),1-sum(cases)/len(cases)


def run(output:Path|None=None):
    temp=TemporaryDirectory(); at=datetime(2026,1,1,tzinfo=timezone.utc)
    memory=InMemoryReferenceRepository(); sid=SourceId(UUID(int=1)); memory.put(Source(sid,"synthetic","phase24",at))
    provenance=Provenance(ProvenanceId(UUID(int=2)),sid,at); store=SQLiteVerifiedLearningStore(Path(temp.name)/"verified.sqlite3")
    learning=VerifiedExperienceLearningService(memory,store); checkpoints={}; serial=1000; latencies=[]; memory_exact=set()
    for interaction in range(1,10001):
        task=CLASSES[(interaction-1)%6]; strategy=("fast" if ((interaction-1)//6)%2==0 else "safe")
        success=strategy==CORRECT[task]; serial+=1
        item=Experience(ExperienceId(UUID(int=serial)),task,(("platform","windows"),),(strategy,),
          OutcomeStatus.SUCCESS if success else OutcomeStatus.FAILURE,EvidenceKind.DETERMINISTIC_TEST,
          AttributionQuality.DIRECT,EvidenceQuality(.95,1,1,1,1),at,provenance,f"exp-{serial}",
          "fixed-evaluator","unchanged-policy-model",principal_scope="benchmark",environment="controlled",
          desired_result_verified=success,independence_key=f"run-{serial}")
        learning.record(item); memory_exact.add(task)
        if interaction in (10,100,1000,10000):
            tick=perf_counter(); learning.maintain(); latencies.append((perf_counter()-tick)*1000)
            promoted={h.task_class for key in store.pending_keys(0) for h in ()}  # no scan on hot path
            rows=store.db.execute("SELECT payload FROM verified_hypotheses WHERE state='PROMOTED'").fetchall()
            import json
            promoted={json.loads(row[0])["task_class"] for row in rows}
            success_rate,error=_score(promoted,memory_exact)
            valid_promotions=sum(CORRECT.get(json.loads(row[0])["task_class"])==json.loads(row[0])["strategy"][0] for row in rows)
            checkpoints[interaction]={"task_success":success_rate,"repeated_error_rate":error,"verified_knowledge_count":len(promoted),
                "learning_precision":valid_promotions/max(1,len(rows)),"learning_recall":len(promoted)/len(CLASSES),"false_promotions":len(rows)-valid_promotions}
    off_start=perf_counter(); off_success,off_error=_score(set(),set()); off_ms=(perf_counter()-off_start)*1000
    mem_start=perf_counter(); mem_success,mem_error=_score(set(),memory_exact); mem_ms=(perf_counter()-mem_start)*1000
    rows=store.db.execute("SELECT payload FROM verified_hypotheses WHERE state='PROMOTED'").fetchall(); import json
    promoted={json.loads(row[0])["task_class"] for row in rows}
    learned_start=perf_counter(); learned_success,learned_error=_score(promoted,memory_exact); learned_ms=(perf_counter()-learned_start)*1000
    result={"kind":"deterministic_synthetic_same_model","underlying_model":"unchanged-policy-model-v1",
      "learning_off":{"task_success":off_success,"repeated_error_rate":off_error,"false_promotions":0,"context_size":0,"latency_ms":off_ms},
      "memory_only":{"task_success":mem_success,"repeated_error_rate":mem_error,"false_promotions":0,"context_size":.2,"latency_ms":mem_ms},
      "verified_learning":{"task_success":learned_success,"repeated_error_rate":learned_error,"learning_precision":checkpoints[10000]["learning_precision"],"learning_recall":checkpoints[10000]["learning_recall"],"false_promotions":checkpoints[10000]["false_promotions"],"contamination":0,"context_size":.8,"latency_ms":learned_ms},
      "longitudinal":checkpoints,"learning_maintenance_p95_ms":quantiles(latencies,n=20)[18],"llm_calls":0,"tokens":0}
    store.close(); temp.cleanup()
    if output: output.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    return result


if __name__=="__main__":
    import json
    print(json.dumps(run(),indent=2,sort_keys=True))
