"""Repeatable local lean-path benchmark; no provider or learning dependency."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from time import perf_counter

from syune import ContextRequest, RememberRequest, RuntimeMode, Syune
from syune.product.config import load_config
from syune.product.state import initialize_state


def percentile(values, p):
    ordered = sorted(values); return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p))]


def measure(operation, iterations):
    values = []
    for _ in range(iterations):
        start = perf_counter(); operation(); values.append((perf_counter() - start) * 1000)
    return {"p50_ms": round(median(values), 3), "p95_ms": round(percentile(values, .95), 3),
            "p99_ms": round(percentile(values, .99), 3)}


def run(root: Path, iterations: int = 100):
    config = load_config(cli_state_root=root.resolve()); initialize_state(config)
    with Syune.open(state_root=root.resolve(), mode=RuntimeMode.TEST) as client:
        client.remember(RememberRequest("governed context preserves provenance and authorization"))
        result = {
            "remember": measure(lambda: client.remember("benchmark governed memory"), iterations),
            "recall": measure(lambda: client.recall("governed context"), iterations),
            "context": measure(lambda: client.context(ContextRequest("governed context", max_chars=2000)), iterations),
            "authorized_context": measure(lambda: client.context(ContextRequest("governed context", user_id="bench")), iterations),
            "model_without_learning": "covered by deterministic ModelGateway tests; provider-specific latency excluded",
        }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path); parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args(); print(json.dumps(run(args.root, args.iterations), indent=2, sort_keys=True))
