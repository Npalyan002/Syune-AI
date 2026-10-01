"""True subprocess crash/restart matrix for the Phase 29 gateway."""
import json, os, subprocess, sys
from pathlib import Path
from syune.model_gateway import *

SCHEMA={"type":"object","additionalProperties":False,"properties":{"status":{"type":"string","enum":["OK"]}},"required":["status"]}
STAGES=("before_budget_reservation","after_budget_reservation","before_provider_request","after_provider_response","after_raw_persistence","after_parsing","after_semantic_commit","after_checkpoint_write")

class FileAdapter:
    name="fixture";is_local=True
    def __init__(self,counter):self.counter=counter
    def model_metadata(self,model):return ModelMetadata(self.name,model,"v1",ModelCapabilities(frozenset({Capability.TEXT_GENERATION,Capability.STRUCTURED_OUTPUT,Capability.NATIVE_JSON_SCHEMA,Capability.USAGE_TELEMETRY,Capability.PROVIDER_REQUEST_ID}),1000,1000),1,1)
    def capabilities(self,model):return self.model_metadata(model).capabilities
    def health(self,model):return HealthStatus.HEALTHY
    def execute(self,call):
        n=int(self.counter.read_text() if self.counter.exists() else "0")+1;self.counter.write_text(str(n))
        body=json.dumps({"id":f"fixture-{n}","model":"m1","output_text":"{\"status\":\"OK\"}"})
        return RawProviderResponse(200,body,f"fixture-{n}","m1","v1","completed",input_tokens=10,output_tokens=5,latency_ms=1,sanitized_metadata={"response_text":"{\"status\":\"OK\"}"})

def child(root,stage):
    root=Path(root);store=EvidenceStore(root/"gateway.sqlite3")
    def hook(name):
        if stage==name: os._exit(91)
    gateway=ModelGateway({"fixture":FileAdapter(root/"provider_calls.txt")},store,routes=(("fixture","m1"),),stage_hook=hook)
    req=ModelExecutionRequest("crash-call","crash fixture",({"role":"user","content":"return OK"},),structured_output_schema=SCHEMA,preferred_model="m1",exact_model=True,max_output_tokens=32,retry_policy=RetryPolicy(max_attempts=1),budget_limits=(BudgetLimit("experiment","crash",max_calls=20,max_input_tokens=10000,max_output_tokens=1000,max_cost_usd=1),))
    result=gateway.execute(req)
    if result.committed:
        side=root/"side_effect.txt"
        if not side.exists():side.write_text(result.semantic_commit_id)
    store.close();return 0

def parent(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[]
    for stage in STAGES:
        root=out/stage;root.mkdir(exist_ok=True)
        first=subprocess.run([sys.executable,__file__,"--child",str(root),stage])
        second=subprocess.run([sys.executable,__file__,"--child",str(root),"NONE"])
        store=EvidenceStore(root/"gateway.sqlite3")
        commits=store.db.execute("select count(*) from commits").fetchone()[0]
        reservations=store.db.execute("select count(*),sum(cost_usd) from budget_reservations").fetchone()
        transitions=store.transitions("crash-call");evidence=store.evidence("crash-call");store.close()
        rows.append({"stage":stage,"crash_exit":first.returncode,"resume_exit":second.returncode,
            "provider_calls":int((root/"provider_calls.txt").read_text()) if (root/"provider_calls.txt").exists() else 0,
            "commits":commits,"side_effects":int((root/"side_effect.txt").exists()),"attempt_evidence":len(evidence),
            "budget_reservations":reservations[0],"reserved_cost_usd":reservations[1] or 0,
            "remote_ambiguity":"REMOTE_COMPLETION_AMBIGUOUS" in transitions,"transitions":transitions,
            "passed":first.returncode==91 and second.returncode==0 and commits==1 and (root/"side_effect.txt").exists()})
    report={"boundaries":rows,"passed":sum(x["passed"] for x in rows),"failed":sum(not x["passed"] for x in rows),
        "duplicate_remote_attempt_exposure":sum(max(0,x["provider_calls"]-1) for x in rows)}
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps({"passed":report["passed"],"failed":report["failed"]}));return int(report["failed"]>0)

if __name__=="__main__":
    raise SystemExit(child(sys.argv[2],sys.argv[3]) if sys.argv[1]=="--child" else parent(sys.argv[1]))
