"""Synthetic HTTPS load probe for the isolated AML-09B.1 Compose stack."""
from __future__ import annotations

import argparse
import json
import ssl
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TOKEN = "aml09b1-dummy-local-token"
SSL = ssl._create_unverified_context()


def request(url: str, path: str, payload: dict | None = None) -> tuple[int, bytes, float]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if body is not None: headers["Content-Type"] = "application/json"
    call = urllib.request.Request(url + path, data=body, headers=headers,
                                  method="POST" if body is not None else "GET")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(call, context=SSL, timeout=190) as response:
            return response.status, response.read(), (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), (time.perf_counter() - started) * 1000
    except urllib.error.URLError as exc:
        return 0, str(exc.reason).encode(), (time.perf_counter() - started) * 1000


def pct(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    pick = lambda q: ordered[min(len(ordered) - 1, int(len(ordered) * q))]
    return {"p50_ms": round(statistics.median(ordered), 3),
            "p95_ms": round(pick(.95), 3), "p99_ms": round(pick(.99), 3)}


def size_bytes(value: str) -> float:
    number, unit = value.strip().split()[:2] if " " in value.strip() else (value[:-3], value[-3:])
    factors = {"B": 1, "kB": 1000, "KB": 1000, "KiB": 1024, "MB": 1000**2,
               "MiB": 1024**2, "GB": 1000**3, "GiB": 1024**3}
    return float(number) * factors.get(unit, 1)


class ResourceMonitor:
    def __init__(self, ids: list[str]):
        self.ids, self.stop = ids, threading.Event()
        self.samples: dict[str, dict[str, float]] = {item: {"cpu_percent": 0, "rss_bytes": 0} for item in ids}
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self.stop.wait(.25):
            result = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{json .}}", *self.ids],
                                    capture_output=True, text=True)
            for line in result.stdout.splitlines():
                try:
                    row = json.loads(line); cid = row["ID"]
                    cpu = float(row["CPUPerc"].rstrip("%")); rss = size_bytes(row["MemUsage"].split("/")[0].strip())
                    full_id = next((item for item in self.ids if item.startswith(cid)), None)
                    if full_id is not None:
                        self.samples[full_id]["cpu_percent"] = max(self.samples[full_id]["cpu_percent"], cpu)
                        self.samples[full_id]["rss_bytes"] = max(self.samples[full_id]["rss_bytes"], rss)
                except (KeyError, ValueError, json.JSONDecodeError):
                    pass

    def __enter__(self): self.thread.start(); return self
    def __exit__(self, *_): self.stop.set(); self.thread.join(timeout=3)


def classify(status: int, body: bytes) -> str:
    if status == 429: return "nginx_429"
    if status == 503 and b"service capacity exhausted" in body: return "app_503"
    if status == 503: return "uvicorn_or_proxy_503"
    if status >= 500: return "other_5xx"
    if status == 0: return "transport_error"
    return str(status)


def container_logs(container_id: str) -> list[str]:
    result = subprocess.run(["docker", "logs", container_id], capture_output=True, text=True)
    return (result.stdout + result.stderr).splitlines()


