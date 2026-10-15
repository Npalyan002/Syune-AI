"""Paired query-level comparison for frozen AML-09G SciFact reports."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean

METRICS = ("recall@1", "recall@5", "recall@10", "recall@100", "precision@1", "precision@5", "precision@10", "precision@100", "mrr", "ndcg", "empty_result_rate")


def compare(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
    left_rows = {str(row["id"]): row for row in left["details"]}
    right_rows = {str(row["id"]): row for row in right["details"]}
    ids = sorted(set(left_rows) & set(right_rows))
    rng = random.Random(90908)
    output: dict[str, object] = {}
    for metric in METRICS:
        deltas = [float(right_rows[key][metric]) - float(left_rows[key][metric]) for key in ids]
        samples = sorted(mean(rng.choice(deltas) for _ in deltas) for _ in range(5000))
        output[metric] = {
            "delta": round(mean(deltas), 6),
            "paired_bootstrap_ci95": {"low": round(samples[124], 6), "high": round(samples[4874], 6)},
        }
    return {"left": left["label"], "right": right["label"], "paired_queries": len(ids), "metrics": output}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--aml09e", type=Path, required=True)
    parser.add_argument("--aml09f", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in (args.baseline, args.aml09e, args.aml09f)]
    result = {
        "bootstrap": {"unit": "paired query", "samples": 5000, "seed": 90908},
        "baseline_to_aml09e": compare(reports[0], reports[1]),
        "baseline_to_aml09f": compare(reports[0], reports[2]),
        "aml09e_to_aml09f": compare(reports[1], reports[2]),
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
