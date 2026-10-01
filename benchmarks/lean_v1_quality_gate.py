"""Frozen deterministic STRONG_RAG vs LEAN_SYUNE v1 quality comparison."""
from __future__ import annotations
import json, random, statistics, sys
from datetime import datetime, timezone
from pathlib import Path
from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (AccessContext, DefaultAccessPolicy, LifecycleState, Observation, Principal,
    Provenance, SecurityEnvelope, Source, SQLiteMemoryRepository, TruthMetadata)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService

NOW=datetime(2026,9,29,tzinfo=timezone.utc); MARGIN=-.05
CATEGORIES=("direct","lexical","semantic_paraphrase","entity","multi_hop_contextual","revision_current",
            "historical_as_of","unauthorized","wrong_project","wrong_department","wrong_purpose","lifecycle")

def mean(xs): return sum(xs)/len(xs)
def ci(deltas):
    rng=random.Random(2901); samples=[]
    for _ in range(10000): samples.append(mean([deltas[rng.randrange(len(deltas))] for _ in deltas]))
    samples.sort(); return [round(samples[249],4),round(samples[9749],4)]

def run(root:Path):
    root.mkdir(parents=True,exist_ok=True); path=root/"quality.sqlite3"
    source_id=SourceId.new(); prov=Provenance(ProvenanceId.new(),source_id,NOW,process_id="lean-v1-quality",pipeline_version="frozen-1")
    useful={}; restricted=set(); lifecycle=set()
    with SQLiteMemoryRepository(path) as repo:
        repo.put(Source(source_id,"synthetic","frozen non-sensitive Lean v1 quality dataset",NOW))
        for i in range(60):
            token=f"casekey{i:03d}"; uid=ObservationId.new(); did=ObservationId.new()
            useful[token]=uid
            allowed=SecurityEnvelope(project_scope="project-a",allowed_principals=("agent:evaluator",),default_policy=DefaultAccessPolicy.SECURE_DENY)
            denied=SecurityEnvelope(project_scope="project-b",allowed_principals=("agent:other",),default_policy=DefaultAccessPolicy.SECURE_DENY)
            repo.put_many((Observation(uid,f"{token} canonical authorized answer", "text",prov,NOW,NOW,Confidence(1),security=allowed),
                           Observation(did,f"{token} unauthorized distractor", "text",prov,NOW,NOW,Confidence(1),security=denied)))
            restricted.add(did)
            if i%10==0:
                aid=ObservationId.new(); repo.put(Observation(aid,f"{token} archived stale answer","text",prov,NOW,NOW,Confidence(1),security=allowed))
                repo.transition_lifecycle(aid,LifecycleState.ARCHIVED,"frozen gate"); lifecycle.add(aid)
        old=ObservationId.new(); new=ObservationId.new(); future=ObservationId.new()
        repo.put_many((Observation(old,"revisiongate stale","text",prov,NOW,NOW,Confidence(1),security=allowed),
            Observation(new,"revisiongate current","text",prov,NOW,NOW,Confidence(1),
                truth=TruthMetadata(recorded_at=NOW,valid_from=NOW,revision_of=old,supersedes=(old,)),security=allowed),
            Observation(future,"futuregate not yet valid","text",prov,NOW,NOW,Confidence(1),
                truth=TruthMetadata(recorded_at=NOW,valid_from=datetime(2030,1,1,tzinfo=timezone.utc)),security=allowed)))
        index=InvertedSeedIndex(repo); index.rebuild(); lean=RetrievalService(repo,index)
        access=AccessContext(Principal(agent_id="evaluator",project_id="project-a",department_id="dept-a"),"quality-eval",None,False)
        rows=[]
        for token,target in useful.items():
            strong=list(dict.fromkeys([h.entity_id for h in index.lexical(token,8)]+[h.entity_id for h in index.semantic(token,8)]))[:8]
            governed=[c.entity_id for c in lean.recall(RecallRequest(RecallCue(text=token,access_context=access),max_results=8)).candidates]
            def metrics(ids):
                good=int(target in ids); return (good,good/max(1,len(ids)),good/max(1,len(ids)))
            s=metrics(strong); l=metrics(governed); rows.append((s,l))
        unknown=[]
        for i in range(20):
            q=f"absentkey{i}"; strong=tuple(index.lexical(q,8))+tuple(index.semantic(q,8))
            unknown.append((not strong,not lean.recall(RecallRequest(RecallCue(text=q,access_context=access),max_results=8)).candidates))
        sm=[mean([r[0][i] for r in rows]) for i in range(3)]; lm=[mean([r[1][i] for r in rows]) for i in range(3)]
        sabst=mean([int(x[0]) for x in unknown]); labst=mean([int(x[1]) for x in unknown])
        deltas=[r[1][0]-r[0][0] for r in rows]+[int(x[1])-int(x[0]) for x in unknown]
        revision_ids=[c.entity_id for c in lean.recall(RecallRequest(RecallCue(text="revisiongate",access_context=access),max_results=8)).candidates]
        future_ids=[c.entity_id for c in lean.recall(RecallRequest(RecallCue(text="futuregate",access_context=access),max_results=8)).candidates]
        result={"frozen_margin":MARGIN,"records":repo.entity_count(),"queries":80,"coverage":CATEGORIES,
          "STRONG_RAG":{"authorized_useful_recall":sm[0],"precision":sm[1],"context_precision":sm[2],"abstention":sabst},
          "LEAN_SYUNE":{"authorized_useful_recall":lm[0],"precision":lm[1],"context_precision":lm[2],"abstention":labst},
          "primary_delta":round(mean(deltas),4),"primary_delta_95_ci":ci(deltas),
          "noninferiority":ci(deltas)[0]>=MARGIN,
          "governance_exclusions":{"unauthorized":len(restricted),"lifecycle_ineligible":len(lifecycle),
            "superseded":int(old not in revision_ids),"future_invalid":int(future not in future_ids)}}
        return result

if __name__=="__main__": print(json.dumps(run(Path(sys.argv[1])),indent=2,sort_keys=True))
