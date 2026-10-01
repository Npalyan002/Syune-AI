"""Storage-agnostic memory repository and incremental reference adapter."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from syune.core import AssociationId,ClaimId,ConceptId,EpisodeId,EvidenceId,MemoryTraceId,ObservationId,ProcedureId,SourceId
from .model import Association,Claim,Concept,Episode,Evidence,MemoryTrace,NodeId,Observation,Procedure,Source
from .truth import TruthAuditEvent,classify_disagreement
from .lifecycle import LifecycleRecord,LifecycleState,MemoryClass

MemoryObject=Source|Observation|Concept|Claim|Evidence|Episode|Procedure|MemoryTrace
class DuplicateIdError(ValueError): pass
class MissingEndpointError(ValueError): pass

@dataclass(frozen=True,slots=True)
class RepositoryChange: sequence:int; operation:str; entity_id:NodeId

class MemoryRepository(Protocol):
    def put(self,entity:MemoryObject)->None: ...
    def put_many(self,entities:tuple[MemoryObject,...])->None: ...
    def replace(self,entity:MemoryObject,operation:str="UPDATE")->None: ...
    def get(self,entity_id:NodeId)->MemoryObject|None: ...
    def get_many(self,entity_ids:tuple[NodeId,...])->tuple[MemoryObject,...]: ...
    def exists(self,entity_id:NodeId)->bool: ...
    def entity_count(self)->int: ...
    def changes_since(self,cursor:int,limit:int=1024)->tuple[int,tuple[MemoryObject,...]]: ...
    def add_association(self,association:Association)->None: ...
    def get_association(self,association_id:AssociationId)->Association|None: ...
    def associations_for(self,entity_id:NodeId)->tuple[Association,...]: ...
    def iter_entities(self)->tuple[MemoryObject,...]: ...
    def truth_events(self)->tuple[TruthAuditEvent,...]: ...
    def lifecycle(self,entity_id:NodeId)->LifecycleRecord: ...
    def set_lifecycle(self,record:LifecycleRecord)->None: ...
    def transition_lifecycle(self,entity_id:NodeId,state:LifecycleState,reason:str)->None: ...

def _truth_events(entities):
    events=[]
    for entity in entities:
        truth=getattr(entity,"truth",None)
        if truth is None or truth.recorded_at is None: continue
        kind={"VERIFIED":"memory_verified","DISPUTED":"memory_disputed","SUPERSEDED":"memory_superseded","INVALIDATED":"memory_invalidated"}.get(truth.state.value)
        if kind: events.append(TruthAuditEvent(kind,entity.id,truth.recorded_at,None,truth.state,"stored truth metadata"))
        for target in truth.supersedes: events.append(TruthAuditEvent("memory_superseded",target,truth.recorded_at,None,truth.state,f"superseded by {entity.id}"))
    for pos,left in enumerate(entities):
        lt=getattr(left,"truth",None)
        if lt is None or lt.recorded_at is None: continue
        for right in entities[pos+1:]:
            rt=getattr(right,"truth",None)
            if rt is not None and classify_disagreement(lt,rt).value=="CONTRADICTION":
                events.append(TruthAuditEvent("contradiction_detected",left.id,max(lt.recorded_at,rt.recorded_at or lt.recorded_at),None,lt.state,f"conflicts with {right.id}"))
    return tuple(events)

class InMemoryReferenceRepository:
    """Ephemeral reference adapter with a bounded incremental change journal."""
    def __init__(self):
        self._entities={}; self._associations={}; self._sequence=0; self._changes=[]
        self._lifecycle={}; self._lifecycle_events=[]; self._purged=0
    def _record(self,operation,entity_id):
        self._sequence+=1; self._changes.append(RepositoryChange(self._sequence,operation,entity_id))
    def put(self,entity):
        if not isinstance(entity,(Source,Observation,Concept,Claim,Evidence,Episode,Procedure,MemoryTrace)): raise TypeError("unsupported memory entity")
        if entity.id in self._entities: raise DuplicateIdError(f"duplicate entity ID: {entity.id}")
        if isinstance(entity,Evidence) and any(cid not in self._entities for cid in entity.claim_ids): raise MissingEndpointError("evidence claim IDs must exist")
        if isinstance(entity,MemoryTrace) and entity.entity_id not in self._entities: raise MissingEndpointError("trace target must exist")
        self._entities[entity.id]=entity; self._record("INSERT",entity.id)
        self._lifecycle[entity.id]=LifecycleRecord(entity.id,created_at=getattr(entity,"created_at",None) or getattr(entity,"registered_at"),
                                                    memory_class=MemoryClass.ORGANIZATIONAL if isinstance(entity,Source) else MemoryClass.SEMANTIC,
                                                    protected=isinstance(entity,Source))
    def put_many(self,entities):
        original=self._entities.copy(); lifecycle=self._lifecycle.copy(); seq=self._sequence; changes=list(self._changes)
        try:
            for entity in entities:self.put(entity)
        except Exception:
            self._entities=original; self._lifecycle=lifecycle; self._sequence=seq; self._changes=changes; raise
    def replace(self,entity,operation="UPDATE"):
        if entity.id not in self._entities: raise KeyError(entity.id)
        self._entities[entity.id]=entity; self._record(operation,entity.id)
    @staticmethod
    def _require_node_id(entity_id):
        if not isinstance(entity_id,(SourceId,ObservationId,ConceptId,ClaimId,EvidenceId,EpisodeId,ProcedureId,MemoryTraceId)): raise TypeError("expected typed node ID")
    def get(self,entity_id): self._require_node_id(entity_id); return self._entities.get(entity_id)
    def get_many(self,ids): return tuple(item for item in (self.get(i) for i in ids) if item is not None)
    def exists(self,entity_id): self._require_node_id(entity_id); return entity_id in self._entities
    def entity_count(self): return len(self._entities)
    def changes_since(self,cursor,limit=1024):
        changes=[c for c in self._changes if c.sequence>cursor][:limit]
        return (changes[-1].sequence if changes else cursor,self.get_many(tuple(c.entity_id for c in changes)))
    def add_association(self,a):
        if not isinstance(a,Association): raise TypeError("expected Association")
        if a.id in self._associations: raise DuplicateIdError(f"duplicate association ID: {a.id}")
        if a.source_id not in self._entities or a.target_id not in self._entities: raise MissingEndpointError("both association endpoints must exist")
        self._associations[a.id]=a
    def get_association(self,association_id):
        if not isinstance(association_id,AssociationId): raise TypeError("expected AssociationId")
        return self._associations.get(association_id)
    def associations_for(self,entity_id):
        self._require_node_id(entity_id); return tuple(x for x in self._associations.values() if x.source_id==entity_id or x.target_id==entity_id)
    def iter_entities(self): return tuple(sorted(self._entities.values(),key=lambda x:(type(x.id).__name__,str(x.id))))
    def truth_events(self): return _truth_events(self.iter_entities())
    def lifecycle(self,entity_id):
        self._require_node_id(entity_id); return self._lifecycle.get(entity_id,LifecycleRecord(entity_id))
    def set_lifecycle(self,record):
        prior=self._lifecycle.get(record.entity_id); self._lifecycle[record.entity_id]=record
        self._record("LIFECYCLE",record.entity_id); self._lifecycle_events.append((record.entity_id,prior.state if prior else None,record.state,record.reason))
    def transition_lifecycle(self,entity_id,state,reason):
        from dataclasses import replace
        from syune.core import utc_now
        current=self.lifecycle(entity_id)
        if current.state is LifecycleState.PURGED: raise ValueError("purged memory cannot transition")
        if current.state is LifecycleState.FORGOTTEN and state is LifecycleState.ACTIVE: raise ValueError("forgotten memory requires administrative recovery policy")
        self.set_lifecycle(replace(current,state=state,changed_at=utc_now(),reason=reason))
    def reinforce(self,entity_id,reason):
        from dataclasses import replace
        from syune.core import utc_now
        current=self.lifecycle(entity_id); self.set_lifecycle(replace(current,last_reinforced_at=utc_now(),reinforcement_count=current.reinforcement_count+1,reason=reason))
    def record_access(self,entity_id):
        from dataclasses import replace
        current=self.lifecycle(entity_id); self._lifecycle[entity_id]=replace(current,access_count=current.access_count+1)
    def find_active_fingerprint(self,fingerprint):
        return next((key for key,value in self._lifecycle.items() if value.state is LifecycleState.ACTIVE and value.content_fingerprint==fingerprint),None)
    def lifecycle_scan(self,cursor,limit):
        values=tuple(sorted(self._lifecycle.values(),key=lambda x:(type(x.entity_id).__name__,str(x.entity_id))))
        return min(len(values),cursor+limit),values[cursor:cursor+limit]
    def lifecycle_changes_since(self,cursor,limit=1024):
        changes=[c for c in self._changes if c.sequence>cursor and c.operation=="LIFECYCLE"][:limit]
        return (changes[-1].sequence if changes else cursor,tuple((c.entity_id,self.lifecycle(c.entity_id).state) for c in changes))
    def purge(self,entity_id,reason):
        self.transition_lifecycle(entity_id,LifecycleState.PURGED,reason); self._entities.pop(entity_id,None); self._purged+=1
    def lifecycle_events(self): return tuple(self._lifecycle_events)
    def lifecycle_metrics(self):
        from .lifecycle import LifecycleMetrics
        counts={state:0 for state in LifecycleState}
        for value in self._lifecycle.values(): counts[value.state]+=1
        consolidated=sum(bool(value.source_memory_ids) for value in self._lifecycle.values())
        return LifecycleMetrics(counts[LifecycleState.ACTIVE],counts[LifecycleState.ARCHIVED],counts[LifecycleState.FORGOTTEN],self._purged,consolidated,0,0.0)
