"""Live 25%-150% output-capacity stress with synthetic text."""
import json, os, statistics, sys
from pathlib import Path
from syune.model_gateway import *
MODEL="gpt-5.4-mini-2026-03-17";LEVELS=(25,50,75,100,125,150);STRATEGIES=("PLAIN_JSON","NATIVE_STRUCTURED","COMPACT_SCHEMA");MAX_OUTPUT=256
def main(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);pre={"model":MODEL,"levels_percent":LEVELS,"strategies":STRATEGIES,"max_output_tokens":MAX_OUTPUT,"generation":"request one numbered synthetic token per target unit; target units equal percentage of 160-word calibrated visible capacity","calls":18,"hard_cost_usd":.25};(out/"preregistration.json").write_text(json.dumps(pre,indent=2)+"\n")
 caps=ModelCapabilities(frozenset({Capability.TEXT_GENERATION,Capability.STRUCTURED_OUTPUT,Capability.NATIVE_JSON_SCHEMA,Capability.USAGE_TELEMETRY,Capability.PROVIDER_REQUEST_ID}),400000,128000);meta=ModelMetadata("openai",MODEL,"2026-03-17",caps,.75,4.5);store=EvidenceStore(out/"executions.sqlite3");g=ModelGateway({"openai":OpenAIResponsesAdapter(os.environ["OPENAI_API_KEY"],{MODEL:meta})},store,routes=(("openai",MODEL),));budget=(BudgetLimit("experiment","phase29.2-truncation",30,100000,10000,.25),);rows=[]
 try:
  for strategy in STRATEGIES:
   compact=strategy=="COMPACT_SCHEMA";key="t" if compact else "text";schema={"type":"object","additionalProperties":False,"properties":{key:{"type":"string"}},"required":[key]};mode=StructuredOutputStrategy.PLAIN_JSON_PROMPT if strategy=="PLAIN_JSON" else StructuredOutputStrategy.COMPACT_SCHEMA if compact else StructuredOutputStrategy.NATIVE_STRUCTURED_OUTPUT
   for level in LEVELS:
    target=round(160*level/100)
    def validate(value,target=target,key=key):
     if len(value[key].split())<target:raise ValueError("semantic output incomplete")
    req=ModelExecutionRequest(f"phase29.2:stress:{strategy}:{level}","Synthetic truncation stress",({"role":"system","content":"Return the requested synthetic sequence completely and no commentary."},{"role":"user","content":f"In field {key}, write exactly {target} space-separated tokens numbered W1 through W{target}."}),call_role=CallRole.SYNTHESIS,structured_output_schema=schema,semantic_validator=validate,preferred_model=MODEL,exact_model=True,max_output_tokens=MAX_OUTPUT,strategy=mode,retry_policy=RetryPolicy(max_attempts=1),budget_limits=budget)
    r=g.execute(req);ev=store.evidence(req.logical_call_id);rows.append({"strategy":strategy,"level_percent":level,"target_words":target,"committed":r.committed,"failure":r.failure.value if r.failure else None,"finish_reason":ev[-1]["finish_reason"] if ev else None,"input_tokens":r.input_tokens,"output_tokens":r.output_tokens,"latency_ms":r.latency_ms,"cost_usd":r.cost_usd,"finish_before_parse":bool(ev and ev[-1]["failure_class"]=="TRUNCATED_OUTPUT") if r.failure is FailureClass.TRUNCATED_OUTPUT else None})
    (out/"calls.jsonl").write_text("\n".join(json.dumps(x,sort_keys=True) for x in rows)+"\n")
  report={"preregistration":pre,"rows":rows,"totals":{"calls":len(rows),"commits":sum(x["committed"] for x in rows),"truncations":sum(x["failure"]=="TRUNCATED_OUTPUT" for x in rows),"semantic_failures":sum(x["failure"]=="SEMANTIC_INVALID" for x in rows),"terminal_failures":sum(not x["committed"] for x in rows),"correct_finish_classifications":sum(x["finish_before_parse"] is True for x in rows),"input_tokens":sum(x["input_tokens"] for x in rows),"output_tokens":sum(x["output_tokens"] for x in rows),"cost_usd":sum(x["cost_usd"] for x in rows)}};(out/"report.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report["totals"]));return 0
 finally:store.close()
if __name__=="__main__":raise SystemExit(main(sys.argv[1]))
