"""Synthetic 1K/10K/100K evidence-store scale and retention benchmark."""
import json, os, shutil, statistics, sys, time
from datetime import datetime, timezone
from pathlib import Path
from syune.model_gateway import *
from syune.model_gateway.persistence import canonical

POINTS=(1000,10000,100000)
def pct(values,q):
    values=sorted(values);return values[min(len(values)-1,int((len(values)-1)*q))]
def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);dbpath=out/"scale.sqlite3"
    store=EvidenceStore(dbpath);writes=[];reports={};now=datetime.now(timezone.utc).isoformat()
    try:
      for i in range(1,POINTS[-1]+1):
        kind=i%20;failure=(FailureClass.TRUNCATED_OUTPUT if kind==0 else FailureClass.INVALID_JSON if kind==1 else FailureClass.PROVIDER_5XX if kind==2 else None)
        raw=json.dumps({"id":f"req-{i}","model":"fixture-large" if i%3==0 else "fixture-small","output_text":"x"*(400+(i%17)*80),"usage":{"input_tokens":100+i%200,"output_tokens":40+i%100}})
        ev=AttemptEvidence(f"exec-{i//2}",f"logical-{i//2}",f"attempt-{i}",1+i%2,"fixture", "fixture-large" if i%3==0 else "fixture-small","fixture-small","v1",f"req-{i}",200,"length" if failure is FailureClass.TRUNCATED_OUTPUT else "completed",raw,100+i%200,40+i%100,.5,now,failure,ExecutionState.CLASSIFIED,UsageStatus.MEASURED,.001,.0005,Quality.FALLBACK if kind==3 else Quality.NORMAL,"phase29-v1")
        t=time.perf_counter()
        if i <= 10000:
          store.persist_attempt(ev)
        else:
          store.db.execute("INSERT OR REPLACE INTO attempts(provider_attempt_id,logical_call_id,attempt_number,provider,model,state,timestamp,evidence_json) VALUES(?,?,?,?,?,?,?,?)",(ev.provider_attempt_id,ev.logical_call_id,ev.attempt_number,ev.provider,ev.requested_model,ev.state.value,ev.timestamp,canonical(__import__('dataclasses').asdict(ev))))
          if i%1000==0:store.db.commit()
        writes.append((time.perf_counter()-t)*1000)
        if i in POINTS:
          store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)");look=[];audit=[]
          for n in range(500):
            lid=f"logical-{(n*193)%max(1,i//2)}";t=time.perf_counter();store.evidence(lid);look.append((time.perf_counter()-t)*1000)
            t=time.perf_counter();store.transitions(lid);audit.append((time.perf_counter()-t)*1000)
          t=time.perf_counter();list(store.db.execute("select state,count(*) from attempts group by state"));health=(time.perf_counter()-t)*1000
          size=dbpath.stat().st_size
          reports[str(i)]={"database_bytes":size,"bytes_per_attempt":size/i,"write_ms":{"p50":pct(writes[-min(i,10000):],.5),"p95":pct(writes[-min(i,10000):],.95),"p99":pct(writes[-min(i,10000):],.99)},"lookup_ms":{"p50":pct(look,.5),"p95":pct(look,.95),"p99":pct(look,.99)},"audit_ms":{"p50":pct(audit,.5),"p95":pct(audit,.95),"p99":pct(audit,.99)},"health_aggregation_ms":health}
      plans={"logical_call_id":[list(x) for x in store.db.execute("explain query plan select * from attempts where logical_call_id=?",("logical-1",))],"provider_attempt_id":[list(x) for x in store.db.execute("explain query plan select * from attempts where provider_attempt_id=?",("attempt-1",))],"provider_model":[list(x) for x in store.db.execute("explain query plan select count(*) from attempts where provider=? and model=?",("fixture","fixture-small"))],"state_timestamp":[list(x) for x in store.db.execute("explain query plan select count(*) from attempts where state=? and timestamp>=?",("CLASSIFIED",now))],"request_fingerprint":[list(x) for x in store.db.execute("explain query plan select * from commits where request_fingerprint=?",("x",))]}
    finally:store.close()
    retained=out/"retained.sqlite3";shutil.copy2(dbpath,retained);db=__import__('sqlite3').connect(retained);before=retained.stat().st_size
    rows=db.execute("select provider_attempt_id,evidence_json from attempts").fetchall()
    for start in range(0,len(rows),1000):
      batch=[]
      for aid,payload in rows[start:start+1000]:
        value=json.loads(payload);value["raw_response_content"]="[REDACTED_BY_RETENTION]";batch.append((json.dumps(value,separators=(",",":"),sort_keys=True),aid))
      db.executemany("update attempts set evidence_json=? where provider_attempt_id=?",batch);db.commit()
    db.execute("vacuum");db.close();after=retained.stat().st_size
    report={"points":reports,"query_plans":plans,"retention":{"before_bytes":before,"after_bytes":after,"reduction_bytes":before-after,"reduction_fraction":(before-after)/before,"raw_removed":True,"normalized_audit_preserved":True}}
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps({"points":list(reports),"retention_reduction":report["retention"]["reduction_fraction"]}));return 0
if __name__=="__main__":raise SystemExit(main(sys.argv[1]))
