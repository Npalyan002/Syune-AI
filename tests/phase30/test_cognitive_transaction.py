import json, threading
from dataclasses import dataclass

import pytest
from syune.model_gateway import *

SCHEMA={"type":"object","additionalProperties":False,"properties":{"action":{"type":"string","enum":["PROMOTE"]}},"required":["action"]}

@dataclass
class Adapter:
    calls:int=0; name:str="fixture"; is_local:bool=True; fail:bool=False
    def model_metadata(self,model):return ModelMetadata(self.name,model,"v1",ModelCapabilities(frozenset({Capability.TEXT_GENERATION,Capability.STRUCTURED_OUTPUT,Capability.NATIVE_JSON_SCHEMA}),1000,1000),1,1)
    def capabilities(self,model):return self.model_metadata(model).capabilities
    def health(self,model):return HealthStatus.HEALTHY
    def execute(self,call):
        self.calls+=1
        if self.fail:raise ProviderTransportError("down",status=503,response_received=True)
        text='{"action":"PROMOTE"}';return RawProviderResponse(200,json.dumps({"id":"r1","model":"m1","output_text":text}),"r1","m1","v1","completed",input_tokens=10,output_tokens=5,sanitized_metadata={"response_text":text})

def fixture(tmp_path,fail=False):
    adapter=Adapter(fail=fail);store=EvidenceStore(tmp_path/"gateway.db");gateway=ModelGateway({"fixture":adapter},store,routes=(("fixture","m1"),),sleeper=lambda _:None)
    ledger=CognitiveTransactionLedger(tmp_path/"cognitive.db");ledger.db.execute("create table effects(effect_key text primary key,value text not null)")
    request=ModelExecutionRequest("learn:candidate-1:evidence-a:policy-v2","Verified learning promotion",({"role":"system","content":"Return authorized decision."},{"role":"user","content":"Authorized evidence IDs: evidence-a"}),call_role=CallRole.VERIFICATION,structured_output_schema=SCHEMA,preferred_model="m1",exact_model=True,principal="agent-1",data_policy=DataPolicy(local_only=True),budget_limits=(BudgetLimit("agent","agent-1",max_calls=2),),retry_policy=RetryPolicy(max_attempts=1))
    operation=CognitiveOperation("promote:candidate-1","verified_learning","agent-1",request.purpose,("evidence-a",),request)
    return adapter,store,gateway,ledger,operation

def mutator(db,value):
    db.execute("insert into effects values(?,?)",("candidate-1",value["action"]));return {"effect":"candidate-1","action":value["action"]}

def test_gateway_commit_and_cognitive_commit_are_distinct_and_replay_once(tmp_path):
    adapter,store,gateway,ledger,operation=fixture(tmp_path);service=GatewayCognitiveTransactionService(gateway,ledger)
    first=service.execute(operation,mutator);second=service.execute(operation,mutator)
    assert first.state is CognitiveTransactionState.APPLIED and second.replayed
    assert adapter.calls==1 and ledger.db.execute("select count(*) from effects").fetchone()[0]==1
    audit=ledger.audit(first.cognitive_transaction_id)
    assert audit["gateway_logical_call_id"]==operation.request.logical_call_id
    assert audit["gateway_semantic_commit_id"]==first.gateway_semantic_commit_id
    assert first.cognitive_transaction_id not in {first.gateway_semantic_commit_id,operation.request.logical_call_id}

def test_terminal_gateway_failure_has_zero_cognitive_mutation(tmp_path):
    adapter,store,gateway,ledger,operation=fixture(tmp_path,True);service=GatewayCognitiveTransactionService(gateway,ledger)
    with pytest.raises(RuntimeError,match="MODEL_EXECUTION_UNAVAILABLE"):service.execute(operation,mutator)
    assert ledger.db.execute("select count(*) from effects").fetchone()[0]==0

def test_multi_write_failure_rolls_back_effect_and_ledger(tmp_path):
    _,_,gateway,ledger,operation=fixture(tmp_path);result=gateway.execute(operation.request)
    def broken(db,value):
        db.execute("insert into effects values('candidate-1','partial')");raise RuntimeError("crash")
    with pytest.raises(RuntimeError):ledger.apply(operation,result,broken)
    assert ledger.db.execute("select count(*) from effects").fetchone()[0]==0
    assert ledger.db.execute("select count(*) from cognitive_transactions").fetchone()[0]==0

def test_concurrent_application_is_one_effect(tmp_path):
    adapter,_,gateway,ledger,operation=fixture(tmp_path);service=GatewayCognitiveTransactionService(gateway,ledger);results=[]
    threads=[threading.Thread(target=lambda:results.append(service.execute(operation,mutator))) for _ in range(8)]
    [x.start() for x in threads];[x.join() for x in threads]
    assert len(results)==8 and sum(not x.replayed for x in results)==1
    assert adapter.calls==1 and ledger.db.execute("select count(*) from effects").fetchone()[0]==1

def test_authorized_context_and_cost_are_auditable(tmp_path):
    _,_,gateway,ledger,operation=fixture(tmp_path);result=GatewayCognitiveTransactionService(gateway,ledger).execute(operation,mutator)
    audit=ledger.audit(result.cognitive_transaction_id)
    assert audit["principal"]=="agent-1" and audit["purpose"]==operation.purpose
    assert audit["authorized_context_hash"] and ledger.cost_by_subsystem()["verified_learning"]>0

def test_operation_rejects_post_authorization_identity_mismatch(tmp_path):
    _,_,_,_,operation=fixture(tmp_path)
    with pytest.raises(ValueError):CognitiveOperation("x","learning","other",operation.purpose,(),operation.request)

def test_cognitive_service_exposes_gateway_health(tmp_path):
    _,_,gateway,ledger,_=fixture(tmp_path)
    service=GatewayCognitiveTransactionService(gateway,ledger)
    assert service.health()==gateway.health()
