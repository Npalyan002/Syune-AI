import asyncio
import os
import sys
from hashlib import sha256

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from syune.core import (
    ClaimId, ConceptId, Confidence, EpisodeId, EvidenceId, MemoryTraceId,
    ObservationId, ProcedureId, ProvenanceId, SourceId, utc_now,
)
from syune.gateway.mcp import GatewayConfig, open_gateway
from syune.gateway.mcp.server import TOOL_ALLOWLIST
from syune.memory import (
    Claim, Concept, Episode, Evidence, EvidencePolarity, MemoryTrace,
    Observation, Procedure, Provenance, Source,
)
from syune.product.config import load_config
from syune.product.state import initialize_state


def payload(result):
    assert not result.is_error, result.content
    assert result.structured_content is not None
    return result.structured_content


def test_official_client_discovery_study_recall_security_and_restart(tmp_path):
    root = tmp_path / "library"
    root.mkdir()
    source = root / "sample.md"
    source.write_text("# Local\n\nOrchard planning note\n", encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_text("not approved", encoding="utf-8")
    config = GatewayConfig(tmp_path / "state", (root,))

    async def first():
        with open_gateway(config) as (server, services):
            async with Client(server) as client:
                listed = await client.list_tools()
                assert {tool.name for tool in listed.tools} == TOOL_ALLOWLIST
                health = payload(await client.call_tool("syune_health"))
                assert (health["service"], health["autonomy_level"], health["execution_mode"]) == ("SYUNE Research Compatibility", "RESEARCH_COMPATIBILITY_L3", "ADVISORY_RESEARCH")
                assert "state" not in str(health)
                unknown = payload(await client.call_tool("syune_source_status", {"fingerprint": "0" * 64}))
                assert not unknown["known"]
                studied = payload(await client.call_tool("syune_study_source", {"path": str(source)}))
                assert studied["classification"] == "NEW_SOURCE"
                assert studied["state"] == "ENCODED"
                assert studied["materialization"] == "MATERIALIZED"
                assert studied["sha256"] == sha256(source.read_bytes()).hexdigest()
                same = payload(await client.call_tool("syune_study_source", {"path": str(source)}))
                assert same["classification"] == "ALREADY_STUDIED"
                status = payload(await client.call_tool("syune_source_status", {"source_id": "SourceId:" + studied["source_id"]}))
                assert status["is_studied"] and status["materialization"] == "MATERIALIZED"
                oid = ObservationId.parse(services.registry.status(services.registry.by_fingerprint(studied["sha256"]).revision_id).derived_memory_ids[0])
                memory = payload(await client.call_tool("syune_memory_get", {"entity_id": "ObservationId:" + str(oid)}))
                assert memory["entity_type"] == "Observation"
                assert memory["fields"]["provenance"]["source_id"] == studied["source_id"]
                before = tuple(services.memory._db.execute("SELECT * FROM entities ORDER BY id_type,id_value"))
                recall = payload(await client.call_tool("syune_recall", {"text": "orchard planning"}))
                assert any(item["entity_type"] == "Observation" for item in recall["candidates"])
                assert recall["candidates"][0]["typed_entity_id"] == "ObservationId:" + recall["candidates"][0]["entity_id"]
                direct = payload(await client.call_tool(
                    "syune_memory_get", {"entity_id": recall["candidates"][0]["typed_entity_id"]}))
                assert direct["id"] == recall["candidates"][0]["entity_id"]
                assert recall["candidates"][0]["components"]
                assert recall["score_meaning"].startswith("relevance")
                repeat = payload(await client.call_tool("syune_recall", {"text": "orchard planning"}))
                assert [(x["entity_id"], x["score"]) for x in recall["candidates"]] == [(x["entity_id"], x["score"]) for x in repeat["candidates"]]
                assert tuple(services.memory._db.execute("SELECT * FROM entities ORDER BY id_type,id_value")) == before
                assert (await client.call_tool("syune_study_source", {"path": str(outside)})).is_error
                assert (await client.call_tool("syune_study_source", {"path": str(root / ".." / "outside.md")})).is_error
                unsupported = root / "file.bin"
                unsupported.write_bytes(b"x")
                assert (await client.call_tool("syune_study_source", {"path": str(unsupported)})).is_error
                assert source.read_text(encoding="utf-8") == "# Local\n\nOrchard planning note\n"
                return studied, str(oid)

    studied, oid = asyncio.run(first())

    async def restarted():
        with open_gateway(config) as (server, _):
            async with Client(server) as client:
                health = payload(await client.call_tool("syune_health"))
                status = payload(await client.call_tool("syune_source_status", {"fingerprint": studied["sha256"]}))
                memory = payload(await client.call_tool("syune_memory_get", {"entity_id": "ObservationId:" + oid}))
                recall = payload(await client.call_tool("syune_recall", {"text": "orchard planning"}))
                assert health["retrieval_index"] == "available"
                assert status["is_studied"] and status["materialization"] == "MATERIALIZED"
                assert memory["entity_type"] == "Observation"
                assert recall["candidates"]

    asyncio.run(restarted())


def test_stdio_protocol_smoke(tmp_path):
    from syune.gateway.mcp import LEAN_TOOL_ALLOWLIST
    root = tmp_path / "library"
    root.mkdir()
    state = (tmp_path / "state").resolve()
    initialize_state(load_config(cli_state_root=state))

    async def run():
        env = os.environ.copy()
        env["SYUNE_STUDY_ROOTS"] = str(root)
        env["SYUNE_STATE_ROOT"] = str(state)
        params = StdioServerParameters(command=sys.executable, args=["-m", "syune.gateway.mcp"], env=env, cwd=str(tmp_path))
        async with Client(params) as client:
            assert {tool.name for tool in (await client.list_tools()).tools} == LEAN_TOOL_ALLOWLIST
            assert payload(await client.call_tool("syune_health"))["transport"] == "stdio"

    asyncio.run(run())


def test_typed_claim_safe_errors_and_degraded_materialization(tmp_path):
    root = tmp_path / "library"
    root.mkdir()
    source = root / "note.txt"
    source.write_text("A perceived note", encoding="utf-8")
    config = GatewayConfig(tmp_path / "state", (root,))

    async def run():
        with open_gateway(config) as (server, services):
            async with Client(server) as client:
                assert (await client.call_tool("syune_memory_get", {"entity_id": "bad-id"})).is_error
                assert (await client.call_tool("syune_study_source", {"path": str(root / "missing.txt")})).is_error
                studied = payload(await client.call_tool("syune_study_source", {"path": str(source)}))
                at = utc_now()
                claim_id = ClaimId.new()
                services.memory.put(Claim(claim_id, "a proposition, not accepted truth",
                                          Provenance(ProvenanceId.new(), SourceId.parse(studied["source_id"]), at),
                                          Confidence(0.4), at))
                services.index.sync()
                claim = payload(await client.call_tool("syune_memory_get", {"entity_id": "ClaimId:" + str(claim_id)}))
                assert claim["entity_type"] == "Claim"
                revision = services.registry.by_fingerprint(studied["sha256"])
                missing_trace = revision.derived_memory_ids[1]
                services.memory._db.execute("DELETE FROM entities WHERE id_type='MemoryTraceId' AND id_value=?", (missing_trace,))
                services.memory._db.commit()
                status = payload(await client.call_tool("syune_source_status", {"fingerprint": studied["sha256"]}))
                assert status["materialization"] == "PARTIAL_MEMORY"
                assert (await client.call_tool("syune_recall", {"text": "perceived note"})).is_error

    asyncio.run(run())


def test_every_recall_entity_type_has_canonical_round_trip_id(tmp_path):
    root = tmp_path / "library"
    root.mkdir()
    config = GatewayConfig(tmp_path / "state", (root,))

    async def run():
        with open_gateway(config) as (server, services):
            at = utc_now()
            source_id = SourceId.new()
            provenance = Provenance(ProvenanceId.new(), source_id, at)
            claim_id = ClaimId.new()
            observation_id = ObservationId.new()
            entities = (
                Source(source_id, "synthetic", "typed round trip", at),
                Observation(observation_id, "typed observation", "text", provenance, at, at),
                Concept(ConceptId.new(), "typed concept", provenance, Confidence(0.5), at),
                Claim(claim_id, "typed claim", provenance, Confidence(0.5), at),
                Evidence(EvidenceId.new(), (claim_id,), EvidencePolarity.SUPPORTS, "typed evidence",
                         provenance, Confidence(0.5), at),
                Episode(EpisodeId.new(), "typed episode", at, provenance, Confidence(0.5), at),
                Procedure(ProcedureId.new(), ("typed step",), provenance, Confidence(0.5), at),
                MemoryTrace(MemoryTraceId.new(), observation_id, at, provenance, Confidence(0.5), at),
            )
            for entity in entities:
                services.memory.put(entity)
            services.index.sync()

            async with Client(server) as client:
                for entity in entities:
                    canonical = f"{type(entity.id).__name__}:{entity.id}"
                    recall = payload(await client.call_tool("syune_recall", {"entity_ids": [canonical]}))
                    assert len(recall["candidates"]) == 1
                    candidate = recall["candidates"][0]
                    assert candidate["entity_id"] == str(entity.id)
                    assert candidate["entity_type"] == type(entity).__name__
                    assert candidate["typed_entity_id"] == canonical
                    memory = payload(await client.call_tool(
                        "syune_memory_get", {"entity_id": candidate["typed_entity_id"]}))
                    assert memory["id"] == candidate["entity_id"]
                    assert memory["entity_type"] == candidate["entity_type"]
                assert (await client.call_tool("syune_memory_get", {"entity_id": str(observation_id)})).is_error

    asyncio.run(run())


def test_shadow_stdio_exposes_only_read_tools(tmp_path):
    from syune.gateway.mcp import LEAN_TOOL_ALLOWLIST
    root = tmp_path / "library"
    root.mkdir()
    state = (tmp_path / "state").resolve()
    initialize_state(load_config(cli_state_root=state))

    async def run():
        env = os.environ.copy()
        env["SYUNE_STUDY_ROOTS"] = str(root)
        env["SYUNE_STATE_ROOT"] = str(state)
        env["SYUNE_MCP_SHADOW_READ_ONLY"] = "1"
        params = StdioServerParameters(command=sys.executable, args=["-m", "syune.gateway.mcp"], env=env, cwd=str(tmp_path))
        async with Client(params) as client:
            names = {tool.name for tool in (await client.list_tools()).tools}
            assert names == LEAN_TOOL_ALLOWLIST
            assert payload(await client.call_tool("syune_health"))["runtime"] == "LEAN_V1"
            assert (await client.call_tool("syune_remember", {"text": "blocked"})).is_error

    asyncio.run(run())
