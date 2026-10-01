"""Synthetic Cognitive Core benchmark for five bounded scenarios."""
import json,math,statistics
from time import perf_counter
from syune.core import AssociationId,CognitiveRequestId,Confidence,ObservationId,ProvenanceId,SourceId,utc_now
from syune.cognition import CognitiveBudget,CognitiveRequest,CognitiveService
from syune.memory import Association,InMemoryReferenceRepository,Observation,Provenance,Source
from syune.retrieval import InvertedSeedIndex,RetrievalService

def p(values,q):
    values=sorted(values);return values[min(len(values)-1,max(0,math.ceil(len(values)*q)-1))]
def run(size,repeats=5):
    memory=InMemoryReferenceRepository();at=utc_now();source=Source(SourceId.new(),"synthetic","benchmark",at);prov=Provenance(ProvenanceId.new(),source.id,at);memory.put(source);items=[]
    for n in range(size):
        item=Observation(ObservationId.new(),f"benchmark node {n} common cue" if n<20 else f"node {n}","text",prov,at,at,Confidence(.5));memory.put(item);items.append(item)
    for n in range(min(20,size-1)):
        relation="contradicted_by" if n==0 else "supports";memory.add_association(Association(AssociationId.new(),items[n].id,items[n+1].id,relation,prov,Confidence(.5),at,.4))
    index=InvertedSeedIndex(memory);index.rebuild();service=CognitiveService(memory,RetrievalService(memory,index));budget=CognitiveBudget(max_recall_candidates=8,max_active_entities=6,max_inference_paths=24,max_inference_records=16)
    scenarios={"simple":lambda:CognitiveRequest(CognitiveRequestId.new(),text="benchmark node 5",budget=budget),
      "associative":lambda:CognitiveRequest(CognitiveRequestId.new(),entity_ids=(items[5].id,),budget=budget),
      "conflict":lambda:CognitiveRequest(CognitiveRequestId.new(),entity_ids=(items[0].id,items[1].id),budget=budget),
      "multi_hop":lambda:CognitiveRequest(CognitiveRequestId.new(),entity_ids=(items[2].id,items[5].id),budget=budget),
      "incomplete":lambda:CognitiveRequest(CognitiveRequestId.new(),text="not present anywhere",budget=budget)}
    result={"entities":size}
    for name,factory in scenarios.items():
        times=[]
        for _ in range(repeats):
            tick=perf_counter();service.process(factory());times.append((perf_counter()-tick)*1000)
        result[name]={"p50_ms":statistics.median(times),"p95_ms":p(times,.95)}
    return result
if __name__=="__main__":print(json.dumps([run(n) for n in (100,1000,10000)],indent=2))
