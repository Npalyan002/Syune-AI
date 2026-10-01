from __future__ import annotations

import json
from pathlib import Path


def load_result(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(baseline: dict, candidate: dict) -> dict:
    def delta(path: tuple[str, ...]):
        left, right = baseline, candidate
        for key in path: left, right = left.get(key), right.get(key)
        return {"baseline": left, "candidate": right, "delta": right - left if left is not None and right is not None else None}
    return {
        "quality_delta": {"recall": delta(("metrics", "recall")), "precision": delta(("metrics", "precision")), "mrr": delta(("metrics", "mrr"))},
        "task_success_delta": delta(("task_success",)), "context_delta": delta(("metrics", "context_records_mean")),
        "latency_delta": delta(("latency_ms", "p95")), "token_delta": delta(("tokens", "total")),
        "cost_delta": {"baseline": baseline["cost"], "candidate": candidate["cost"], "delta": None},
        "storage_delta": {"baseline": baseline["storage_after"], "candidate": candidate["storage_after"], "delta": None},
        "permission_violations": delta(("metrics", "permission_violation_count")),
        "false_memory": delta(("metrics", "false_memory_count")),
    }


def evaluate_policy(comparison: dict, policy: dict) -> dict:
    checks = {
        "task_success": comparison["task_success_delta"]["delta"] is None or comparison["task_success_delta"]["delta"] >= -policy["max_task_success_regression"],
        "recall": comparison["quality_delta"]["recall"]["delta"] is None or comparison["quality_delta"]["recall"]["delta"] >= -policy["max_recall_regression"],
        "false_memory": comparison["false_memory"]["candidate"] <= policy["max_false_memory_count"],
        "p95_latency": comparison["latency_delta"]["candidate"] is None or comparison["latency_delta"]["candidate"] <= policy["max_p95_latency_ms"],
        "tokens": comparison["token_delta"]["candidate"] is None or comparison["token_delta"]["candidate"] <= policy["max_total_tokens"],
        "permission": comparison["permission_violations"]["candidate"] == policy["required_permission_violations"],
    }
    return {"passed": all(checks.values()), "checks": checks, "hard_gates": ["permission"]}


def markdown_report(result: dict) -> str:
    metrics = result["metrics"]
    return (f"# Benchmark run {result['run_id']}\n\n"
            f"- System: `{result['system']}` ({result['adapter_status']})\n"
            f"- Dataset: `{result['dataset_id']}@{result['dataset_version']}` seed `{result['seed']}`\n"
            f"- Cases: {result['case_count']} ({result['passed']} passed, {result['failed']} failed)\n"
            f"- Task success: {result['task_success']:.3f}\n"
            f"- Recall / precision / MRR: {metrics['recall']:.3f} / {metrics['precision']:.3f} / {metrics['mrr']:.3f}\n"
            f"- P95 retrieval latency: {result['latency_ms']['p95']} ms\n"
            f"- Cost status: `{result['cost']['status']}`\n"
            f"- Errors: {len(result['errors'])}\n"
            f"- Unsupported: {', '.join(result['unsupported_capabilities']) or 'none'}\n")
