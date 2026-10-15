"""Evaluate one frozen AML-09E split; final is run once after candidate selection."""
from __future__ import annotations
import argparse, hashlib, json, math, random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from uuid import NAMESPACE_URL, uuid5
from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (AccessContext, InMemoryReferenceRepository, Observation, Principal,
                          Provenance, SecurityEnvelope, Source, TruthMetadata, TruthState)
from syune.retrieval import InvertedSeedIndex, QueryMode, RecallCue, RecallRequest, RetrievalService

NOW=datetime(2026,1,1,tzinfo=timezone.utc); KS=(1,5,10,100)
METRICS=tuple([f"recall@{k}" for k in KS]+[f"precision@{k}" for k in KS]+["mrr","ndcg","empty_result_rate","false_positive_rate","abstention_accuracy","relevant_coverage"])
def dt(value): return datetime.fromisoformat(value.replace("Z","+00:00")) if value else None
def scored(ranked,relevant):
    out={}; relevant=set(relevant)
    for k in KS:
        hits=len(set(ranked[:k])&relevant); out[f"recall@{k}"]=hits/len(relevant) if relevant else float(not ranked); out[f"precision@{k}"]=hits/k
    out["mrr"]=next((1/i for i,x in enumerate(ranked,1) if x in relevant),0.0)
    ideal=sum(1/math.log2(i+1) for i in range(1,len(relevant)+1)); dcg=sum(1/math.log2(i+1) for i,x in enumerate(ranked,1) if x in relevant)
    out["ndcg"]=dcg/ideal if ideal else float(not ranked); out["empty_result_rate"]=float(not ranked)
    out["false_positive_rate"]=len(set(ranked)-relevant)/len(ranked) if ranked else 0.0
    out["abstention_accuracy"]=float((not ranked)==(not relevant)); out["relevant_coverage"]=float(bool(set(ranked)&relevant)) if relevant else 1.0
    return out
def aggregate(rows): return {m:round(mean(float(r[m]) for r in rows),6) for m in METRICS}
def ci(rows,metric):
    groups=defaultdict(list)
    for row in rows: groups[row["cluster"]].append(row)
    keys=sorted(groups); rng=random.Random(90501); vals=[]
    for _ in range(5000):
        sample=[r for _ in keys for r in groups[rng.choice(keys)]]; vals.append(mean(float(r[metric]) for r in sample))
    vals.sort(); return {"low":round(vals[124],6),"high":round(vals[4874],6)}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dataset",type=Path,default=Path("benchmarks/data/aml09e_independent_v1.json")); ap.add_argument("--split",choices=("development","final"),required=True); ap.add_argument("--label",required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    raw=a.dataset.read_bytes(); data=json.loads(raw); repo=InMemoryReferenceRepository(); source=Source(SourceId(uuid5(NAMESPACE_URL,"aml09e")),"evaluation","v1",NOW); repo.put(source); ids={}
    for d in data["documents"]:
        oid=ObservationId(uuid5(NAMESPACE_URL,"aml09e:"+d["id"])); ids[d["id"]]=oid
        repo.put(Observation(oid,d["text"],"text",Provenance(ProvenanceId(uuid5(NAMESPACE_URL,"aml09e-prov:"+d["id"])),source.id,NOW),dt(d.get("valid_from")) or NOW,NOW,Confidence(1),TruthMetadata(TruthState.VERIFIED,recorded_at=NOW,valid_from=dt(d.get("valid_from")),valid_until=dt(d.get("valid_until"))),security=SecurityEnvelope(owner=d["owner"]) if d.get("owner") else None))
    index=InvertedSeedIndex(repo); index.rebuild(); service=RetrievalService(repo,index); reverse={v:k for k,v in ids.items()}; rows=[]
    for q in (q for q in data["queries"] if q["split"]==a.split):
        access=AccessContext(Principal(q["principal"],"aml09e"),"evaluation",legacy_local_compatible=False) if q.get("principal") else None
        cue=RecallCue(text=q["text"],query_mode=QueryMode(q.get("mode","CURRENT")),valid_at=dt(q.get("valid_at")),access_context=access)
        ranked=[reverse[x.entity_id] for x in service.recall(RecallRequest(cue,max_results=100)).candidates if x.entity_id in reverse]
        rows.append({"id":q["id"],"cluster":q["cluster"],"category":q["category"],"ranked":ranked,"forbidden":sorted(set(q.get("forbidden",()))&set(ranked)),**scored(ranked,q["relevant"])})
    report={"label":a.label,"split":a.split,"dataset_sha256":hashlib.sha256(raw).hexdigest(),"documents":len(data["documents"]),"queries":len(rows),"clusters":len({r["cluster"] for r in rows}),"bootstrap":{"unit":"source cluster","samples":5000},"overall":aggregate(rows),"by_category":{c:aggregate([r for r in rows if r["category"]==c]) for c in sorted({r["category"] for r in rows})},"recall@5_cluster_ci95":ci(rows,"recall@5"),"false_positive_rate_cluster_ci95":ci(rows,"false_positive_rate"),"forbidden_result_count":sum(len(r["forbidden"]) for r in rows),"details":rows}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n"); print(json.dumps({k:v for k,v in report.items() if k!="details"},indent=2))
if __name__=="__main__": main()
