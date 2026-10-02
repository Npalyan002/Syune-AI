"""Safe persistent setup and local readiness diagnostics for Lean SYUNE."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import threading
from typing import Callable

from syune.release import RELEASE_VERSION
from .config import SyuneConfig
from .state import initialize_state, load_metadata, missing_databases

HOSTS = ("codex", "claude-code", "claude-desktop", "generic", "python")
MCP_TOOLS = frozenset({"syune_health", "syune_remember", "syune_context", "syune_revise",
                       "syune_forget", "syune_history", "syune_audit", "syune_model"})
HOST_DOCS = {
    "codex": "https://developers.openai.com/codex/mcp",
    "claude-code": "https://docs.anthropic.com/en/docs/claude-code/mcp",
    "claude-desktop": "https://modelcontextprotocol.io/quickstart/user",
    "generic": "https://modelcontextprotocol.io/clients",
}


class ConnectFailure(ValueError):
    """Expected, actionable setup or doctor failure."""

    def __init__(self, code: str, message: str, fix: str):
        super().__init__(message)
        self.code, self.message, self.fix = code, message, fix


@dataclass(frozen=True, slots=True)
class RuntimeCommand:
    command: str
    args: tuple[str, ...]


def _safe_environment(state_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    # Do not let a caller replace the package or interpreter used by the MCP subprocess.
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["SYUNE_STATE_ROOT"] = str(state_root)
    return env


def discover_runtime() -> RuntimeCommand:
    executable = Path(sys.executable).resolve(strict=True)
    if not executable.is_file():
        raise ConnectFailure("EXECUTABLE_NOT_FOUND", "Python executable is unavailable",
                             "reinstall SYUNE in a Python 3.12+ environment")

    return RuntimeCommand(str(executable), ("-m", "syune.gateway.mcp"))


async def _probe(command: RuntimeCommand, state_root: Path) -> dict[str, object]:
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(command=command.command, args=list(command.args),
        env=_safe_environment(state_root), cwd=str(state_root))
    async with Client(params) as client:
        tools = {item.name for item in (await client.list_tools()).tools}
        health = await client.call_tool("syune_health")
        if health.is_error or health.structured_content is None:
            raise ConnectFailure("MCP_HEALTH_FAILED", "syune_health returned an error",
                                 "run syune doctor --debug and inspect the state configuration")
        missing = sorted(MCP_TOOLS - tools)
        if missing:
            raise ConnectFailure("MCP_TOOL_CONTRACT_MISMATCH",
                "canonical Lean tools are missing: " + ", ".join(missing),
                "reinstall the matching SYUNE package version")
        data = health.structured_content
        if data.get("version") != RELEASE_VERSION or data.get("transport") != "stdio":
            raise ConnectFailure("MCP_HEALTH_MISMATCH", "MCP health metadata is incompatible",
                                 "verify the generated command uses the active SYUNE environment")
        return {"handshake": "PASS", "health": "PASS", "tools": sorted(tools),
                "canonical_tools": len(MCP_TOOLS), "additional_tools": sorted(tools - MCP_TOOLS)}


def probe_mcp(command: RuntimeCommand, state_root: Path, *, timeout: float = 20) -> dict[str, object]:
    try:
        return asyncio.run(asyncio.wait_for(_probe(command, state_root), timeout))
    except ConnectFailure:
        raise
    except TimeoutError as exc:
        raise ConnectFailure("MCP_HANDSHAKE_TIMEOUT", "MCP handshake timed out",
                             "check executable permissions and run syune doctor --debug") from exc
    except Exception as exc:
        raise ConnectFailure("MCP_HANDSHAKE_FAILED",
            f"MCP server did not become ready ({type(exc).__name__})",
            "run syune doctor --debug and verify the generated command") from exc


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if os.name != "nt": temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        if temporary.exists(): os.remove(temporary)


def _sdk_example(state_root: Path) -> str:
    return ("from pathlib import Path\nfrom syune import Syune\n\n"
            f"state = Path({str(state_root)!r})\n\n"
            "with Syune.open(state_root=state) as syune:\n    print(syune.health().data)\n")


def _choose_host(input_fn: Callable[[str], str]) -> str:
    labels = ("Codex", "Claude Code", "Claude Desktop", "Generic MCP", "Python SDK")
    print("SYUNE Setup\n\nChoose integration:")
    for number, label in enumerate(labels, 1): print(f"  {number}. {label}")
    raw = input_fn("Selection: ").strip()
    try: return HOSTS[int(raw) - 1]
    except (ValueError, IndexError) as exc:
        raise ConnectFailure("INVALID_HOST", "selection must be 1 through 5", "run syune setup again") from exc


def _acquire_setup_lock(root: Path) -> Path:
    root.parent.mkdir(parents=True, exist_ok=True)
    lock = root.parent / f".{root.name}.syune-setup.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ConnectFailure("SETUP_IN_PROGRESS", "another setup is using this state root",
                             f"wait for it to finish; if it crashed, remove {lock}") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(f"pid={os.getpid()}\n")
    return lock


def setup(config: SyuneConfig, host: str | None, *, input_fn: Callable[[str], str] = input) -> dict[str, object]:
    selected = host or _choose_host(input_fn)
    if selected not in HOSTS:
        raise ConnectFailure("INVALID_HOST", f"unsupported host: {selected}",
                             "choose codex, claude-code, claude-desktop, generic, or python")
    root = config.state.root
    lock = _acquire_setup_lock(root)
    try:
        metadata, created = initialize_state(config)
        command = discover_runtime()
        mcp = probe_mcp(command, root) if selected != "python" else None
        common: dict[str, object] = {
            "product": "SYUNE", "version": RELEASE_VERSION, "host": selected,
            "state_root": str(root), "state_initialized": True, "state_created": created,
            "instance_id": str(metadata.instance_id), "host_model_mode": "READY",
            "separate_llm_api_required": False, "model_gateway": "NOT_CONFIGURED_OPTIONAL",
            "mcp_validation": mcp,
        }
        if selected == "python":
            example = _sdk_example(root)
            path = root / "artifacts" / "connect" / "python-sdk.py"
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
            temporary.write_text(example, encoding="utf-8"); temporary.replace(path)
            return common | {"integration": "python-sdk", "sdk_example": example,
                             "artifact": str(path), "generated_config": None,
                             "next_action": "use the generated example in your Python application"}
        generated = {"command": command.command, "args": list(command.args),
                     "env": {"SYUNE_STATE_ROOT": str(root)}}
        artifact = root / "artifacts" / "connect" / f"{selected}.json"
        _atomic_json(artifact, generated)
        return common | {"integration": "stdio-mcp", "generated_config": generated,
                         "artifact": str(artifact), "host_documentation": HOST_DOCS[selected],
                         "next_action": "register the generated command/args/env tuple using the host's current MCP documentation",
                         "third_party_config_modified": False}
    finally:
        if lock.exists(): os.remove(lock)


def _check(name: str, status: str, detail: str, *, fix: str | None = None) -> dict[str, object]:
    value: dict[str, object] = {"name": name, "status": status, "detail": detail}
    if fix: value["fix"] = fix
    return value


def doctor(config: SyuneConfig) -> tuple[dict[str, object], bool]:
    checks: list[dict[str, object]] = []
    checks.append(_check("package.version", "PASS", RELEASE_VERSION))
    root = config.state.root
    if not root.exists():
        checks.append(_check("state.initialized", "FAIL", "STATE_ROOT_NOT_INITIALIZED",
                             fix=f"syune setup --state-root {str(root)!r}"))
        checks.extend((_check("model.host_mode", "READY", "no provider credential required"),
                       _check("model.gateway", "OPTIONAL", "not configured by setup")))
        return _doctor_result(config, checks, None), False
    readable = os.access(root, os.R_OK)
    writable = os.access(root, os.W_OK)
    checks.append(_check("state.readable", "PASS" if readable else "FAIL", str(root),
                         fix=None if readable else "grant read permission to the state root"))
    checks.append(_check("state.writable", "PASS" if writable else "FAIL", str(root),
                         fix=None if writable else "grant write permission to the state root"))
    try:
        metadata = load_metadata(root)
        missing = missing_databases(root)
        if missing: raise ValueError("missing databases: " + ", ".join(missing))
        checks.append(_check("state.initialized", "PASS", f"schema {metadata.state_schema_version}"))
        command = discover_runtime()
        checks.append(_check("mcp.executable", "PASS", command.command))
        probe = probe_mcp(command, root)
        checks.extend((_check("mcp.handshake", "PASS", "stdio initialization succeeded"),
                       _check("mcp.health", "PASS", "syune_health succeeded"),
                       _check("mcp.tools", "PASS", f"{probe['canonical_tools']}/{len(MCP_TOOLS)} canonical tools")))
    except ConnectFailure as exc:
        checks.append(_check("mcp", "FAIL", exc.code, fix=exc.fix)); probe = None
    except FileNotFoundError:
        checks.append(_check("state.initialized", "FAIL", "STATE_ROOT_NOT_INITIALIZED", fix="syune setup")); probe = None
    except (ValueError, PermissionError) as exc:
        checks.append(_check("state.compatible", "FAIL", f"STATE_INVALID: {str(exc)[:160]}",
                             fix="preserve the state root and restore a compatible backup")); probe = None
    checks.extend((_check("model.host_mode", "READY", "no provider credential required"),
                   _check("model.gateway", "OPTIONAL", "not configured by setup")))
    ready = all(item["status"] not in ("FAIL",) for item in checks)
    return _doctor_result(config, checks, probe), ready


def _doctor_result(config: SyuneConfig, checks: list[dict[str, object]],
                   probe: dict[str, object] | None) -> dict[str, object]:
    ready = all(item["status"] != "FAIL" for item in checks)
    return {"product": "SYUNE Doctor", "version": RELEASE_VERSION,
            "state_root": str(config.state.root), "checks": checks,
            "mcp": probe, "host_model_mode": "READY",
            "separate_llm_api_required": False,
            "model_gateway": "NOT_CONFIGURED_OPTIONAL", "overall": "READY" if ready else "NOT_READY"}


__all__ = ["ConnectFailure", "HOSTS", "MCP_TOOLS", "RuntimeCommand", "discover_runtime",
           "doctor", "probe_mcp", "setup"]
