from __future__ import annotations

import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .adapters import adapter_for
from .model import Baseline, Dataset, StateMode

BENCHMARK_VERSION = "1.0.0"


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values: return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def validate_result(result: dict) -> None:
    required = {"run_id", "timestamp", "git_commit", "working_tree_state", "system", "system_version",
                "adapter_version", "model", "model_version", "model_parameters", "dataset_id", "dataset_version",
                "seed", "benchmark", "benchmark_version", "case_count", "passed", "failed", "task_success",
                "metrics", "tokens", "latency_ms", "cost", "storage_before", "storage_after", "errors",
                "warnings", "unsupported_capabilities", "samples", "dataset_metadata"}
    missing = required - result.keys()
    if missing: raise ValueError(f"result schema missing fields: {sorted(missing)}")
    if result["passed"] + result["failed"] != result["case_count"]:
        raise ValueError("passed + failed must equal case_count")
    if result["cost"]["status"] not in {"MEASURED_COST", "ESTIMATED_COST", "UNKNOWN_COST"}:
        raise ValueError("invalid cost status")


def write_raw_result(result: dict, directory: Path) -> Path:
    validate_result(result)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{result['run_id']}.json"
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


class BenchmarkRunner:
    def __init__(self, repository_root: Path): self.root = repository_root

    def _git(self) -> tuple[str, str]:
        try:
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()
            state = "DIRTY" if subprocess.run(["git", "status", "--porcelain"], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip() else "CLEAN"
            return commit, state
        except (OSError, subprocess.SubprocessError): return "UNKNOWN", "UNKNOWN"

    def run(self, baseline: Baseline, dataset: Dataset, family: str | None = None, repeats: int = 1) -> dict:
        adapter = adapter_for(baseline)
        commit, tree = self._git()
        selected = [case for case in dataset.cases if family is None or case.family == family]
        errors: list[dict[str, str]] = []
        warnings: list[str] = []
        samples: list[dict] = []
        all_latencies: list[float] = []
        total_relevant = total_retrieved = true_positive = reciprocal_sum = 0.0
        passed = permission_violations = false_memories = provenance_hits = 0
        storage_before = adapter.export_state_metrics()
        adapter.prepare()
        try:
            if adapter.status != "READY":
                for case in selected:
                    response = adapter.execute_task(case)
                    errors.append({"case_id": case.case_id, **(response.error or {"category": "unsupported_capability", "message": "not configured"})})
                sample_count = 0
            else:
                for repeat in range(repeats):
                    for case in selected:
                        if case.state_mode is StateMode.FRESH or repeat == 0:
                            adapter.reset()
                        try:
                            adapter.ingest(case.records, case.edges)
                            response = adapter.execute_task(case)
                            retrieved = response.retrieved_ids
                            relevant = set(case.relevant_ids)
                            forbidden = set(case.forbidden_ids)
                            hits = relevant & set(retrieved)
                            violations = forbidden & set(retrieved)
                            success = ((not retrieved) if case.family == "abstention" else
                                       (not relevant or relevant.issubset(retrieved))) and not violations
                            passed += int(success)
                            permission_violations += len(violations) if case.family in {"permission", "cross_agent"} else 0
                            false_memories += len(violations)
                            provenance_hits += int(bool(response.provenance_ids))
                            total_relevant += len(relevant)
                            total_retrieved += len(retrieved)
                            true_positive += len(hits)
                            if relevant:
                                ranks = [retrieved.index(item) + 1 for item in relevant if item in retrieved]
                                reciprocal_sum += 1 / min(ranks) if ranks else 0
                            all_latencies.append(response.latency_ms)
                            warnings.extend(response.warnings)
                            samples.append({"repeat": repeat + 1, "case_id": case.case_id, "family": case.family,
                                            "state_mode": case.state_mode.value, "passed": success, "retrieved_ids": retrieved,
                                            "relevant_ids": list(case.relevant_ids), "forbidden_ids": list(case.forbidden_ids),
                                            "latency_ms": response.latency_ms, "input_tokens": response.input_tokens,
                                            "output_tokens": response.output_tokens, "error": response.error})
                        except Exception as exc:
                            errors.append({"case_id": case.case_id, "category": "exception", "message": f"{type(exc).__name__}: {exc}"})
                            samples.append({"repeat": repeat + 1, "case_id": case.case_id, "family": case.family,
                                            "state_mode": case.state_mode.value, "passed": False, "retrieved_ids": [],
                                            "relevant_ids": list(case.relevant_ids), "forbidden_ids": list(case.forbidden_ids),
                                            "latency_ms": None, "input_tokens": None, "output_tokens": None,
                                            "error": errors[-1]})
                sample_count = len(samples)
        finally:
            storage_after = adapter.export_state_metrics()
            adapter.cleanup()
        case_count = len(selected) * repeats
        failed = case_count - passed
        lat_mean = statistics.fmean(all_latencies) if all_latencies else None
        variance = statistics.pvariance(all_latencies) if len(all_latencies) > 1 else 0.0 if all_latencies else None
        ci95 = 1.96 * math.sqrt(variance / len(all_latencies)) if variance is not None and all_latencies else None
        result = {
            "run_id": f"p18-{baseline.value.lower()}-{uuid4()}", "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": commit, "working_tree_state": tree, "system": baseline.value, "system_version": "0.1.0",
            "adapter_version": adapter.adapter_version, "adapter_status": adapter.status, "model": None,
            "model_version": None, "model_parameters": {"provider": None, "temperature": None, "top_p": None,
                "seed": None, "max_tokens": None, "system_prompt_version": None,
                "limitation": "No model invoked" if adapter.status == "READY" else "Provider unavailable"},
            "dataset_id": dataset.dataset_id, "dataset_version": dataset.dataset_version, "seed": dataset.seed,
            "dataset_metadata": {"generator_version": dataset.generator_version, "created_at": dataset.created_at,
                "case_count": dataset.case_count, "content_hash": dataset.content_hash, "tier": dataset.tier},
            "benchmark": family or "all", "benchmark_version": BENCHMARK_VERSION, "case_count": case_count,
            "passed": passed, "failed": failed, "task_success": _ratio(passed, case_count),
            "metrics": {"recall": _ratio(int(true_positive), int(total_relevant)),
                "precision": _ratio(int(true_positive), int(total_retrieved)), "mrr": _ratio(int(reciprocal_sum * 1_000_000), max(1, case_count) * 1_000_000),
                "temporal_accuracy": _family_accuracy(samples, "temporal"), "contradiction_accuracy": _family_accuracy(samples, "contradiction"),
                "provenance_accuracy": _ratio(provenance_hits, sample_count), "abstention_accuracy": _family_accuracy(samples, "abstention"),
                "permission_accuracy": _family_accuracy(samples, "permission"), "false_memory_count": false_memories,
                "permission_violation_count": permission_violations, "context_records_mean": _mean_length(samples, "retrieved_ids")},
            "tokens": {"input": _sum_nullable(samples, "input_tokens"), "output": _sum_nullable(samples, "output_tokens"),
                "total": _sum_nullable(samples, "input_tokens", "output_tokens")},
            "latency_ms": {"retrieval": lat_mean, "generation": None, "end_to_end": lat_mean,
                "p50": _percentile(all_latencies, .5), "p95": _percentile(all_latencies, .95), "p99": _percentile(all_latencies, .99),
                "sample_count": len(all_latencies), "variance": variance, "ci95_half_width": ci95},
            "cost": {"status": "UNKNOWN_COST", "amount": None, "currency": None},
            "storage_before": storage_before, "storage_after": storage_after, "errors": errors, "warnings": sorted(set(warnings)),
            "unsupported_capabilities": list(adapter.unsupported_capabilities), "samples": samples,
        }
        validate_result(result)
        return result


def _family_accuracy(samples: list[dict], family: str) -> float | None:
    chosen = [sample for sample in samples if sample["family"] == family]
    return _ratio(sum(bool(sample["passed"]) for sample in chosen), len(chosen)) if chosen else None


def _mean_length(samples: list[dict], key: str) -> float | None:
    return statistics.fmean(len(sample[key]) for sample in samples) if samples else None


def _sum_nullable(samples: list[dict], *keys: str) -> int | None:
    values = [sample[key] for sample in samples for key in keys]
    return sum(values) if values and all(value is not None for value in values) else None
