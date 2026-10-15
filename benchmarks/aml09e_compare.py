"""Paired source-cluster comparison for frozen AML-09E reports."""
from __future__ import annotations
import argparse, json, random
from collections import defaultdict
from pathlib import Path
from statistics import mean

METRICS=("recall@1","recall@5","recall@10","recall@100","precision@1","precision@5","precision@10","precision@100","mrr","ndcg","empty_result_rate","false_positive_rate","abstention_accuracy","relevant_coverage")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--baseline",type=Path,required=True); ap.add_argument("--candidate",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    b=json.loads(a.baseline.read_text()); c=json.loads(a.candidate.read_text()); assert b["dataset_sha256"]==c["dataset_sha256"] and b["split"]==c["split"]
    before={r["id"]:r for r in b["details"]}; after={r["id"]:r for r in c["details"]}; assert before.keys()==after.keys()
    groups=defaultdict(list)
    for key,row in before.items(): groups[row["cluster"]].append(key)
    clusters=sorted(groups); rng=random.Random(90501); metrics={}
    for metric in METRICS:
        delta={g:mean(after[k][metric]-before[k][metric] for k in groups[g]) for g in clusters}
        samples=sorted(mean(delta[rng.choice(clusters)] for _ in clusters) for _ in range(5000))
        metrics[metric]={"baseline":round(mean(before[k][metric] for k in before),6),"candidate":round(mean(after[k][metric] for k in after),6),"delta":round(mean(after[k][metric]-before[k][metric] for k in before),6),"delta_cluster_ci95":{"low":round(samples[124],6),"high":round(samples[4874],6)}}
    out={"dataset_sha256":b["dataset_sha256"],"split":b["split"],"queries":len(before),"clusters":len(clusters),"bootstrap_unit":"source cluster","paired_bootstrap_samples":5000,"metrics":metrics}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps(out,indent=2,sort_keys=True))
if __name__=="__main__": main()
