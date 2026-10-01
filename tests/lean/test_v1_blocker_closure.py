from pathlib import Path
import pytest
from syune import (ContextRequest, ProvenanceMode, RememberRequest, ReviseRequest, Syune,
                   SyuneError, TypedId, memory_context, memory_only, model_gateway_only)
from syune.product.config import load_config
from syune.product.state import initialize_state

def opened(tmp_path):
    root=(tmp_path/"state").resolve(); initialize_state(load_config(cli_state_root=root)); return root,Syune.open(state_root=root)

def test_audit_provenance_revision_and_restart(tmp_path):
    root,client=opened(tmp_path)
    remembered=client.remember(RememberRequest("alpha release fact",correlation_id="op-1"))
    ctx=client.context(ContextRequest("alpha release",correlation_id="op-2",provenance_mode=ProvenanceMode.FULL))
    item=ctx.data["items"][0]
    assert item["audit_sequence"] and item["provenance"]["memory_id"]==remembered.data["memory_id"]
    assert "[provenance " in ctx.data["rendered"]
    revised=client.revise(ReviseRequest(TypedId.parse(remembered.data["memory_id"]),"alpha revised",correlation_id="op-3"))
    with pytest.raises(SyuneError) as conflict:
        client.revise(ReviseRequest(TypedId.parse(remembered.data["memory_id"]),"conflict"))
    assert conflict.value.code=="REVISION_CONFLICT"
    assert client.history(revised.data["memory_id"]).data["truth"]["revision_of"]==remembered.data["memory_id"]
    before=client.audit().data["events"]; client.close()
    with Syune.open(state_root=root) as restarted:
        assert len(restarted.audit().data["events"])>=len(before)

def test_typed_authorization_and_lifecycle_errors(tmp_path):
    _,client=opened(tmp_path)
    record=client.remember(RememberRequest("private",owner="agent:owner"))
    with pytest.raises(SyuneError) as missing: client.memory_get(record.data["memory_id"])
    assert missing.value.code=="MISSING_PRINCIPAL"
    client.forget(record.data["memory_id"])
    with pytest.raises(SyuneError) as forgotten: client.memory_get(record.data["memory_id"])
    assert forgotten.value.code=="RECORD_FORGOTTEN"
    client.close()

def test_detachable_modes(tmp_path):
    with memory_only(tmp_path/"memory.sqlite3") as mode:
        assert mode.health()["mode"]=="MEMORY_ONLY" and mode.retrieval is None
    with memory_context(tmp_path/"mc") as mode: assert mode.health()["mode"]=="MEMORY_CONTEXT"
    class Gateway:
        def execute(self, request): return request
    with model_gateway_only(Gateway()) as mode: assert mode.health()["mode"]=="MODEL_GATEWAY_ONLY"
