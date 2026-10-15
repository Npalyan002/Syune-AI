"""Orchestrate disposable AML-09B.1 Linux Compose load configurations."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path


def run(command: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, env=env, text=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, choices=(3000, 10000), required=True)
    parser.add_argument("--concurrency", type=int, choices=(4, 8, 16, 32), required=True)
    parser.add_argument("--port", type=int, default=18443)
    parser.add_argument("--uvicorn", type=int, default=40)
    parser.add_argument("--nginx-rate", default="64r/s")
    parser.add_argument("--nginx-burst", type=int, default=64)
    parser.add_argument("--nginx-connections", type=int, default=40)
    parser.add_argument("--label", default="candidate")
    parser.add_argument("--settle-seconds", type=float, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    project = f"aml09b1-{args.label}-{args.records}-c{args.concurrency}"
    compose_file = Path("deploy/aml09b1/compose.yaml")
    compose = ["docker", "compose", "-f", str(compose_file), "-p", project]
    env = os.environ | {
        "AML_APP_CONCURRENCY": str(args.concurrency),
        "AML_UVICORN_LIMIT": str(args.uvicorn),
        "AML_NGINX_RATE": args.nginx_rate,
        "AML_NGINX_BURST": str(args.nginx_burst),
        "AML_NGINX_CONNECTIONS": str(args.nginx_connections),
        "AML_HOST_PORT": str(args.port),
    }
    started = time.perf_counter()
    try:
        run([*compose, "up", "-d", "--no-build"], env=env)
        cold_start_ms = (time.perf_counter() - started) * 1000
        roles = {
            role: subprocess.check_output([*compose, "ps", "-q", role], env=env, text=True).strip()
            for role in ("app", "proxy")
        }
        run([
            "python3", "benchmarks/aml09b1_e2e.py", "--records", str(args.records),
            "--project", project, "--compose", str(compose_file), "--output", str(args.output),
            "--url", f"https://127.0.0.1:{args.port}",
            "--settle-seconds", str(args.settle_seconds),
        ], env=env)
        volume = f"{project}_aml09b1_state"
        mount = subprocess.check_output(
            ["docker", "volume", "inspect", "--format", "{{.Mountpoint}}", volume], text=True
        ).strip()
        disk_bytes = int(subprocess.check_output(["du", "-sb", mount], text=True).split()[0])
        report = json.loads(args.output.read_text())
        report.update({
            "settings": {"application": args.concurrency, "uvicorn": args.uvicorn,
                         "nginx_rate": args.nginx_rate, "nginx_burst": args.nginx_burst,
                         "nginx_connections": args.nginx_connections},
            "cold_start_ms": round(cold_start_ms, 3),
            "state_disk_bytes": disk_bytes,
            "container_roles": roles,
        })
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    finally:
        subprocess.run([*compose, "down", "-v", "--remove-orphans"], env=env, check=False)


if __name__ == "__main__":
    main()
