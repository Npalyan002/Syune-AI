"""Release-only smoke suite; run with an installed wheel from outside the checkout."""
from __future__ import annotations
import argparse, asyncio, json, shutil, subprocess, sys, tempfile
from dataclasses import dataclass
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path); args=parser.parse_args()
    from syune import (ContextRequest, ProvenanceMode, ReviseRequest, Syune, TypedId,
        __version__, context_only, full_lean, memory_context, memory_only, model_gateway_only)
    assert __version__=="1.0.0"
    base=Path(tempfile.mkdtemp(prefix="syune-rc1-")); state=base/"state"
    subprocess.run([sys.executable,"-m","syune.cli.app","init","--state-root",str(state)],check=True,
                   stdout=subprocess.DEVNULL)
    with Syune.open(state_root=state) as client:
        assert client.status().data["package_version"]=="1.0.0"
        first=client.remember("installed wheel governed record"); old=first.data["memory_id"]
        context=client.context(ContextRequest("governed record",provenance_mode=ProvenanceMode.FULL))
        assert context.data["items"][0]["audit_sequence"] and "provenance" in context.data["rendered"]
        revised=client.revise(ReviseRequest(TypedId.parse(old),"installed wheel revised record"))
        assert client.history(revised.data["memory_id"]).data["truth"]["revision_of"]==old
        client.archive(old); assert client.audit().data["events"]
    backup=base/"backup"; shutil.copytree(state,backup); shutil.rmtree(state); shutil.copytree(backup,state)
    with Syune.open(state_root=state) as restored:
        assert restored.recall("revised record").data["candidates"] and restored.audit().data["events"]
        from mcp import Client
        from syune.gateway.mcp import LEAN_TOOL_ALLOWLIST, create_lean_mcp_server
        async def mcp_check():
            async with Client(create_lean_mcp_server(restored)) as mcp:
                assert {tool.name for tool in (await mcp.list_tools()).tools}==LEAN_TOOL_ALLOWLIST
                result=await mcp.call_tool("syune_health")
                assert not result.is_error and result.structured_content["product"]=="SYUNE"
                assert result.structured_content["runtime"]=="LEAN_V1"
                assert result.structured_content["version"]=="1.0.0"
        asyncio.run(mcp_check())
        restored.close()  # repeated shutdown is safe
    modes={}
    with memory_only(base/"memory-only.sqlite3") as item: modes[item.mode.value]=item.health()["overall"]
    memory=memory_only(base/"context.sqlite3")
    with context_only(memory.memory) as item: modes[item.mode.value]=item.health()["overall"]
    class Gateway:
        def execute(self,request): return request
    with model_gateway_only(Gateway()) as item: modes[item.mode.value]=item.health()["overall"]
    with memory_context(base/"memory-context") as item: modes[item.mode.value]=item.health()["overall"]
    with full_lean(state_root=state) as item:
        modes[item.mode.value]=item.health()["overall"]
        assert item.runtime.learning is item.runtime.cognition is item.runtime.council is item.runtime.planner is None
    from syune.model_gateway import (BudgetLimit, CallRole, Capability, EvidenceStore, FailureClass,
        HealthStatus, ModelCapabilities, ModelExecutionRequest, ModelGateway, ModelMetadata,
        RawProviderResponse)
    @dataclass
    class Adapter:
        name:str="synthetic"; is_local:bool=True
        def capabilities(self,model): return self.model_metadata(model).capabilities
        def model_metadata(self,model): return ModelMetadata(self.name,model,"rc1-synthetic",
            ModelCapabilities(frozenset({Capability.TEXT_GENERATION,Capability.STRUCTURED_OUTPUT,
                Capability.NATIVE_JSON_SCHEMA,Capability.USAGE_TELEMETRY}),max_output_tokens=100),1.0,1.0)
        def health(self,model): return HealthStatus.HEALTHY
        def execute(self,request): return RawProviderResponse(200,json.dumps({"output_text":"{\"answer\":\"ok\"}"}),
            "synthetic-request",request.model,"rc1-synthetic","completed",None,4,3,1.0,
            sanitized_metadata={"response_text":"{\"answer\":\"ok\"}"})
    evidence_path=base/"gateway.sqlite3"; store=EvidenceStore(evidence_path)
    gateway=ModelGateway({"synthetic":Adapter()},store,routes=(("synthetic","model-1"),),sleeper=lambda _:None)
    schema={"type":"object","additionalProperties":False,"properties":{"answer":{"type":"string"}},"required":["answer"]}
    model_request=ModelExecutionRequest("installed-model-call","installed validation",({"role":"user","content":"synthetic"},),
        call_role=CallRole.DECISION,structured_output_schema=schema,preferred_model="model-1",exact_model=True)
    result=gateway.execute(model_request); assert result.committed and result.provider=="synthetic" and result.resolved_model=="model-1"
    denied=gateway.execute(ModelExecutionRequest("installed-budget-call","budget",({"role":"user","content":"synthetic"},),
        preferred_model="model-1",exact_model=True,budget_limits=(BudgetLimit("request","rc",max_calls=0),)))
    assert denied.failure is FailureClass.BUDGET_EXCEEDED
    with Syune.open(state_root=state,model_gateway=gateway) as client:
        assert client.model(model_request).data["state"]=="COMMITTED"
        assert any(event["logical_call_id"]=="installed-model-call" for event in client.audit().data["events"])
    store.close(); reopened=EvidenceStore(evidence_path); assert reopened.evidence("installed-model-call"); reopened.close()
    missing=base/"missing-audit"; shutil.copytree(state,missing); (missing/"audit"/"audit.sqlite3").unlink()
    try: Syune.open(state_root=missing)
    except Exception as exc: missing_explicit=type(exc).__name__
    else: raise AssertionError("missing audit store was silently recreated")
    corrupt=base/"corrupt"; shutil.copytree(state,corrupt)
    (corrupt/"memory"/"memory.sqlite3").write_bytes(b"not-a-sqlite-database")
    try: Syune.open(state_root=corrupt)
    except Exception as exc: corruption_explicit=type(exc).__name__
    else: raise AssertionError("corrupt store opened silently")
    result={"version":__version__,"wheel_import":True,"quickstart_core":True,"backup_restore":True,
            "restart":True,"audit":True,"mcp":True,"detachability":modes,"default_research_initialized":False,
            "model_gateway":True,"structured_output":True,"budget":True,"model_identity":True,
            "missing_store_failure":missing_explicit,"corruption_failure":corruption_explicit,
            "python":sys.version.split()[0],"platform":sys.platform}
    if args.output: args.output.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result,sort_keys=True)); shutil.rmtree(base)

if __name__=="__main__": main()
