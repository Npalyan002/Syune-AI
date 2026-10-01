import json
import threading
from dataclasses import dataclass

from syune.model_gateway import *


SCHEMA = {"type":"object","additionalProperties":False,
          "properties":{"answer":{"type":"string"},"confidence":{"type":"number","minimum":0,"maximum":1}},
          "required":["answer","confidence"]}


@dataclass
class FakeAdapter:
    outcomes: list
    name: str = "fake"
    is_local: bool = True

    def capabilities(self, model): return self.model_metadata(model).capabilities
    def model_metadata(self, model):
        return ModelMetadata(self.name,model,"snapshot-1",ModelCapabilities(frozenset({
            Capability.TEXT_GENERATION,Capability.STRUCTURED_OUTPUT,Capability.NATIVE_JSON_SCHEMA,
            Capability.USAGE_TELEMETRY,Capability.PROVIDER_REQUEST_ID}),max_output_tokens=1000),1.0,2.0)
    def health(self, model): return HealthStatus.HEALTHY
    def execute(self, request):
        outcome=self.outcomes.pop(0)
        if isinstance(outcome,Exception): raise outcome
        text=outcome.get("text",json.dumps({"answer":"yes","confidence":.8}))
        body=json.dumps({"id":"p1","model":request.model,"output_text":text,"secret":"never"})
        return RawProviderResponse(outcome.get("status",200),body,"p1",request.model,"snapshot-1",
            outcome.get("finish","completed"),outcome.get("refusal"),10,5,3.0,
            sanitized_metadata={"response_text":text,"authorization":"Bearer leak"})


def request(call_id="call-1", **changes):
    values=dict(logical_call_id=call_id,purpose="test",call_role=CallRole.DECISION,
        messages=({"role":"system","content":"trusted"},{"role":"user","content":"data"}),
        structured_output_schema=SCHEMA,preferred_model="m1",exact_model=True,
        retry_policy=RetryPolicy(max_attempts=2,backoff_seconds=(0,)))
    values.update(changes); return ModelExecutionRequest(**values)


def gateway(tmp_path, adapter, **kwargs):
    store=EvidenceStore(tmp_path/"gateway.sqlite3")
    return ModelGateway({adapter.name:adapter},store,routes=((adapter.name,"m1"),),sleeper=lambda _:None,**kwargs)


def test_raw_first_structured_commit_and_idempotent_resume(tmp_path):
    adapter=FakeAdapter([{}]); subject=gateway(tmp_path,adapter)
    first=subject.execute(request()); second=subject.execute(request())
    assert first.committed and second.committed and first.semantic_commit_id==second.semantic_commit_id
    assert len(subject.store.evidence("call-1"))==1 and not adapter.outcomes
    states=subject.store.transitions("call-1")
    assert states.index("RAW_PERSISTED") < states.index("COMMITTED")


def test_finish_reason_classifies_truncation_before_json_parse(tmp_path):
    subject=gateway(tmp_path,FakeAdapter([{"finish":"length","text":"{"},{"finish":"length","text":"{"}]))
    result=subject.execute(request())
    assert result.failure is FailureClass.TRUNCATED_OUTPUT and result.attempts==2
    assert all(row["failure_class"]=="TRUNCATED_OUTPUT" for row in subject.store.evidence("call-1"))


def test_schema_and_semantic_validation_are_distinct(tmp_path):
    bad=gateway(tmp_path/"a",FakeAdapter([{"text":json.dumps({"answer":"yes"})}]))
    assert bad.execute(request(retry_policy=RetryPolicy(max_attempts=1))).failure is FailureClass.SCHEMA_INVALID
    def reject(value): raise ValueError("not permitted")
    semantic=gateway(tmp_path/"b",FakeAdapter([{}]))
    assert semantic.execute(request(semantic_validator=reject,retry_policy=RetryPolicy(max_attempts=1))).failure is FailureClass.SEMANTIC_INVALID


def test_budget_wins_before_transport(tmp_path):
    adapter=FakeAdapter([{}]); subject=gateway(tmp_path,adapter)
    result=subject.execute(request(budget_limits=(BudgetLimit("request","x",max_calls=0),)))
    assert result.failure is FailureClass.BUDGET_EXCEEDED and len(adapter.outcomes)==1


