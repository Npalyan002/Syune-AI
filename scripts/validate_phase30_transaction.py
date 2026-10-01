"""Cross-process gateway-to-cognitive transaction recovery evidence."""
import json, os, sqlite3, subprocess, sys, time
from pathlib import Path
from syune.model_gateway import *

SCHEMA={"type":"object","additionalProperties":False,"properties":{"action":{"type":"string","enum":["PROMOTE"]}},"required":["action"]}
class Adapter:
 name="fixture";is_local=True
 def __init__(self,path):self.path=path
 def model_metadata(self,model):return ModelMetadata(self.name,model,"v1",ModelCapabilities(frozenset({Capability.TEXT_GENERATION,Capability.STRUCTURED_OUTPUT,Capability.NATIVE_JSON_SCHEMA}),1000,1000),1,1)
 def capabilities(self,model):return self.model_metadata(model).capabilities
 def health(self,model):return HealthStatus.HEALTHY
 def execute(self,call):
  n=int(self.path.read_text() if self.path.exists() else "0")+1;self.path.write_text(str(n));text='{"action":"PROMOTE"}'
  return RawProviderResponse(200,json.dumps({"id":f"r{n}","model":"m1","output_text":text}),f"r{n}","m1","v1","completed",input_tokens=10,output_tokens=5,sanitized_metadata={"response_text":text})
def run(root,kill):
 root=Path(root);gs=EvidenceStore(root/"gateway.db");g=ModelGateway({"fixture":Adapter(root/"provider_calls.txt")},gs,routes=(("fixture","m1"),));ledger=CognitiveTransactionLedger(root/"cognitive.db");ledger.db.execute("create table if not exists effects(effect_key text primary key,value text not null)")
 req=ModelExecutionRequest("verified:c1:e1:policy-v2","Verified learning promotion",({"role":"system","content":"Use authorized evidence only."},{"role":"user","content":"Evidence e1 supports promotion."}),call_role=CallRole.VERIFICATION,structured_output_schema=SCHEMA,preferred_model="m1",exact_model=True,principal="agent-1",data_policy=DataPolicy(local_only=True),retry_policy=RetryPolicy(max_attempts=1))
 op=CognitiveOperation("promote:c1","verified_learning","agent-1",req.purpose,("e1",),req)
 def hook(stage):
  if stage==kill:os._exit(93)
 def mutate(db,value):db.execute("insert into effects values('c1',?)",(value["action"],));return {"candidate":"c1","state":value["action"]}
 result=GatewayCognitiveTransactionService(g,ledger).execute(op,mutate,stage_hook=hook);(root/"ack.json").write_text(json.dumps({"tx":result.cognitive_transaction_id,"replayed":result.replayed}));ledger.close();gs.close();return 0
def parent(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[]
 for kill in ("after_gateway_commit","after_cognitive_commit"):
  root=out/kill;root.mkdir(exist_ok=True);start=time.perf_counter();first=subprocess.run([sys.executable,__file__,"--child",str(root),kill]);second=subprocess.run([sys.executable,__file__,"--child",str(root),"NONE"]);elapsed=(time.perf_counter()-start)*1000
  db=sqlite3.connect(root/"cognitive.db");effects=db.execute("select count(*) from effects").fetchone()[0];transactions=db.execute("select count(*) from cognitive_transactions where state='APPLIED'").fetchone()[0];db.close();gs=EvidenceStore(root/"gateway.db");commits=gs.db.execute("select count(*) from commits").fetchone()[0];gs.close()
  rows.append({"boundary":kill,"crash_exit":first.returncode,"resume_exit":second.returncode,"provider_calls":int((root/"provider_calls.txt").read_text()),"gateway_commits":commits,"cognitive_commits":transactions,"cognitive_effects":effects,"resume_replayed":json.loads((root/"ack.json").read_text())["replayed"],"recovery_ms":elapsed,"passed":first.returncode==93 and second.returncode==0 and commits==transactions==effects==1})
 report={"boundaries":rows,"passed":sum(x["passed"] for x in rows),"failed":sum(not x["passed"] for x in rows)};(out/"report.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report));return int(report["failed"]>0)
if __name__=="__main__":raise SystemExit(run(sys.argv[2],sys.argv[3]) if sys.argv[1]=="--child" else parent(sys.argv[1]))
