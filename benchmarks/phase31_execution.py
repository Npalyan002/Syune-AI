"""Executable Phase 31 runner using production ModelGateway and SYUNE services."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from benchmarks.phase28r import (DECISION_SCHEMA, DECISION_SYSTEM, MODEL, SYNTHESIS_SCHEMA,
                                 SYNTHESIS_SYSTEM, build_prompt)
from benchmarks.phase28r_integration import LearningRuntime, Phase28RExperienceAdapter
from benchmarks.phase31 import BUDGET, TREATMENTS, canonical, dataset
from syune.memory import AccessContext, Principal
from syune.model_gateway import *
from syune.retrieval import RecallCue, RecallRequest, RetrievalService

PRICE_INPUT = .75
PRICE_OUTPUT = 4.5


class Phase31ExperienceAdapter(Phase28RExperienceAdapter):
    """Use material environment identity; epoch chronology is stored elsewhere."""
    def map(self,task,selected_action,outcome,condition):
        value=super().map(task,selected_action,outcome,condition)
        stable={"system_generation":task["environment_state_visible_to_agent"]["system_generation"]}
        return replace(value,environment=canonical(stable))


@dataclass
class DeterministicTraversalAdapter:
    """Development-only traversal adapter; never used for treatment evidence."""
    name: str = "fake"
    is_local: bool = True
    calls: int = 0
    def model_metadata(self, model):
        return ModelMetadata(self.name, model, "fake-v1", default_text_capabilities(), PRICE_INPUT, PRICE_OUTPUT)
    def capabilities(self, model): return self.model_metadata(model).capabilities
    def health(self, model): return HealthStatus.HEALTHY
    def execute(self, call):
        self.calls += 1; prompt = str(call.request.messages[-1]["content"])
        if call.request.call_role is CallRole.SYNTHESIS:
            value = {"applicable_rule":"Use current policy and the most recent matching successful experience.","conditions":[],"exceptions":[],"uncertainty":.25,"supporting_evidence_ids":[],"conflicting_evidence_ids":[]}
        else:
            actions = re.findall(r"^- ([A-Z0-9_]+):", prompt, re.MULTILINE)
            value = {"selected_action":actions[0] if actions else "ABSTAIN","abstain":not bool(actions),"confidence":.6,"reason_code":"FAKE_TRAVERSAL"}
        text = canonical(value)
        return RawProviderResponse(200, canonical({"id":f"fake-{self.calls}","model":MODEL,"output_text":text}),
            f"fake-{self.calls}", MODEL, "fake-v1", "completed", input_tokens=max(1,len(prompt)//4),
            output_tokens=max(1,len(text)//4), latency_ms=.2, sanitized_metadata={"response_text":text})


def _gateway(root: Path, live: bool):
    root.mkdir(parents=True, exist_ok=True); store = EvidenceStore(root / "gateway.sqlite3")
    caps = ModelCapabilities(frozenset({Capability.TEXT_GENERATION,Capability.STRUCTURED_OUTPUT,
        Capability.NATIVE_JSON_SCHEMA,Capability.USAGE_TELEMETRY,Capability.PROVIDER_REQUEST_ID}),400000,128000)
    if live:
        meta = ModelMetadata("openai",MODEL,"2026-03-17",caps,PRICE_INPUT,PRICE_OUTPUT)
        adapter = OpenAIResponsesAdapter(os.environ["OPENAI_API_KEY"],{MODEL:meta}); name = "openai"
    else:
        adapter = DeterministicTraversalAdapter(); name = "fake"
    return ModelGateway({name:adapter},store,routes=((name,MODEL),)), store, adapter, name


def _request(logical_id: str, role: CallRole, system: str, prompt: str, schema: dict[str,Any],
             principal: str, provider: str, metadata: dict[str,Any], max_output: int) -> ModelExecutionRequest:
    def valid(value):
        if role is CallRole.DECISION:
            available = metadata["available_actions"]
            if value.get("selected_action") not in available: raise ValueError("selected_action unavailable")
    return ModelExecutionRequest(logical_id,"Phase 31 frozen enterprise product validation",
        ({"role":"system","content":system},{"role":"user","content":prompt}),call_role=role,
        structured_output_schema=schema,semantic_validator=valid,preferred_model=MODEL,exact_model=True,
        principal=principal,temperature=.2,max_output_tokens=max_output,retry_policy=RetryPolicy(name="phase31-v1",max_attempts=2),
        data_policy=DataPolicy(allow_external=True,allowed_providers=frozenset({provider})),
        budget_limits=(BudgetLimit("experiment","phase31-final",max_calls=BUDGET["max_provider_calls"],
            max_input_tokens=BUDGET["max_input_tokens"],max_output_tokens=BUDGET["max_output_tokens"],
            max_cost_usd=BUDGET["hard_cost_cap_usd"]),),metadata=metadata)


def _raw_context(history: list[dict[str,Any]], task: dict[str,Any]) -> tuple[str,list[str]]:
    eligible = [x for x in history if x["task_family"] == task["task_family"] and x["epoch"] < task["epoch"]]
    eligible = eligible[-8:]; ids = [x["task_id"] for x in eligible]
    records = [{"evidence_id":x["task_id"],"epoch":x["epoch"],"observable_facts":x["observable_facts"],
        "selected_action":x["selected_action"],"outcome_success":x["outcome_success"],
        "policy_violation":x["policy_violation"],"environment":x["environment"]} for x in eligible]
    return canonical(records) if records else "No eligible organizational experience.", ids


def _syune_context(runtime: LearningRuntime, task: dict[str,Any]) -> tuple[str,list[str],float,int]:
    started=time.perf_counter(); auth=task["authorization_context"]
    access=AccessContext(Principal(agent_id=task["agent_id"],organization_id="northstar-works",
        project_id=auth["project"],department_id=auth["department"]),task["purpose"],task["task_id"],False)
    # The family identifier is the stable retrieval key embedded in promoted procedures.
    # Adding all scenario prose dilutes lexical coverage below the production seed threshold.
    simulated_at=datetime.fromisoformat(task["simulation_timestamp"])
    cue=RecallCue(text=task["task_family"],temporal_context=simulated_at,
        valid_at=simulated_at,knowledge_at=simulated_at,access_context=access)
    service=RetrievalService(runtime.memory,runtime.index)
    result=service.recall(RecallRequest(cue,max_results=6))
    records=[]; ids=[]
    for hit in result.working_memory:
        entity=runtime.memory.get(hit.entity_id)
        if hasattr(entity,"steps"):
            ids.append(str(entity.id));records.append({"procedure_id":str(entity.id),"steps":entity.steps,
                "truth":entity.truth.state.value,"confidence":entity.confidence.value})
    denied=sum(not event.decision.value.startswith("ALLOW") for event in service.access_events)
    return (canonical(records) if records else "No eligible organizational experience.",ids,
            (time.perf_counter()-started)*1000,denied)


class Runner:
    def __init__(self, out: Path, live: bool):
        self.out=out;self.live=live;self.runtime_root=out/"state";self.gateway,self.evidence,self.adapter,self.provider=_gateway(self.runtime_root,live)
        self.ledger=CognitiveTransactionLedger(self.runtime_root/"cognitive.sqlite3")
        self.ledger.db.execute("create table if not exists phase31_results(task_id text primary key,row_json text not null)")
        self.results_path=out/"results.jsonl";self.tasks,self.truth=dataset();self.truth_by={x["task_id"]:x for x in self.truth}
        self.completed=set();self.histories=defaultdict(list)
        if self.results_path.exists():
            for line in self.results_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row=json.loads(line);self.completed.add((row["treatment"],row["task_id"]));self.histories[row["treatment"]].append(row)

    def _append(self,row):
        with self.results_path.open("a",encoding="utf-8") as handle:
            handle.write(canonical(row)+"\n");handle.flush();os.fsync(handle.fileno())
        self.completed.add((row["treatment"],row["task_id"]));self.histories[row["treatment"]].append(row)

    def _terminal_result(self,logical_id):
        row=self.evidence.db.execute("select detail_json from transitions where logical_call_id=? and state='FAILED_TERMINAL' order by sequence desc limit 1",(logical_id,)).fetchone()
        if not row:return None
        failure=FailureClass(json.loads(row[0])["failure"]);attempts=self.evidence.db.execute("select evidence_json from attempts where logical_call_id=? order by attempt_number",(logical_id,)).fetchall()
        evidence=[json.loads(x[0]) for x in attempts]
        return ModelExecutionResult("",logical_id,None,ExecutionState.FAILED_TERMINAL,failure=failure,attempts=len(evidence),
            input_tokens=sum(x.get("input_tokens") or 0 for x in evidence),output_tokens=sum(x.get("output_tokens") or 0 for x in evidence),
            cost_usd=sum(x.get("actual_cost_usd") or 0 for x in evidence),latency_ms=sum(x.get("latency_ms") or 0 for x in evidence))

    def _model(self,treatment,task,context,context_ids):
        principal=task["agent_id"];meta={"treatment":treatment,"epoch":task["epoch"],"task_id":task["task_id"],
            "agent_id":principal,"available_actions":[x["id"] for x in task["available_actions"]]}
        synthesis=None;components=[]
        if treatment=="RAG_SYNTHESIS":
            sreq=_request(f"phase31:{treatment}:{task['task_id']}:synthesis",CallRole.SYNTHESIS,SYNTHESIS_SYSTEM,
                context,SYNTHESIS_SCHEMA,principal,self.provider,{**meta,"available_actions":[]},220)
            wall=time.perf_counter();synthesis=self._terminal_result(sreq.logical_call_id) or self.gateway.execute(sreq);elapsed=(time.perf_counter()-wall)*1000
            components.append((synthesis,elapsed));context=canonical(synthesis.value)
            if not synthesis.committed:
                context="Query-time synthesis unavailable after terminal gateway failure. Use current policy only."
        prompt=build_prompt(task,context)
        req=_request(f"phase31:{treatment}:{task['task_id']}:decision",CallRole.DECISION,DECISION_SYSTEM,prompt,
            DECISION_SCHEMA,principal,self.provider,meta,140)
        wall=time.perf_counter();result=self._terminal_result(req.logical_call_id) or self.gateway.execute(req);gateway_wall=(time.perf_counter()-wall)*1000
        cognitive_ms=0.0
        if not result.committed:
            answer={"selected_action":"__TERMINAL_FAILURE__","abstain":True,"confidence":0.0,"reason_code":result.failure.value if result.failure else "UNKNOWN"}
        elif treatment=="PRODUCTION_SYUNE":
            op=CognitiveOperation(f"decision:{task['task_id']}","phase31_decision",principal,req.purpose,tuple(context_ids),req)
            start=time.perf_counter()
            applied=self.ledger.apply(op,result,lambda db,v:(db.execute("insert or ignore into phase31_results values(?,?)",
                (task["task_id"],canonical(v))),v)[1])
            cognitive_ms=(time.perf_counter()-start)*1000
            answer=applied.value
        else: answer=result.value
        components.append((result,gateway_wall));model_ms=sum(x.latency_ms for x,_ in components)
        wall_ms=sum(w for _,w in components);gateway_ms=max(0,wall_ms-model_ms)
        telemetry={"input_tokens":sum(x.input_tokens for x,_ in components),"output_tokens":sum(x.output_tokens for x,_ in components),
            "cost_usd":sum(x.cost_usd for x,_ in components),"model_ms":model_ms,"gateway_ms":gateway_ms,
            "cognitive_ms":cognitive_ms,"attempts":sum(x.attempts for x,_ in components),
            "repairs":sum(x.used_repair for x,_ in components),"fallbacks":sum(x.used_fallback for x,_ in components)}
        telemetry["terminal_failures"]=sum(not x.committed for x,_ in components)
        telemetry["truncations"]=sum(x.failure is FailureClass.TRUNCATED_OUTPUT for x,_ in components)
        return answer,telemetry

    def run(self):
        for treatment in TREATMENTS:
            runtime=LearningRuntime(self.runtime_root/"syune", "SYUNE_ORGANIZATIONAL", self.tasks) if treatment=="PRODUCTION_SYUNE" else None
            if runtime: runtime.adapter=Phase31ExperienceAdapter()
            try:
                for epoch in range(10):
                    if runtime: runtime.index.rebuild()
                    for task in (x for x in self.tasks if x["epoch"]==epoch):
                        if (treatment,task["task_id"]) in self.completed: continue
                        retrieve_start=time.perf_counter();denied=0
                        if runtime: context,ids,retrieval_ms,denied=_syune_context(runtime,task)
                        else:
                            context,ids=_raw_context(self.histories[treatment],task);retrieval_ms=(time.perf_counter()-retrieve_start)*1000
                        answer,telemetry=self._model(treatment,task,context,ids)
                        truth=self.truth_by[task["task_id"]];selected=answer["selected_action"]
                        outcome=truth["outcomes_by_action"].get(selected,{"success":False,"policy_violation":True})
                        storage_start=time.perf_counter()
                        learning=None
                        if runtime: learning=runtime.process(task,selected,outcome)
                        storage_ms=(time.perf_counter()-storage_start)*1000
                        prior_errors=[x for x in self.histories[treatment] if x["task_family"]==task["task_family"] and not x["success"]]
                        knowledge_used=bool(ids);shifted=epoch in (4,5,6,7,8,9)
                        row={"treatment":treatment,"task_id":task["task_id"],"epoch":epoch,"department":task["department"],
                            "task_family":task["task_family"],"agent_id":task["agent_id"],"cold_agent":task["agent_id"].endswith("replacement"),
                            "selected_action":selected,"success":bool(outcome["success"]),"policy_violation":bool(outcome.get("policy_violation")),
                            "prior_family_error":bool(prior_errors),"repeated_error":bool(prior_errors and not outcome["success"]),
                            "knowledge_used":knowledge_used,"stale_use":bool(knowledge_used and shifted and not outcome["success"]),
                            "negative_transfer":bool(knowledge_used and not outcome["success"]),"authorized_context_ids":ids,
                            "authorization_denials":denied,"retrieval_ms":retrieval_ms,"storage_ms":storage_ms,
                            "total_latency_ms":retrieval_ms+storage_ms+telemetry["model_ms"]+telemetry["gateway_ms"]+telemetry["cognitive_ms"],
                            **telemetry,"learning":learning,"observable_facts":task["observable_facts"],
                            "environment":task["environment_state_visible_to_agent"],"outcome_success":bool(outcome["success"])}
                        self._append(row)
            finally:
                if runtime: runtime.close()
        return {"status":"COMPLETE","rows":len(self.completed),"live":self.live,"provider_calls":self.adapter.calls if not self.live else None}

    def close(self): self.ledger.close();self.evidence.close()
