"""Phase 31 final product-value protocol and frozen decision rules."""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmarks.phase28r import (DECISION_SCHEMA, DECISION_SYSTEM, MODEL, POLICIES,
                                 SYNTHESIS_SCHEMA, SYNTHESIS_SYSTEM, build_dataset,
                                 build_prompt, family_specs, roster)

VERSION = "P31-FINAL-PRODUCT-V1"
SEED = 310001
TREATMENTS = ("STRONG_RAG", "RAG_SYNTHESIS", "PRODUCTION_SYUNE")
EPOCHS = ("Cold Start", "Initial Experience", "Repetition", "Cross-Agent Reuse",
          "Environment Shift", "Contradiction", "Policy Change", "Agent Replacement",
          "Revocation / Human Correction", "Long-Term Reuse")
SAMPLE = {"tasks_per_treatment": 200, "paired_tasks": 200, "families": 20,
          "departments": 5, "epochs": 10, "active_agents": 25, "replacement_agents": 5}
BUDGET = {"decision_calls": 600, "synthesis_calls": 200, "max_provider_calls": 850,
          "estimated_input_tokens": 1_600_000, "estimated_output_tokens": 128_000,
          "max_input_tokens": 2_500_000, "max_output_tokens": 200_000,
          "estimated_cost_usd": 1.776, "hard_cost_cap_usd": 5.0}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def dataset() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """One frozen task per family/epoch; ground truth remains a separate return value."""
    provider, truth, _ = build_dataset()
    wanted = {f"P28R-E{epoch}-{family:02d}-0" for epoch in range(10) for family in range(20)}
    p = sorted((x for x in provider if x["task_id"] in wanted), key=lambda x: (x["epoch"], x["family_index"]))
    truth_by_id = {x["task_id"]: x for x in truth}
    g = [truth_by_id[x["task_id"]] for x in p]
    if len(p) != 200 or len(g) != 200:
        raise RuntimeError("phase31 dataset cardinality drift")
    return p, g


DECISION_RULES = {
    "security_hard_gate": "all security and leakage counts equal zero",
    "truth_hard_gate": "temporal and contradiction accuracy equal 1 and false-memory selection equals zero",
    "quality_noninferior": "SYUNE minus RAG_SYNTHESIS lower 95% cluster-bootstrap bound >= -0.03",
    "learning_win": "SYUNE repeated-error rate <= 0.75 * RAG_SYNTHESIS",
    "continuity_win": "SYUNE replacement-agent first-10 success >= RAG_SYNTHESIS - 0.02",
    "economic_win": "SYUNE cost/success <= RAG_SYNTHESIS cost/success",
    "latency_acceptable": "SYUNE p95 total latency <= 1.25 * RAG_SYNTHESIS p95",
    "adaptation_acceptable": "SYUNE stale uses <= RAG_SYNTHESIS stale uses + 1",
    "full": "hard gates, noninferiority, >=4 of learning/continuity/economics/latency/adaptation wins, and complexity ratio <=2",
    "lean": "hard gates, noninferiority, >=2 of learning/continuity/economics/governance wins, but full rule fails",
    "pivot": "hard gates and abs quality delta <=.03, with <2 learning/continuity/economics wins and governed-core audit completeness=1",
    "otherwise": "DO_NOT_PRODUCTIZE_CURRENT_ARCHITECTURE",
}


