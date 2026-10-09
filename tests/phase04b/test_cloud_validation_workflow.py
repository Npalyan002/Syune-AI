from __future__ import annotations

import re
from pathlib import Path

from deploy.aml.cloud_container_probe import (
    PRIVATE_MARKER,
    add_payload,
    native_100_search_payload,
)


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "aml-container-validation.yml"


def test_workflow_is_manual_least_privilege_and_immutable():
    text = WORKFLOW.read_text(encoding="utf-8")
    trigger = text.split("permissions:", 1)[0]
    assert "workflow_dispatch:" in trigger
    assert "workflow_call:" in trigger
    assert "pull_request:" not in trigger and "push:" not in trigger
    assert re.search(r"permissions:\s*\n\s+contents: read", text)
    actions = re.findall(r"uses:\s*([^\s]+)", text)
    assert actions == [
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
    ]
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) for action in actions)
    assert "secrets." not in text
    assert "upload-artifact" not in text and "id-token: write" not in text


def test_default_registered_proxy_can_only_call_container_job_manually():
    text = (ROOT / ".github" / "workflows" / "cross-platform-acceptance.yml").read_text(
        encoding="utf-8"
    )
    assert "if: ${{ github.event_name == 'workflow_dispatch' }}" in text
    assert "uses: ./.github/workflows/aml-container-validation.yml" in text
    actions = re.findall(r"uses:\s*(actions/[^\s]+)", text)
    assert actions == [
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
    ]


def test_workflow_covers_required_container_gates_without_printing_values():
    text = WORKFLOW.read_text(encoding="utf-8")
    for required in (
        "docker compose config --quiet",
        "docker compose build --pull app",
        "docker compose up --detach --no-build",
        "docker compose exec -T proxy nginx -t",
        "--phase initial",
        "--phase seed-native-100",
        "--phase native-100",
        "--phase after-restart",
        "--phase persistence",
        "--phase limits",
        "docker compose down --volumes --remove-orphans",
        "docker image inspect",
        "docker save",
        "uv run python -m pytest -q",
    ):
        assert required in text
    assert "set -x" not in text
    assert PRIVATE_MARKER not in text


def test_compose_has_explicit_resource_and_filesystem_bounds():
    text = (ROOT / "deploy" / "aml" / "compose.yaml").read_text(encoding="utf-8")
    assert text.count("read_only: true") == 2
    assert "image: syune-aml-rc:local" in text
    assert "mem_limit: 2g" in text and "mem_limit: 256m" in text
    assert "cpus: 2.0" in text and "cpus: 1.0" in text
    assert "pids_limit: 256" in text and "pids_limit: 128" in text
    assert text.count("no-new-privileges:true") == 2


def test_synthetic_probe_preserves_order_and_fills_native_top_100_pool():
    messages = [message for batch in range(5) for message in add_payload(batch)["messages"]]
    assert len(messages) == 100
    assert [message["content"].rsplit(" ", 1)[-1] for message in messages[:20]] == [
        str(index) for index in range(20)
    ]
    assert all(PRIVATE_MARKER in message["content"] for message in messages)
    assert native_100_search_payload()["top_k"] == 100
