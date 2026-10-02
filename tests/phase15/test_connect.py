import json
import os
from pathlib import Path
import pytest
from syune.cli.app import SUCCESS, UNHEALTHY, run
from syune.product.config import StateConfig, SyuneConfig
from syune.product.connect import ConnectFailure, MCP_TOOLS, RuntimeCommand, _safe_environment, doctor, setup

def _config(root: Path) -> SyuneConfig:
    return SyuneConfig(StateConfig(root.resolve()))

def _runtime() -> RuntimeCommand:
    return RuntimeCommand(str(Path(os.sys.executable).resolve()), ("-m", "syune.gateway.mcp"))

def _probe() -> dict[str, object]:
    return {"handshake": "PASS", "health": "PASS", "tools": sorted(MCP_TOOLS), "canonical_tools": 8, "additional_tools": []}

@pytest.fixture
def mocked_connect(monkeypatch):
    monkeypatch.setattr("syune.product.connect.discover_runtime", _runtime)
    monkeypatch.setattr("syune.product.connect.probe_mcp", lambda command, root: _probe())

def test_setup_fresh_repeat_and_spaces(tmp_path, mocked_connect):
    root = (tmp_path / "state with spaces").resolve()
    first = setup(_config(root), "generic")
    second = setup(_config(root), "generic")
    assert first["state_created"] is True and second["state_created"] is False
    assert first["instance_id"] == second["instance_id"]
    assert first["generated_config"] == {"command": str(Path(os.sys.executable).resolve()), "args": ["-m", "syune.gateway.mcp"], "env": {"SYUNE_STATE_ROOT": str(root)}}
    assert json.loads(Path(first["artifact"]).read_text()) == first["generated_config"]
    assert first["third_party_config_modified"] is False

def test_setup_python_has_no_mcp_config_or_probe(tmp_path, monkeypatch):
    monkeypatch.setattr("syune.product.connect.discover_runtime", _runtime)
    monkeypatch.setattr("syune.product.connect.probe_mcp", lambda *_: pytest.fail("Python setup must not launch MCP"))
    value = setup(_config(tmp_path / "state"), "python")
    assert value["generated_config"] is None
    assert "Syune.open(state_root=state)" in value["sdk_example"]

def test_interactive_host_selection(tmp_path, mocked_connect):
    assert setup(_config(tmp_path / "state"), None, input_fn=lambda _: "1")["host"] == "codex"

def test_invalid_existing_state_is_not_overwritten(tmp_path, mocked_connect):
    root = tmp_path / "state"; root.mkdir()
    marker = root / "private.txt"; marker.write_text("preserve")
    with pytest.raises(ValueError, match="unknown entries"): setup(_config(root), "generic")
    assert marker.read_text() == "preserve" and list(root.iterdir()) == [marker]

def test_concurrent_setup_is_typed_and_nondestructive(tmp_path, mocked_connect):
    root = (tmp_path / "state").resolve()
    lock = root.parent / f".{root.name}.syune-setup.lock"; lock.write_text("pid=other")
    with pytest.raises(ConnectFailure) as error: setup(_config(root), "generic")
    assert error.value.code == "SETUP_IN_PROGRESS" and not root.exists()

def test_environment_drops_python_injection(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "malicious"); monkeypatch.setenv("PYTHONHOME", "malicious")
    root = (tmp_path / "state").resolve(); env = _safe_environment(root)
    assert "PYTHONPATH" not in env and "PYTHONHOME" not in env
    assert env["SYUNE_STATE_ROOT"] == str(root)

def test_doctor_ready_and_model_gateway_optional(tmp_path, mocked_connect):
    config = _config(tmp_path / "state"); setup(config, "generic")
    value, ready = doctor(config)
    assert ready and value["overall"] == "READY"
    assert any(x["name"] == "mcp.tools" and "8/8" in x["detail"] for x in value["checks"])
    assert any(x["name"] == "model.gateway" and x["status"] == "OPTIONAL" for x in value["checks"])

def test_doctor_uninitialized_is_actionable(tmp_path):
    value, ready = doctor(_config(tmp_path / "missing"))
    failure = next(x for x in value["checks"] if x["status"] == "FAIL")
    assert not ready and failure["detail"] == "STATE_ROOT_NOT_INITIALIZED" and "syune setup" in failure["fix"]

def test_doctor_reports_handshake_failure(tmp_path, mocked_connect, monkeypatch):
    config = _config(tmp_path / "state"); setup(config, "generic")
    def fail(*_): raise ConnectFailure("MCP_HANDSHAKE_FAILED", "failed", "check command")
    monkeypatch.setattr("syune.product.connect.probe_mcp", fail)
    value, ready = doctor(config)
    assert not ready and any(x["detail"] == "MCP_HANDSHAKE_FAILED" and x["fix"] == "check command" for x in value["checks"])

def test_cli_json_setup_and_doctor(tmp_path, mocked_connect, capsys):
    root = str((tmp_path / "state").resolve())
    assert run(["setup", "--host", "generic", "--state-root", root, "--json"]) == SUCCESS
    assert json.loads(capsys.readouterr().out)["generated_config"]["args"] == ["-m", "syune.gateway.mcp"]
    assert run(["doctor", "--state-root", root, "--json"]) == SUCCESS
    assert json.loads(capsys.readouterr().out)["overall"] == "READY"

def test_cli_doctor_uninitialized_exit_code(tmp_path, capsys):
    root = str((tmp_path / "missing").resolve())
    assert run(["doctor", "--state-root", root, "--json"]) == UNHEALTHY
    assert json.loads(capsys.readouterr().out)["overall"] == "NOT_READY"

def test_platform_default_state_paths():
    from syune.product.config import _default_state_root_for
    assert _default_state_root_for("win32", {"LOCALAPPDATA": r"C:\Users\a\AppData\Local"}, r"C:\Users\a") == r"C:\Users\a\AppData\Local\SYUNE\default"
    assert _default_state_root_for("linux", {"XDG_STATE_HOME": "/var/state/me"}, "/home/me") == "/var/state/me/syune/default"
    assert _default_state_root_for("darwin", {}, "/Users/me") == "/Users/me/Library/Application Support/SYUNE/default"