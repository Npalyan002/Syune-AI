"""Sequential Council benchmark at 2, 3, and 6 members."""
import json,math,statistics
from time import perf_counter
from syune.core import AssociationId,Confidence,CognitiveRequestId,CouncilRequestId,ObservationId,ProvenanceId,SourceId,utc_now
from syune.cognition import CognitiveRequest,CognitiveService,ProfileName,ProfileRegistry
from syune.council import CouncilMemberSpec,CouncilRequest,CouncilService
from syune.memory import Association,InMemoryReferenceRepository,Observation,Provenance,Source
from syune.retrieval import InvertedSeedIndex,RetrievalService
def p(values,q):return sorted(values)[min(len(values)-1,math.ceil(len(values)*q)-1)]
def run(size,repeats=5):
    memory=InMemoryReferenceRepository();now=utc_now();sources=[Source(SourceId.new(),"synthetic",f"s{n}",now) for n in range(4)];provs=[Provenance(ProvenanceId.new(),s.id,now) for s in sources];items=[]
    for n in range(size):item=Observation(ObservationId.new(),f"council benchmark common {n}" if n<24 else f"entity {n}","text",provs[n%4],now,now,Confidence(.5));memory.put(item);items.append(item)
    for n in range(min(24,size-1)):memory.add_association(Association(AssociationId.new(),items[n].id,items[n+1].id,"supports",provs[n%4],Confidence(.5),now,.4))
    index=InvertedSeedIndex(memory);index.rebuild();service=CouncilService(CognitiveService(memory,RetrievalService(memory,index)));registry=ProfileRegistry();names=list(ProfileName);result={"entities":size}
    for count in (2,3,6):
        members=tuple(CouncilMemberSpec(registry.by_name(x).id) for x in names[:count]);totals=[];member=[];analysis=[];synthesis=[];entries=agreements=disagreements=0
        for _ in range(repeats):
            request=CouncilRequest(CouncilRequestId.new(),CognitiveRequest(CognitiveRequestId.new(),text="council benchmark common"),members);tick=perf_counter();output=service.run(request);totals.append((perf_counter()-tick)*1000);member.append(output.diagnostics.member_execution_ms);analysis.append(output.diagnostics.analysis_ms);synthesis.append(output.diagnostics.synthesis_ms);entries=len(output.evidence_map.entries);agreements=len(output.agreements);disagreements=len(output.disagreements)
        result[str(count)]={"total_p50_ms":statistics.median(totals),"total_p95_ms":p(totals,.95),"member_p50_ms":statistics.median(member),"analysis_p50_ms":statistics.median(analysis),"synthesis_p50_ms":statistics.median(synthesis),"evidence_entries":entries,"agreements":agreements,"disagreements":disagreements}
    return result
if __name__=="__main__":print(json.dumps([run(x) for x in (100,1000,10000)],indent=2))
