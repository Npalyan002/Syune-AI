"""Cross-platform acceptance of the built SYUNE wheel."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv

EXPECTED = {
    "syune_health", "syune_remember", "syune_context", "syune_revise",
    "syune_forget", "syune_history", "syune_audit", "syune_model",
}
SECRET_NAMES = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> tuple[str, str]:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(
            f"command failed ({result.returncode}): {command!r}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result.stdout, result.stderr


async def handshake(command: str, args: list[str], env: dict[str, str], cwd: Path) -> None:
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(command=command, args=args, env=env, cwd=str(cwd))
    async with Client(params) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        assert names == EXPECTED, (names, EXPECTED)
        health = await client.call_tool("syune_health")
        assert not health.is_error
        assert health.structured_content
        assert health.structured_content["version"] == "2.0.0"
        assert health.structured_content["transport"] == "stdio"


def installed_acceptance() -> None:
    import syune

    assert syune.__version__ == "2.0.0"
    work = Path(tempfile.mkdtemp(prefix="syune acceptance "))
    try:
        env = dict(os.environ)
        for name in ("SYUNE_STATE_ROOT", "SYUNE_CONFIG", "XDG_STATE_HOME", "LOCALAPPDATA"):
            env.pop(name, None)
        for name in SECRET_NAMES:
            env[name] = f"SYUNE_ACCEPTANCE_SECRET_{name}"
        home = work / "Fake Home"
        home.mkdir()
        env["HOME"] = str(home)

        if sys.platform == "win32":
            local = work / "Local App Data"
            env["LOCALAPPDATA"] = str(local)
            expected = local / "SYUNE" / "default"
        elif sys.platform == "darwin":
            expected = home / "Library" / "Application Support" / "SYUNE" / "default"
        else:
            xdg = work / "XDG State"
            env["XDG_STATE_HOME"] = str(xdg)
            expected = xdg / "syune" / "default"

        quick_out, quick_err = run([sys.executable, "-m", "syune.quickstart"], cwd=work, env=env)
        assert json.loads(quick_out.strip().splitlines()[-1])["closed"] is True

        setup_out, setup_err = run(
            [sys.executable, "-m", "syune.cli.app", "setup", "--host", "generic", "--json"],
            cwd=work, env=env,
        )
        first = json.loads(setup_out)
        assert first["state_root"] == str(expected.resolve())
        assert first["state_created"] is True
        assert first["third_party_config_modified"] is False
        assert first["mcp_validation"]["handshake"] == "PASS"
        assert set(first["mcp_validation"]["tools"]) == EXPECTED

        generated = first["generated_config"]
        assert Path(generated["command"]).is_absolute()
        assert Path(generated["env"]["SYUNE_STATE_ROOT"]).is_absolute()
        assert generated["args"] == ["-m", "syune.gateway.mcp"]
        assert Path(first["artifact"]).resolve().is_relative_to(expected.resolve())
        assert expected.exists()
        assert not Path(syune.__file__).resolve().is_relative_to(expected)

        doctor_out, doctor_err = run(
            [sys.executable, "-m", "syune.cli.app", "doctor", "--json"], cwd=work, env=env
        )
        assert json.loads(doctor_out)["overall"] == "READY"

        mcp_env = dict(env)
        mcp_env.update(generated["env"])
        asyncio.run(handshake(generated["command"], generated["args"], mcp_env, work))

        second_out, second_err = run(
            [sys.executable, "-m", "syune.cli.app", "setup", "--host", "generic", "--json"],
            cwd=work, env=env,
        )
        second = json.loads(second_out)
        assert second["state_created"] is False
        assert second["instance_id"] == first["instance_id"]
        repeat_doctor, repeat_err = run(
            [sys.executable, "-m", "syune.cli.app", "doctor", "--json"], cwd=work, env=env
        )
        assert json.loads(repeat_doctor)["overall"] == "READY"

        if sys.platform.startswith("linux"):
            env.pop("XDG_STATE_HOME", None)
            fallback = home / ".local" / "state" / "syune" / "default"
            fallback_out, fallback_err = run(
                [sys.executable, "-m", "syune.cli.app", "setup", "--host", "generic", "--json"],
                cwd=work, env=env,
            )
            fallback_result = json.loads(fallback_out)
            assert fallback_result["state_root"] == str(fallback.resolve())
            assert fallback_result["mcp_validation"]["handshake"] == "PASS"
            fallback_doctor, _ = run(
                [sys.executable, "-m", "syune.cli.app", "doctor", "--json"], cwd=work, env=env
            )
            assert json.loads(fallback_doctor)["overall"] == "READY"

        combined = "\n".join(
            (quick_out, quick_err, setup_out, setup_err, doctor_out, doctor_err,
             second_out, second_err, repeat_doctor, repeat_err)
        )
        for name in SECRET_NAMES:
            assert env[name] not in combined
        assert not any(work.parent.glob("syune.sqlite3"))
        print(json.dumps({
            "platform": sys.platform,
            "version": syune.__version__,
            "install": "PASS",
            "quickstart": "PASS",
            "setup": "PASS",
            "doctor": "READY",
            "mcp_handshake": "PASS",
            "health": "PASS",
            "tools": "8/8",
            "persistence": "PASS",
            "state_root": str(expected.resolve()),
            "third_party_config_modified": False,
            "model_api_required": False,
        }, sort_keys=True))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def bootstrap(wheel_dir: Path) -> None:
    wheels = list(wheel_dir.resolve().glob("syune-2.0.0-py3-none-any.whl"))
    assert len(wheels) == 1, wheels
    root = Path(tempfile.mkdtemp(prefix="syune wheel acceptance "))
    try:
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [str(python), "-m", "pip", "install", str(wheels[0])],
            check=True,
        )
        subprocess.run(
            [str(python), str(Path(__file__).resolve()), "--installed"],
            check=True,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel-dir", type=Path)
    parser.add_argument("--installed", action="store_true")
    options = parser.parse_args()
    if options.installed:
        installed_acceptance()
    else:
        if options.wheel_dir is None:
            parser.error("--wheel-dir is required")
        bootstrap(options.wheel_dir)
