from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import syune.adapters.aml.v1 as aml
from syune.adapters.aml import AdapterSettings, create_app


TOKEN = "phase04a-secret-token"
PROJECT = Path(__file__).resolve().parents[2]
DEPLOY = PROJECT / "deploy" / "aml"
BASELINE = "fb76ca390d0774a95a522517d129730c3446a312"


def settings(tmp_path, **overrides):
    values = {
        "state_root": (tmp_path / "evaluation-state").resolve(),
        "bearer_token": TOKEN,
        "min_free_bytes": 0,
    }
    values.update(overrides)
    return AdapterSettings(**values)


def test_health_compatibility_and_internal_readiness(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_failure_is_generic(tmp_path, monkeypatch):
    monkeypatch.setattr(aml, "_readiness_check", lambda *_args: False)
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert "sqlite" not in response.text.lower()


def test_readiness_requires_configured_disk_floor(tmp_path):
    with TestClient(create_app(settings(tmp_path, min_free_bytes=2**63))) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_secret_file_injection_and_ambiguous_secret_rejection(tmp_path, monkeypatch):
    token_file = (tmp_path / "token").resolve()
    token_file.write_text(TOKEN + "\n", encoding="utf-8")
    root = (tmp_path / "state").resolve()
    monkeypatch.setenv("SYUNE_AML_STATE_ROOT", str(root))
    monkeypatch.setenv("SYUNE_AML_BEARER_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("SYUNE_AML_MIN_FREE_BYTES", "0")
    monkeypatch.delenv("SYUNE_AML_BEARER_TOKEN", raising=False)
    with TestClient(aml.app_from_environment()) as client:
        assert client.get("/ready").status_code == 200
        assert client.post("/search", headers={"Authorization": f"Bearer {TOKEN}"},
                           json={"query": "x", "user_id": "u", "top_k": 1}).status_code == 200
    monkeypatch.setenv("SYUNE_AML_BEARER_TOKEN", "second-secret")
    with pytest.raises(RuntimeError, match="exactly one"):
        aml.app_from_environment()


def test_structured_logs_exclude_secrets_identity_and_payload(tmp_path, caplog):
    secret_content = "private payload never log"
    with caplog.at_level("INFO", logger="syune.aml.operations"):
        with TestClient(create_app(settings(tmp_path))) as client:
            response = client.post(
                "/add",
                headers={"Authorization": f"Bearer {TOKEN}"},
                json={"request_id": "private-request", "user_id": "private-user",
                      "session_id": "private-session", "messages": [
                          {"role": "user", "content": secret_content}]},
            )
    assert response.status_code == 200
    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert TOKEN not in rendered
    assert secret_content not in rendered
    assert "private-request" not in rendered and "private-user" not in rendered
    event = json.loads(caplog.records[-1].getMessage())
    assert set(event) == {"event", "method", "path", "status", "duration_ms"}


def test_debug_and_schema_endpoints_are_not_exposed(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_transient_windows_metadata_replace_failure_is_retried(tmp_path, monkeypatch):
    original = aml.Syune.open
    calls = 0

    def transient(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("synthetic atomic replace contention")
        return original(*args, **kwargs)

    monkeypatch.setattr(aml.Syune, "open", transient)
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/search", headers={"Authorization": f"Bearer {TOKEN}"},
                               json={"query": "x", "user_id": "u", "top_k": 1})
    assert response.status_code == 200 and calls == 2


def test_proxy_policy_has_tls_limits_timeouts_and_redacted_logs():
    config = (DEPLOY / "nginx.conf").read_text(encoding="utf-8")
    assert "ssl_protocols TLSv1.2 TLSv1.3" in config
    assert "client_max_body_size 1m" in config
    assert "limit_req_status 429" in config and "Retry-After" in config
    assert "proxy_read_timeout 1800s" in config
    assert "location = /health" in config and "^/(add|search)$" in config
    assert "location = /ready" not in config
    assert "$request_body" not in config and "$http_authorization" not in config
    assert "$args" not in config and "$request_uri" not in config


def test_container_and_vm_are_single_process_hardened_and_frozen():
    dockerfile = (DEPLOY / "Dockerfile").read_text(encoding="utf-8")
    compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
    unit = (DEPLOY / "syune-aml.service").read_text(encoding="utf-8")
    assert "uv sync --frozen --no-dev --no-editable" in dockerfile
    assert "python:3.12.10-slim-bookworm@sha256:" in dockerfile
    assert 'USER 10001:10001' in dockerfile and '"--workers", "1"' in dockerfile
    assert "read_only: true" in compose and "no-new-privileges:true" in compose
    assert "SYUNE_AML_BEARER_TOKEN_FILE" in compose and "SYUNE_AML_BEARER_TOKEN:" not in compose
    assert "nginx:1.28.0-alpine@sha256:" in compose
    assert "--workers 1" in unit and "ProtectSystem=strict" in unit
    assert "LoadCredential=" in unit and "TimeoutStopSec=1860" in unit


def test_locked_manifest_matches_dependency_files():
    import tomllib
    manifest = tomllib.loads((DEPLOY / "deployment-manifest.toml").read_text(encoding="utf-8"))
    for name, key in (("uv.lock", "dependency_lock_sha256"),
                      ("pyproject.toml", "pyproject_sha256")):
        digest = hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
        assert digest == manifest[key]
    assert manifest["runtime"]["application_processes"] == 1
    assert manifest["proposed_version"] == "1.1.1-aml.1"
    assert "@sha256:" in manifest["images"]["application_base"]
    assert "@sha256:" in manifest["images"]["reverse_proxy"]
    assert "uncommitted" in manifest["source_state"]


def test_release_candidate_source_manifest_is_complete_and_current():
    manifest_path = DEPLOY / "source-change-manifest.sha256"
    entries = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, relative = line.split("  ", 1)
        entries[relative] = digest
        canonical = (PROJECT / relative).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical).hexdigest() == digest
    tracked = subprocess.run(
        ["git", "diff", "--name-only", BASELINE], cwd=PROJECT, check=True,
        capture_output=True, text=True,
    ).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"], cwd=PROJECT,
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    expected = {
        path.replace("\\", "/") for path in tracked + untracked
        if path and path != "deploy/aml/source-change-manifest.sha256"
        and "/__pycache__/" not in f"/{path.replace('\\', '/')}"
    }
    assert set(entries) == expected


def test_loopback_startup_readiness_and_shutdown_simulation(tmp_path):
    token_file = (tmp_path / "token").resolve()
    token_file.write_text(TOKEN, encoding="utf-8")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    environment = os.environ.copy()
    environment.update({
        "SYUNE_AML_STATE_ROOT": str((tmp_path / "state").resolve()),
        "SYUNE_AML_BEARER_TOKEN_FILE": str(token_file),
        "SYUNE_AML_MIN_FREE_BYTES": "0",
    })
    environment.pop("SYUNE_AML_BEARER_TOKEN", None)
    command = [sys.executable, "-m", "uvicorn", "syune.adapters.aml.v1:app_from_environment",
               "--factory", "--host", "127.0.0.1", "--port", str(port), "--workers", "1",
               "--no-access-log", "--no-server-header"]
    process = subprocess.Popen(command, cwd=PROJECT, env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 20
        payload = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                pytest.fail(f"uvicorn exited early: {stdout} {stderr}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/ready", timeout=1) as response:
                    payload = json.loads(response.read())
                    break
            except OSError:
                time.sleep(0.1)
        assert payload == {"status": "ready"}
    finally:
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=15)
    assert process.returncode is not None


def test_runbook_requires_manual_marked_cleanup_and_version_disclosure():
    runbook = (PROJECT / "docs" / "AML_DEPLOYMENT_RUNBOOK.md").read_text(encoding="utf-8")
    assert "No automatic destructive schedule" in runbook
    assert "within 30 days" in runbook
    assert "must never be represented as that" in runbook
    assert "development or personal state" in runbook
