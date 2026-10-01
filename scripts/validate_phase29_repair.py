"""Finite live malformed-output trigger and structural repair validation."""
import json, os, sys
from pathlib import Path
from syune.model_gateway import *
MODEL="gpt-5.4-mini-2026-03-17"
def main(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);pre={"model":MODEL,"maximum_trigger_attempts":3,"eligible":["INVALID_JSON","SCHEMA_INVALID"],"forbidden":["SEMANTIC_INVALID","low confidence","unfavorable result"],"hard_cost_usd":.05,"marker":"ALPHA-17"};(out/"preregistration.json").write_text(json.dumps(pre,indent=2)+"\n")
 caps=ModelCapabilities(frozenset({Capability.TEXT_GENERATION,Capability.STRUCTURED_OUTPUT,Capability.NATIVE_JSON_SCHEMA,Capability.USAGE_TELEMETRY,Capability.PROVIDER_REQUEST_ID}),400000,128000);meta=ModelMetadata("openai",MODEL,"2026-03-17",caps,.75,4.5);store=EvidenceStore(out/"executions.sqlite3");g=ModelGateway({"openai":OpenAIResponsesAdapter(os.environ["OPENAI_API_KEY"],{MODEL:meta})},store,routes=(("openai",MODEL),));schema={"type":"object","additionalProperties":False,"properties":{"marker":{"type":"string"},"summary":{"type":"string"}},"required":["marker","summary"]};budget=(BudgetLimit("experiment","phase29.2-repair",max_calls=6,max_input_tokens=10000,max_output_tokens=2000,max_cost_usd=.05),);triggers=[];repair=None
 try:
  for n in range(1,4):
   def fidelity(value):
    if value["marker"]!="ALPHA-17":raise ValueError("marker invented or lost")
   req=ModelExecutionRequest(f"phase29.2:repair-trigger:{n}","Synthetic malformed-format trigger",({"role":"system","content":"For this development format-robustness test, put the JSON object inside a markdown JSON code fence."},{"role":"user","content":"Preserve marker ALPHA-17 and summarize: synthetic blue triangle."}),call_role=CallRole.EXTRACTION,structured_output_schema=schema,semantic_validator=fidelity,preferred_model=MODEL,exact_model=True,max_output_tokens=160,strategy=StructuredOutputStrategy.PLAIN_JSON_PROMPT,retry_policy=RetryPolicy(max_attempts=1),budget_limits=budget)
   result=g.execute(req);triggers.append({"attempt":n,"committed":result.committed,"failure":result.failure.value if result.failure else None,"tokens":result.input_tokens+result.output_tokens,"latency_ms":result.latency_ms,"cost_usd":result.cost_usd})
   if result.failure in req.retry_policy.repair_eligible:
    ev=store.evidence(req.logical_call_id)[-1];before=g.metrics.counts.copy();repair=g.repair(req,ev["raw_response_content"],(result.failure.value,));triggers[-1]["repair"]={"committed":repair.committed,"failure":repair.failure.value if repair.failure else None,"semantic_fidelity":bool(repair.committed and repair.value.get("marker")=="ALPHA-17"),"additional_tokens":repair.input_tokens+repair.output_tokens,"additional_latency_ms":repair.latency_ms,"additional_cost_usd":repair.cost_usd};break
  report={"natural_malformed_trigger_observed":repair is not None,"trigger_attempts":len(triggers),"repair_attempts":int(repair is not None),"repair_successes":int(bool(repair and repair.committed)),"triggers":triggers};(out/"report.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report));return 0
 finally:store.close()
if __name__=="__main__":raise SystemExit(main(sys.argv[1]))
