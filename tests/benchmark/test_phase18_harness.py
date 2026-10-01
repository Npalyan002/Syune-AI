from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.adapters import BasicRagAdapter, NotConfiguredAdapter
from benchmarks.datasets import build_dataset
from benchmarks.model import Baseline
from benchmarks.reporting import compare, evaluate_policy, markdown_report
from benchmarks.runner import BenchmarkRunner, validate_result, write_raw_result


ROOT = Path(__file__).resolve().parents[2]


def test_dataset_determinism_and_seed_reproducibility():
    first, second = build_dataset(seed=7), build_dataset(seed=7)
    assert first.content_hash == second.content_hash
    assert [case.case_id for case in first.cases] == [case.case_id for case in second.cases]
    assert [case.case_id for case in first.cases] != [case.case_id for case in build_dataset(seed=8).cases]


def test_adapters_isolate_and_reset_state():
    one, two = BasicRagAdapter(), BasicRagAdapter()
    case = build_dataset().cases[0]
    one.ingest(case.records, case.edges)
    assert one.export_state_metrics()["records"] > 0
    assert two.export_state_metrics()["records"] == 0
    one.reset()
    assert one.export_state_metrics()["records"] == 0


def test_result_schema_metrics_failure_accounting_and_unsupported():
    runner = BenchmarkRunner(ROOT)
    result = runner.run(Baseline.BASIC_RAG, build_dataset())
    validate_result(result)
    assert result["passed"] + result["failed"] == result["case_count"]
    assert 0 <= result["metrics"]["recall"] <= 1
    unavailable = runner.run(Baseline.MODEL_ONLY, build_dataset())
    assert unavailable["adapter_status"] == "NOT_CONFIGURED"
    assert len(unavailable["errors"]) == unavailable["case_count"]


def test_current_syune_runs_actual_retrieval():
    result = BenchmarkRunner(ROOT).run(Baseline.CURRENT_SYUNE, build_dataset(), family="associative")
    assert result["system"] == "B3_CURRENT_SYUNE"
    assert result["passed"] == 1


def test_historical_results_are_exclusive_create():
    result = BenchmarkRunner(ROOT).run(Baseline.BASIC_RAG, build_dataset(), family="recall")
    test_dir = ROOT / "docs/evals/phase18/test-tmp"
    path = write_raw_result(result, test_dir)
    try:
        assert path.exists()
        with pytest.raises(FileExistsError): write_raw_result(result, test_dir)
    finally:
        path.unlink(missing_ok=True)
        test_dir.rmdir()


def test_comparison_policy_and_report_generation():
    runner, data = BenchmarkRunner(ROOT), build_dataset()
    baseline = runner.run(Baseline.BASIC_RAG, data)
    candidate = runner.run(Baseline.CURRENT_SYUNE, data)
    delta = compare(baseline, candidate)
    assert delta["task_success_delta"]["delta"] == candidate["task_success"] - baseline["task_success"]
    policy = json.loads((ROOT / "benchmarks/config/regression_policy.v1.json").read_text())
    gate = evaluate_policy(delta, policy)
    # Phase 20 closes the permission regression measured by the Phase 18 harness.
    assert gate["checks"]["permission"] is True
    assert baseline["run_id"] in markdown_report(baseline)


def test_scale_and_longitudinal_points_are_declared():
    assert build_dataset(scale=10_000).dataset_id.endswith("s10000")
    assert build_dataset(interactions=100).dataset_id.endswith("i100")
    with pytest.raises(ValueError): build_dataset(scale=999)