def freeze(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    tasks, truth = dataset()
    files = {
        "provider_tasks.jsonl": "".join(canonical(x) + "\n" for x in tasks),
        "ground_truth.jsonl": "".join(canonical(x) + "\n" for x in truth),
        "agent_roster.json": json.dumps(roster(), indent=2) + "\n",
        "family_specs.json": json.dumps(family_specs(), indent=2) + "\n",
        "preregistration.json": json.dumps({"version": VERSION, "seed": SEED,
            "treatments": TREATMENTS, "epochs": EPOCHS, "sample": SAMPLE, "budget": BUDGET,
            "provider": "openai", "model": MODEL, "temperature": .2,
            "cluster_units": ["department", "task_family", "agent", "epoch"],
            "decision_rules": DECISION_RULES}, indent=2) + "\n",
    }
    for name, body in files.items():
        (out / name).write_text(body, encoding="utf-8")
    manifest = {"version": VERSION, "files": {name: hashlib.sha256(body.encode()).hexdigest() for name, body in files.items()}}
    manifest["freeze_hash"] = digest(manifest["files"])
    (out / "freeze_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def percentile(values: list[float], q: float) -> float:
    if not values: return 0.0
    xs = sorted(values); pos = (len(xs) - 1) * q; lo = math.floor(pos); hi = math.ceil(pos)
    return xs[lo] if lo == hi else xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def _competence(rows: list[dict[str, Any]]) -> int | None:
    for i in range(1, len(rows) + 1):
        if i >= 5 and sum(x["success"] for x in rows[max(0, i-10):i]) / min(10, i) >= .8: return i
    return None


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by = defaultdict(list)
    for row in rows: by[row["treatment"]].append(row)
    result = {}
    for treatment, values in by.items():
        values.sort(key=lambda x: (x["epoch"], x["task_id"])); successes = sum(x["success"] for x in values)
        cold = [x for x in values if x["cold_agent"]]
        costs = sum(x["cost_usd"] for x in values); lat = [x["total_latency_ms"] for x in values]
        result[treatment] = {
            "tasks": len(values), "overall_success": successes / len(values),
            "final_epoch_success": sum(x["success"] for x in values if x["epoch"] == 9) / 20,
            "per_department_success": {d: sum(x["success"] for x in values if x["department"] == d) / 40 for d in sorted({x["department"] for x in values})},
            "per_family_success": {f: sum(x["success"] for x in values if x["task_family"] == f) / 10 for f in sorted({x["task_family"] for x in values})},
            "repeated_error_rate": sum(x["repeated_error"] for x in values) / len(values),
            "errors_prevented": sum(x["prior_family_error"] and x["success"] for x in values),
            "cold_first": float(cold[0]["success"]) if cold else None,
            "cold_first5": sum(x["success"] for x in cold[:5]) / max(1, len(cold[:5])),
            "cold_first10": sum(x["success"] for x in cold[:10]) / max(1, len(cold[:10])),
            "time_to_competence": _competence(values),
            "cost_task": costs / len(values), "cost_success": costs / max(1, successes), "cumulative_cost": costs,
            "stale_uses": sum(x["stale_use"] for x in values), "negative_transfer": sum(x["negative_transfer"] for x in values),
            "latency_ms": {"p50": percentile(lat, .5), "p95": percentile(lat, .95), "p99": percentile(lat, .99)},
            "retrieval_ms": {q: percentile([x["retrieval_ms"] for x in values], v) for q, v in (("p50",.5),("p95",.95),("p99",.99))},
            "model_ms": {q: percentile([x["model_ms"] for x in values], v) for q, v in (("p50",.5),("p95",.95),("p99",.99))},
            "gateway_ms": {q: percentile([x["gateway_ms"] for x in values], v) for q, v in (("p50",.5),("p95",.95),("p99",.99))},
            "cognitive_ms": {q: percentile([x["cognitive_ms"] for x in values], v) for q, v in (("p50",.5),("p95",.95),("p99",.99))},
            "storage_ms": {q: percentile([x["storage_ms"] for x in values], v) for q, v in (("p50",.5),("p95",.95),("p99",.99))},
            "input_tokens": sum(x["input_tokens"] for x in values), "output_tokens": sum(x["output_tokens"] for x in values),
        }
    return result


def cluster_bootstrap(rows: list[dict[str, Any]], reps: int = 5000) -> dict[str, float]:
    pair = defaultdict(dict)
    for row in rows:
        if row["treatment"] in ("RAG_SYNTHESIS", "PRODUCTION_SYUNE"): pair[row["task_id"]][row["treatment"]] = row
    pairs = [x for x in pair.values() if len(x) == 2]; groups = defaultdict(list)
    for x in pairs:
        base = x["RAG_SYNTHESIS"]; groups[(base["department"], base["task_family"], base["agent_id"])].append(x)
    rng = random.Random(SEED); departments = sorted({k[0] for k in groups}); draws = []
    for _ in range(reps):
        sample = []
        for department in (rng.choice(departments) for _ in departments):
            clusters = [k for k in groups if k[0] == department]
            for key in (rng.choice(clusters) for _ in clusters): sample.extend(groups[key])
        draws.append(statistics.mean(float(x["PRODUCTION_SYUNE"]["success"]) - float(x["RAG_SYNTHESIS"]["success"]) for x in sample))
    estimate = statistics.mean(float(x["PRODUCTION_SYUNE"]["success"]) - float(x["RAG_SYNTHESIS"]["success"]) for x in pairs)
    return {"estimate": estimate, "ci_low": percentile(draws, .025), "ci_high": percentile(draws, .975), "reps": reps}


def classify(summary: dict[str, Any], ci: dict[str, float], governance: dict[str, Any], complexity: dict[str, Any]) -> str:
    if not governance["security_hard_gate"] or not governance["truth_hard_gate"]: return "DO_NOT_PRODUCTIZE_CURRENT_ARCHITECTURE"
    b, c = summary["RAG_SYNTHESIS"], summary["PRODUCTION_SYUNE"]
    noninferior = ci["ci_low"] >= -.03
    wins = {"learning": c["repeated_error_rate"] <= .75 * max(b["repeated_error_rate"], 1/200),
            "continuity": c["cold_first10"] >= b["cold_first10"] - .02,
            "economics": c["cost_success"] <= b["cost_success"],
            "latency": c["latency_ms"]["p95"] <= 1.25 * b["latency_ms"]["p95"],
            "adaptation": c["stale_uses"] <= b["stale_uses"] + 1}
    count = sum(wins.values())
    if noninferior and count >= 4 and complexity["component_ratio_vs_rag_synthesis"] <= 2: return "BUILD_SYUNE_FULL_PRODUCT"
    if noninferior and sum(wins[k] for k in ("learning","continuity","economics")) >= 2: return "BUILD_SYUNE_LEAN_PRODUCT"
    if abs(ci["estimate"]) <= .03 and governance["audit_completeness"] == 1: return "PIVOT_TO_GOVERNED_MEMORY_PLATFORM"
    return "DO_NOT_PRODUCTIZE_CURRENT_ARCHITECTURE"
