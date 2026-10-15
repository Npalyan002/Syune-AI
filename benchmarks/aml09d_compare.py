"""Paired source-cluster bootstrap comparison for AML-09D reports."""
from __future__ import annotations
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    before_raw = json.loads(args.baseline.read_text(encoding="utf-8"))
    after_raw = json.loads(args.candidate.read_text(encoding="utf-8"))
    assert before_raw["dataset_sha256"] == after_raw["dataset_sha256"]
    before = {row["id"]: row for row in before_raw["details"]}
    after = {row["id"]: row for row in after_raw["details"]}
    assert before.keys() == after.keys()
    clusters: dict[str, list[str]] = defaultdict(list)
    for key, row in before.items():
        clusters[row["cluster"]].append(key)
    cluster_ids = sorted(clusters)
    metrics = ("recall@1", "recall@5", "recall@10", "recall@100", "precision@1",
               "precision@5", "precision@10", "precision@100", "mrr", "ndcg",
               "empty_result_rate", "false_positive_rate")
    rng = random.Random(90401)
    result = {}
    for metric in metrics:
        deltas = {cluster: mean(after[key][metric] - before[key][metric]
                                        for key in clusters[cluster]) for cluster in cluster_ids}
        samples = sorted(mean(deltas[rng.choice(cluster_ids)] for _ in cluster_ids) for _ in range(5000))
        result[metric] = {"baseline": round(mean(before[key][metric] for key in before), 6),
                          "candidate": round(mean(after[key][metric] for key in after), 6),
                          "delta": round(mean(after[key][metric] - before[key][metric] for key in before), 6),
                          "delta_cluster_ci95": {"low": round(samples[124], 6),
                                                   "high": round(samples[4874], 6)}}
    report = {"dataset_sha256": before_raw["dataset_sha256"], "queries": len(before),
              "clusters": len(clusters), "paired_bootstrap_samples": 5000,
              "bootstrap_unit": "source cluster", "metrics": result}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
