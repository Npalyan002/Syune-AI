import pytest

from syune import ContextRequest, RememberRequest, RuntimeMode, Syune, SyuneError
from syune.product.config import load_config
from syune.product.runtime import SyuneRuntime
from syune.product.state import initialize_state


def open_lean(tmp_path):
    root = (tmp_path / "state").resolve()
    config = load_config(cli_state_root=root)
    initialize_state(config)
    return config, Syune.open(state_root=root, mode=RuntimeMode.TEST)


def test_default_runtime_is_lean_and_research_is_not_imported(tmp_path):
    config, _ = open_lean(tmp_path)
    with SyuneRuntime.open(config) as runtime:
        assert runtime.learning is runtime.cognition is runtime.council is runtime.planner is None
        assert runtime.health()["overall"] == "HEALTHY"


def test_remember_context_audit_forget_flow(tmp_path):
    _, client = open_lean(tmp_path)
    with client:
        stored = client.remember("The launch window is Friday.")
        context = client.context(ContextRequest("launch window", max_chars=512))
        assert "Friday" in context.data["rendered"]
        assert context.data["score_meaning"].endswith("truth probability")
        assert client.audit().data["context_events"]
        forgotten = client.forget(stored.data["memory_id"])
        assert forgotten.data["lifecycle"] == "FORGOTTEN"
        assert not client.context("launch window").data["items"]


def test_context_preserves_authorization_boundary(tmp_path):
    _, client = open_lean(tmp_path)
    with client:
        client.remember(RememberRequest("private launch code alpha", owner="user:alice"))
        with pytest.raises(SyuneError) as denied:
            client.context("private launch code")
        assert denied.value.code == "MISSING_PRINCIPAL"
        allowed = client.context(ContextRequest("private launch code", user_id="alice"))
        assert allowed.data["items"]


def test_model_requires_explicit_gateway(tmp_path):
    _, client = open_lean(tmp_path)
    with client, pytest.raises(SyuneError) as error:
        client.model(object())
    assert error.value.code == "MODEL_UNAVAILABLE"