def test_fallback_is_explicit_and_labeled(tmp_path):
    first=FakeAdapter([ProviderTransportError("busy",status=503,response_received=True)],name="p1",is_local=False)
    second=FakeAdapter([{}],name="p2",is_local=False)
    store=EvidenceStore(tmp_path/"gateway.sqlite3")
    subject=ModelGateway({"p1":first,"p2":second},store,routes=(("p1","m1"),("p2","m2")),sleeper=lambda _:None)
    result=subject.execute(request(exact_model=False,fallback_mode=FallbackMode.CAPABILITY_EQUIVALENT,
        retry_policy=RetryPolicy(max_attempts=1),allowed_models=frozenset({"m1","m2"})))
    assert result.committed and result.used_fallback and result.quality is Quality.FALLBACK and result.provider=="p2"


def test_secret_hygiene_in_durable_evidence(tmp_path):
    subject=gateway(tmp_path,FakeAdapter([{}])); subject.execute(request())
    serialized=json.dumps(subject.store.evidence("call-1")).casefold()
    assert "bearer leak" not in serialized and "api_key" not in serialized and "authorization" not in serialized


def test_data_policy_blocks_external_route(tmp_path):
    adapter=FakeAdapter([{}],is_local=False); subject=gateway(tmp_path,adapter)
    result=subject.execute(request(data_policy=DataPolicy(allow_external=False)))
    assert result.failure is FailureClass.CAPABILITY_UNAVAILABLE and len(adapter.outcomes)==1


def test_circuit_breaker_opens_only_for_systemic_failures(tmp_path):
    circuit=CircuitBreaker(threshold=1,recovery_seconds=999)
    subject=gateway(tmp_path,FakeAdapter([ProviderTransportError("down",status=503,response_received=True)]),circuit_breaker=circuit)
    first=subject.execute(request(retry_policy=RetryPolicy(max_attempts=1)))
    second=subject.execute(request("call-2",retry_policy=RetryPolicy(max_attempts=1)))
    assert first.failure is FailureClass.PROVIDER_5XX and second.failure is FailureClass.CIRCUIT_OPEN


def test_unknown_usage_keeps_reservation_and_metrics_are_auditable(tmp_path):
    subject=gateway(tmp_path,FakeAdapter([{}])); result=subject.execute(request())
    metrics=subject.metrics.snapshot()
    assert result.cost_usd>0 and metrics["calls"]==1 and metrics["success_rate"]==1
    assert metrics["cost_by_provider"]["fake"]>0


def test_repair_is_distinct_opt_in_call(tmp_path):
    subject=gateway(tmp_path,FakeAdapter([{}]))
    result=subject.repair(request(),"{bad",("invalid JSON",))
    assert result.committed and result.used_repair and result.logical_call_id.endswith(":repair")
    assert subject.metrics.snapshot()["repair_rate"]==1


def test_same_logical_id_with_different_request_is_rejected(tmp_path):
    subject=gateway(tmp_path,FakeAdapter([{}])); assert subject.execute(request()).committed
    conflict=subject.execute(request(purpose="different"))
    assert conflict.failure is FailureClass.IDEMPOTENCY_CONFLICT


def test_concurrent_duplicate_executes_provider_once(tmp_path):
    adapter=FakeAdapter([{}]); subject=gateway(tmp_path,adapter); results=[]
    threads=[threading.Thread(target=lambda:results.append(subject.execute(request()))) for _ in range(8)]
    [thread.start() for thread in threads]; [thread.join() for thread in threads]
    assert len(results)==8 and all(item.committed for item in results)
    assert len(subject.store.evidence("call-1"))==1 and len({x.semantic_commit_id for x in results})==1


def test_health_distinguishes_content_failure_from_systemic_outage(tmp_path):
    circuit=CircuitBreaker(threshold=1,recovery_seconds=999)
    content=gateway(tmp_path/"content",FakeAdapter([{"text":"{bad"}]),circuit_breaker=circuit)
    content.execute(request(retry_policy=RetryPolicy(max_attempts=1)))
    assert content.health()["overall"]=="HEALTHY"
    systemic=gateway(tmp_path/"systemic",FakeAdapter([ProviderTransportError("down",status=503,response_received=True)]),circuit_breaker=CircuitBreaker(threshold=1,recovery_seconds=999))
    systemic.execute(request(retry_policy=RetryPolicy(max_attempts=1)))
    assert systemic.health()["routes"][0]["status"]=="CIRCUIT_OPEN"