def event_count(lines: list[str], event: str) -> int:
    return sum(f'"event":"{event}"' in line for line in lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://127.0.0.1:18443")
    parser.add_argument("--records", type=int, required=True)
    parser.add_argument("--bursts", type=int, default=3)
    parser.add_argument("--settle-seconds", type=float, default=0)
    parser.add_argument("--project", required=True)
    parser.add_argument("--compose", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compose = ["docker", "compose", "-f", str(args.compose), "-p", args.project]
    ids = subprocess.check_output([*compose, "ps", "-q"], text=True).split()
    seed_latencies = []
    seed_retries = 0
    startup_retries = 0
    for offset in range(0, args.records, 20):
        payload = {"request_id": f"seed-{offset//20}", "user_id": "load-user",
                   "session_id": "load-session", "messages": [
                       {"role": "user", "content": f"synthetic memory {offset+i} alpha marker"}
                       for i in range(min(20, args.records-offset))]}
        while True:
            status, body, latency = request(args.url, "/add", payload)
            if status == 0 and startup_retries < 30:
                startup_retries += 1
                time.sleep(.2)
                continue
            if status != 429:
                break
            seed_retries += 1
            time.sleep(.15)
        seed_latencies.append(latency)
        if status != 200: raise RuntimeError(f"seed failed: {status} {body[:200]!r}")
    app_id = subprocess.check_output([*compose, "ps", "-q", "app"], text=True).strip()
    rebuilds_before_warm = event_count(container_logs(app_id), "index_rebuild")
    warm = [request(args.url, "/search", {"query": "alpha marker", "user_id": "load-user", "top_k": 100})
            for _ in range(10)]
    warm_search_rebuild_delta = event_count(container_logs(app_id), "index_rebuild") - rebuilds_before_warm
    time.sleep(args.settle_seconds)
    outcomes: list[tuple[str, int, bytes, float, str | None]] = []
    load_started = time.perf_counter()
    with ResourceMonitor(ids) as monitor:
        for burst in range(args.bursts):
            def invoke(index: int):
                if index < 16:
                    content = f"capacity visibility {burst} {index}"
                    status, body, latency = request(args.url, "/add", {
                        "request_id": f"capacity-{burst}-{index}", "user_id": "load-user",
                        "session_id": "load-session", "messages": [{"role": "user", "content": content}]})
                    return "add", status, body, latency, content
                status, body, latency = request(args.url, "/search", {
                    "query": "alpha marker", "user_id": "load-user", "top_k": 100})
                return "search", status, body, latency, None
            with ThreadPoolExecutor(max_workers=32) as pool:
                outcomes.extend(pool.map(invoke, range(32)))
    load_seconds = time.perf_counter() - load_started
    committed = [item[4] for item in outcomes if item[0] == "add" and item[1] == 200]
    visibility_failures = 0
    for content in committed:
        status, body, _ = request(args.url, "/search", {"query": content, "user_id": "load-user", "top_k": 100})
        rows = json.loads(body).get("data", []) if status == 200 else []
        visibility_failures += not any(row.get("content") == content for row in rows)
    replay_payload = {"request_id": "global-idempotency", "user_id": "isolation-a", "session_id": "s",
                      "messages": [{"role": "user", "content": "private isolation marker"}]}
    idem = [request(args.url, "/add", replay_payload)[0], request(args.url, "/add", replay_payload)[0]]
    conflict = request(args.url, "/add", replay_payload | {"user_id": "isolation-b"})[0]
    isolated_status, isolated_body, _ = request(args.url, "/search", {
        "query": "private isolation marker", "user_id": "isolation-b", "top_k": 100})
    isolated_rows = json.loads(isolated_body).get("data", []) if isolated_status == 200 else None
    pre_restart_events = []
    for line in container_logs(app_id):
        start = line.find("{")
        if start >= 0:
            try: pre_restart_events.append(json.loads(line[start:]))
            except json.JSONDecodeError: pass
    cache_metrics = next((event for event in reversed(pre_restart_events)
                          if event.get("event") == "policy_partition_cache"), {})
    cache_metrics.pop("event", None)
    restart_started = time.perf_counter(); subprocess.run([*compose, "restart", "app"], check=True, capture_output=True)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if request(args.url, "/health")[0] == 200: break
        time.sleep(.5)
    restart_ms = (time.perf_counter() - restart_started) * 1000
    recovery = request(args.url, "/search", {"query": "alpha marker", "user_id": "load-user", "top_k": 100})
    app_id = subprocess.check_output([*compose, "ps", "-q", "app"], text=True).strip()
    logs = container_logs(app_id)
    events = []
    for line in logs:
        start = line.find("{")
        if start >= 0:
            try: events.append(json.loads(line[start:]))
            except json.JSONDecodeError: pass
    queue = [float(event["duration_ms"]) for event in events if event.get("event") == "queue_wait"]
    report = {
        "records": args.records, "bursts": args.bursts,
        "seed": pct(seed_latencies), "seed_429_retries": seed_retries,
        "proxy_startup_retries": startup_retries,
        "warm_search": pct([item[2] for item in warm]),
        "mixed_add": pct([item[3] for item in outcomes if item[0] == "add"]),
        "mixed_search": pct([item[3] for item in outcomes if item[0] == "search"]),
        "http_distribution": dict(Counter(item[1] for item in outcomes)),
        "error_attribution": dict(Counter(classify(item[1], item[2]) for item in outcomes)),
        "throughput_rps": round(len(outcomes)/load_seconds, 3),
        "queue_wait": pct(queue) if queue else None,
        "index_rebuild_events": sum(event.get("event") == "index_rebuild" for event in events),
        "index_rebuild_details": [
            {"duration_ms": event.get("duration_ms"), "recovery": event.get("recovery")}
            for event in events if event.get("event") == "index_rebuild"
        ],
        "warm_search_rebuild_delta": warm_search_rebuild_delta,
        "sqlite_contention_events": sum("locked" in line.lower() or "busy" in line.lower() for line in logs),
        "committed_adds_checked": len(committed), "visibility_failures": visibility_failures,
        "idempotency_statuses": idem, "global_conflict_status": conflict,
        "cross_user_isolation_rows": isolated_rows,
        "restart_ms": round(restart_ms, 3), "recovery_status": recovery[0],
        "policy_partition_cache": cache_metrics,
        "resources_by_container_id": monitor.samples,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__": main()
