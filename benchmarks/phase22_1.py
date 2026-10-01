"""Phase 22.1 bounded-postings scale and before/after profiling."""
from __future__ import annotations
import cProfile, hashlib, io, json, math, os, platform, pstats, random, statistics
from itertools import islice
from time import perf_counter
from benchmarks.phase22 import DEFAULT_SEED, ScalePostingIndex, generate_scale_records
from syune.retrieval.hybrid import tokens

VERSION="phase22.1-scale-v2"; CANDIDATE_BUDGET=256

class BoundedPostingIndex:
    def __init__(self): self.postings={}; self.records={}; self.exact={}
    def upsert(self,r):
        self.records[r.memory_id]=r; self.exact[r.memory_id]=r.memory_id
        for term in set(tokens(r.text)): self.postings.setdefault(term,[]).append(r.memory_id)
    def search(self,query,limit=1):
        terms=tuple(dict.fromkeys(tokens(query)))
        if len(terms)==1 and terms[0] in self.exact: return (self.exact[terms[0]],),1
        planned=sorted(terms,key=lambda t:(len(self.postings.get(t,())),t)); candidates={}
        for term in planned:
            remaining=CANDIDATE_BUDGET-len(candidates)
            if remaining<=0: break
            for mid in islice(self.postings.get(term,()),remaining): candidates[mid]=candidates.get(mid,0)+1
        eligible=((score,mid) for mid,score in candidates.items() if self.records[mid].state not in {"SUPERSEDED","INVALIDATED"})
        import heapq
        return tuple(mid for _,mid in heapq.nlargest(limit,eligible,key=lambda x:(x[0],x[1]))),len(candidates)
    @property
    def bytes_used(self): return sum(len(k)+sum(len(x) for x in v) for k,v in self.postings.items())

def _pct(v,f): return sorted(v)[min(len(v)-1,max(0,math.ceil(len(v)*f)-1))]
def _profile(index,queries):
    profiler=cProfile.Profile(); profiler.enable()
    for q in queries:index.search(q,1)
    profiler.disable(); out=io.StringIO(); pstats.Stats(profiler,stream=out).sort_stats("cumulative").print_stats(12)
    return out.getvalue()

def run_scale(count,seed=DEFAULT_SEED):
    index=BoundedPostingIndex(); began=perf_counter()
    for record in generate_scale_records(count,seed):index.upsert(record)
    build=(perf_counter()-began)*1000; rng=random.Random(seed+1); targets=rng.sample(range(count),min(200,count))
    classes={"EXACT":[],"LEXICAL_SELECTIVE":[],"LEXICAL_BROAD":[],"ENTITY":[],"ASSOCIATIVE":[],"TEMPORAL":[],"MIXED":[]}
    candidate_counts=[]; all_candidate_counts=[]; tp=0
    for target in targets:
        queries={"EXACT":f"m{target}","LEXICAL_SELECTIVE":f"project token{target}","LEXICAL_BROAD":"deployment checkpoint",
                 "ENTITY":f"entity {target % max(100,count//20)}","ASSOCIATIVE":f"deployment token{target}",
                 "TEMPORAL":f"current checkpoint token{target}","MIXED":f"entity deployment token{target}"}
        for kind,q in queries.items():
            started=perf_counter(); hits,candidates=index.search(q,1); classes[kind].append((perf_counter()-started)*1000)
            all_candidate_counts.append(candidates)
            if kind=="LEXICAL_SELECTIVE": tp+=int(f"m{target}" in hits); candidate_counts.append(candidates)
    lat=[x for values in classes.values() for x in values]
    return {"status":"EXECUTED","records":count,"build_time_ms":build,"recall":tp/len(targets),"precision_at_1":tp/len(targets),
        "p50_ms":_pct(lat,.5),"p95_ms":_pct(lat,.95),"p99_ms":_pct(lat,.99),"candidate_count_max":max(all_candidate_counts),
        "candidate_count_mean":statistics.fmean(candidate_counts),"candidate_budget":CANDIDATE_BUDGET,"index_size_bytes":index.bytes_used,
        "query_classes":{k:{"p50_ms":_pct(v,.5),"p95_ms":_pct(v,.95),"p99_ms":_pct(v,.99)} for k,v in classes.items()}}

def run():
    results={str(n):run_scale(n) for n in (10_000,100_000)}
    pre=ScalePostingIndex()
    for r in generate_scale_records(100_000):pre.upsert(r)
    post=BoundedPostingIndex()
    for r in generate_scale_records(100_000):post.upsert(r)
    queries=["deployment checkpoint"]*20
    payload={"benchmark_version":VERSION,"generator_version":"phase22-scale-v1","metric_change":"precision@1 replaces precision@5 when one relevant item exists",
      "environment":{"python":platform.python_version(),"platform":platform.platform(),"logical_cpu_count":os.cpu_count()},"results":results,
      "profiles":{"pre_100k":_profile(pre,queries),"post_100k":_profile(post,queries)}}
    payload["content_hash"]=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(); return payload
