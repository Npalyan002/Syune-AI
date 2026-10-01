"""Deterministic before/after overhead for the P0 transaction boundary."""
import json, statistics, sys, time
from pathlib import Path
from syune.model_gateway import *
class Adapter:
 name="fixture";is_local=True
 def model_metadata(self,m):return ModelMetadata(self.name,m,"v1",ModelCapabilities(frozenset({Capability.TEXT_GENERATION,Capability.STRUCTURED_OUTPUT}),1000,1000),1,1)
 def capabilities(self,m):return self.model_metadata(m).capabilities
 def health(self,m):return HealthStatus.HEALTHY
 def execute(self,c):
  text='{"action":"PROMOTE"}';return RawProviderResponse(200,json.dumps({"id":c.provider_attempt_id,"model":"m1","output_text":text}),c.provider_attempt_id,"m1","v1","completed",input_tokens=10,output_tokens=5,latency_ms=.2,sanitized_metadata={"response_text":text})
def pct(v,q):v=sorted(v);return v[min(len(v)-1,int((len(v)-1)*q))]
def main(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);store=EvidenceStore(out/"gateway.db");g=ModelGateway({"fixture":Adapter()},store,routes=(("fixture","m1"),));ledger=CognitiveTransactionLedger(out/"cognitive.db");ledger.db.execute("create table effects(k text primary key,v text)");legacy=[];migrated=[]
 for i in range(200):
  t=time.perf_counter();value={"action":"PROMOTE"};json.dumps(value);legacy.append((time.perf_counter()-t)*1000)
  schema={"type":"object","additionalProperties":False,"properties":{"action":{"type":"string","enum":["PROMOTE"]}},"required":["action"]};req=ModelExecutionRequest(f"perf:{i}","Synthetic verification",({"role":"user","content":"promote"},),call_role=CallRole.VERIFICATION,structured_output_schema=schema,preferred_model="m1",exact_model=True,principal="perf",data_policy=DataPolicy(local_only=True),retry_policy=RetryPolicy(max_attempts=1));op=CognitiveOperation(f"perf:{i}","verification","perf",req.purpose,(),req)
  t=time.perf_counter();GatewayCognitiveTransactionService(g,ledger).execute(op,lambda db,v,i=i:(db.execute("insert into effects values(?,?)",(str(i),v["action"])),{"k":i})[1]);migrated.append((time.perf_counter()-t)*1000)
 report={"samples":200,"legacy_contract_ms":{"p50":statistics.median(legacy),"p95":pct(legacy,.95)},"gateway_transaction_ms":{"p50":statistics.median(migrated),"p95":pct(migrated,.95)},"gateway_added_ms":{"p50":statistics.median(migrated)-statistics.median(legacy),"p95":pct(migrated,.95)-pct(legacy,.95)},"provider_latency_ms":.2,"input_tokens":g.metrics.counts["input_tokens"],"output_tokens":g.metrics.counts["output_tokens"],"cost_usd":g.metrics.counts["cost_microusd"]/1e6};(out/"report.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report));ledger.close();store.close()
if __name__=="__main__":main(sys.argv[1])
