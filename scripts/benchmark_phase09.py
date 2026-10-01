"""Profile activation and cognitive-cycle benchmark."""
import json,math,statistics
from time import perf_counter
from syune.core import AssociationId,CognitiveRequestId,Confidence,ObservationId,ProvenanceId,SourceId,utc_now
from syune.cognition import CognitiveRequest,CognitiveService,ProfileName,ProfileRegistry
from syune.memory import Association,InMemoryReferenceRepository,Observation,Provenance,Source
from syune.retrieval import InvertedSeedIndex,RetrievalService

def percentile(values,q):return sorted(values)[min(len(values)-1,math.ceil(len(values)*q)-1)]
def run(size,repeats=5):
    memory=InMemoryReferenceRepository();now=utc_now();sources=[Source(SourceId.new(),"synthetic",f"s{x}",now) for x in range(4)];provs=[Provenance(ProvenanceId.new(),x.id,now) for x in sources];items=[]
    for n in range(size):
        item=Observation(ObservationId.new(),f"profile benchmark common {n}" if n<24 else f"entity {n}","text",provs[n%4],now,now,Confidence(.5));memory.put(item);items.append(item)
    for n in range(min(24,size-1)):memory.add_association(Association(AssociationId.new(),items[n].id,items[n+1].id,"supports",provs[n%4],Confidence(.5),now,.4))
    index=InvertedSeedIndex(memory);index.rebuild();service=CognitiveService(memory,RetrievalService(memory,index));registry=ProfileRegistry();result={"entities":size}
    for name in ProfileName:
        profile=registry.by_name(name);resolution=[];cycles=[]
        for _ in range(repeats):
            tick=perf_counter();registry.resolve(profile.id);resolution.append((perf_counter()-tick)*1000)
            request=CognitiveRequest(CognitiveRequestId.new(),text="profile benchmark common",activation_profile=profile.id)
            tick=perf_counter();service.process(request);cycles.append((perf_counter()-tick)*1000)
        result[name.value]={"resolution_p50_ms":statistics.median(resolution),"cycle_p50_ms":statistics.median(cycles),"cycle_p95_ms":percentile(cycles,.95)}
    return result
if __name__=="__main__":print(json.dumps([run(x) for x in (100,1000,10000)],indent=2))
