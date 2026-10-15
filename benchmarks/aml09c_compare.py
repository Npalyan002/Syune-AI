"""Paired comparison for frozen AML-09C retrieval reports."""
from __future__ import annotations
import argparse, json, random
from pathlib import Path
from statistics import mean


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--improved", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline, improved = json.loads(args.baseline.read_text()), json.loads(args.improved.read_text())
    assert baseline["dataset_sha256"] == improved["dataset_sha256"]
    before = {row["id"]: row for row in baseline["details"] if row["split"] == "heldout"}
    after = {row["id"]: row for row in improved["details"] if row["split"] == "heldout"}
    assert before.keys() == after.keys()
    metrics = ("recall@1", "recall@5", "recall@10", "recall@100", "precision@1",
               "precision@5", "precision@10", "precision@100", "mrr", "ndcg",
               "empty", "false_positive_rate")
    rng = random.Random(90210); ids = sorted(before)
    result = {}
    for metric in metrics:
        deltas = [after[key][metric] - before[key][metric] for key in ids]
        samples = sorted(mean(rng.choice(deltas) for _ in deltas) for _ in range(5000))
        result[metric] = {"baseline": round(mean(before[key][metric] for key in ids), 6),
                          "improved": round(mean(after[key][metric] for key in ids), 6),
                          "delta": round(mean(deltas), 6),
                          "delta_ci95": {"low": round(samples[124], 6),
                                         "high": round(samples[4874], 6)}}
    report = {"dataset_sha256": baseline["dataset_sha256"], "heldout_queries": len(ids),
              "paired_bootstrap_samples": 5000, "metrics": result}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__": main()
