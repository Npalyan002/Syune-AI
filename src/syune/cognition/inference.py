"""Bounded structural inference over existing canonical memory."""
from collections import defaultdict, deque
from uuid import NAMESPACE_URL, uuid5
from syune.core import InferenceId
from syune.memory import Episode, MemoryRepository
from syune.memory.model import NodeId
from .model import InferenceRecord, InferenceType

def _key(x): return type(x).__name__,str(x)

class InferenceEngine:
    def __init__(self,memory:MemoryRepository): self.memory=memory
    def infer(self,request_id,entity_ids:tuple[NodeId,...],max_depth=3,max_paths=64,max_records=32):
        active=set(entity_ids); records=[]; paths=[]
        def add(kind,ids,edges,explanation,support=1.0):
            if len(records)>=max_records:return
            sources=sorted({e.provenance.source_id for i in ids if (e:=self.memory.get(i)) is not None and getattr(e,"provenance",None)},key=str)
            raw=f"{request_id}:{kind.value}:{'|'.join(str(x) for x in ids)}:{'|'.join(edges)}"
            records.append(InferenceRecord(InferenceId(uuid5(NAMESPACE_URL,raw)),kind,tuple(ids),tuple(edges),tuple(sources),
                f"structural:{kind.value.lower()}:v1",max(0,min(1,support)),explanation))
        seen_edges=set()
        for left in sorted(active,key=_key):
            for edge in self.memory.associations_for(left):
                right=edge.target_id if edge.source_id==left else edge.source_id
                if right in active and str(edge.id) not in seen_edges:
                    seen_edges.add(str(edge.id)); add(InferenceType.DIRECT_RELATION,(left,right),(str(edge.id),),f"canonical relation {edge.relation_type}")
                    if "contrad" in edge.relation_type.casefold() or "conflict" in edge.relation_type.casefold():
                        add(InferenceType.CONFLICT_SIGNAL,(left,right),(str(edge.id),),"canonical relation signals unresolved conflict",0.8)
        for root in sorted(active,key=_key):
            queue=deque([(root,(root,),())])
            while queue and len(paths)<max_paths:
                current,nodes,edges=queue.popleft()
                if len(edges)>=max_depth:continue
                for edge in sorted(self.memory.associations_for(current),key=lambda x:str(x.id)):
                    other=edge.target_id if edge.source_id==current else edge.source_id
                    if other in nodes:continue
                    nn=(*nodes,other); ne=(*edges,str(edge.id)); paths.append((root,other,nn,ne))
                    if len(ne)>=2: add(InferenceType.MULTI_HOP_SUPPORT,nn,ne,f"bounded canonical path of {len(ne)} edges",1/len(ne))
                    queue.append((other,nn,ne))
                    if len(paths)>=max_paths:break
        convergent=defaultdict(list)
        for root,target,nodes,edges in paths:
            if root!=target: convergent[target].append((root,nodes,edges))
        for target,items in sorted(convergent.items(),key=lambda x:_key(x[0])):
            roots={x[0] for x in items}
            if len(roots)>=2:
                selected=sorted(items,key=lambda x:(_key(x[0]),x[2]))[:2]
                add(InferenceType.CONVERGENT_SUPPORT,tuple(x[0] for x in selected)+(target,),tuple(e for x in selected for e in x[2]),
                    f"{len(roots)} independent active roots converge structurally",min(1,len(roots)/3))
        sources=defaultdict(list)
        for entity_id in sorted(active,key=_key):
            entity=self.memory.get(entity_id); provenance=getattr(entity,"provenance",None)
            if provenance:sources[provenance.source_id].append(entity_id)
        if len(active)>=2:
            explanation="active entities share source provenance" if any(len(v)>1 for v in sources.values()) else "active entities span independent sources"
            add(InferenceType.SOURCE_OVERLAP,tuple(sorted(active,key=_key)),(),explanation,min(1,len(sources)/2))
        episodes=sorted((self.memory.get(i) for i in active if isinstance(self.memory.get(i),Episode)),key=lambda x:(x.occurred_at,str(x.id)))
        for first,second in zip(episodes,episodes[1:]):
            if first.occurred_at<second.occurred_at:add(InferenceType.TEMPORAL_ORDER,(first.id,second.id),(),"canonical occurred_at orders BEFORE",1)
        if len(active)<2 or (not seen_edges and not paths):
            add(InferenceType.MISSING_LINK,tuple(sorted(active,key=_key)),(),"no bounded canonical link found",0)
        return tuple(records),len(paths)
