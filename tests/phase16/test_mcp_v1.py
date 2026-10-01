import asyncio
import json
import os

from mcp import Client

from syune.gateway.mcp import GatewayConfig, TOOL_ALLOWLIST, open_gateway
from syune import CognitiveRequest, PlanRequest, RecallRequest, StudyRequest, Syune
from syune.product.config import load_config
from syune.product.state import DATABASES, initialize_state


def payload(result):
    return json.loads(result.content[0].text)


def test_mcp_v1_tools_and_semantic_flow(tmp_path):
    library = tmp_path / "library"; library.mkdir()
    source = library / "fixture.txt"; source.write_text("provenance supports safe recall", encoding="utf-8")

    async def run():
        with open_gateway(GatewayConfig(tmp_path / "state", (library,))) as (server, _):
            async with Client(server) as client:
                assert {tool.name for tool in (await client.list_tools()).tools} == TOOL_ALLOWLIST
                health = payload(await client.call_tool("syune_health"))
                assert health["public_api_version"] == "1"
                assert health["gateway_contract_version"] == "1"
                assert payload(await client.call_tool("syune_status"))["execution_exposed"] is False
                caps = payload(await client.call_tool("syune_capabilities"))
                assert caps["runtime_mode"] == "NORMAL"
                studied = payload(await client.call_tool("syune_study_source", {"path": str(source)}))
                assert studied["materialization"] == "MATERIALIZED"
                recall = payload(await client.call_tool("syune_recall", {"text": "safe recall"}))
                assert recall["candidates"]
                cognition = payload(await client.call_tool("syune_cognize", {"text": "safe recall", "correlation_id": "mcp"}))
                assert cognition["correlation_id"] == "mcp"
                council = payload(await client.call_tool("syune_council", {"text": "safe recall"}))
                assert "truth probability" in council["agreement_meaning"]
                plan = payload(await client.call_tool("syune_plan", {"goal": "review safe recall"}))
                assert plan["execution_authority"] is False
    asyncio.run(run())


def test_shadow_mcp_omits_writes(tmp_path):
    library = tmp_path / "library"; library.mkdir()
    async def run():
        config = GatewayConfig(tmp_path / "state", (library,), shadow_read_only=True)
        with open_gateway(config) as (server, _):
            async with Client(server) as client:
                names = {tool.name for tool in (await client.list_tools()).tools}
                assert names == TOOL_ALLOWLIST - {"syune_study_source"}
                caps = payload(await client.call_tool("syune_capabilities"))
                study = next(item for item in caps["capabilities"] if item["operation"] == "study")
                assert study["available"] is False
    asyncio.run(run())


def test_sdk_mcp_semantic_parity(tmp_path, monkeypatch):
    library=(tmp_path/"library").resolve();library.mkdir();source=library/"parity.txt"
    source.write_text("parity evidence with provenance",encoding="utf-8")
    state=(tmp_path/"product").resolve();monkeypatch.setenv("SYUNE_STUDY_ROOTS",str(library))
    initialize_state(load_config(cli_state_root=state))
    with Syune.open(state_root=state) as brain:
        brain.study(StudyRequest(str(source)))
        sdk={"health":brain.health().data,"recall":brain.recall(RecallRequest(cue="parity evidence")).data,
             "cognition":brain.cognize(CognitiveRequest(cue="parity evidence")).data,
             "plan":brain.plan(PlanRequest("review parity evidence")).data}
    async def run():
        config=GatewayConfig(state,(library,),memory_path=state/DATABASES["memory"],study_path=state/DATABASES["study_perception"])
        with open_gateway(config) as (server,_):
            async with Client(server) as client:
                mcp={"health":payload(await client.call_tool("syune_health")),
                     "recall":payload(await client.call_tool("syune_recall",{"text":"parity evidence"})),
                     "cognition":payload(await client.call_tool("syune_cognize",{"text":"parity evidence"})),
                     "plan":payload(await client.call_tool("syune_plan",{"goal":"review parity evidence"}))}
        assert sdk["health"]["overall"]=="HEALTHY" and mcp["health"]["memory"]=="available"
        assert sdk["recall"]["candidates"][0]["entity_type"]==mcp["recall"]["candidates"][0]["entity_type"]
        assert sdk["cognition"]["status"]==mcp["cognition"]["status"]
        assert sdk["plan"]["status"]==mcp["plan"]["status"]
        assert sdk["plan"]["execution_authority"] is mcp["plan"]["execution_authority"] is False
    asyncio.run(run())
