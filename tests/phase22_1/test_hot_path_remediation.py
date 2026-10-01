from dataclasses import replace
from datetime import datetime, timezone
from threading import Thread

from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import AccessContext, InMemoryReferenceRepository, Observation, Principal, Provenance, SecurityEnvelope, Source, TruthMetadata, TruthState
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService

NOW=datetime(2026,1,1,tzinfo=timezone.utc)

class CountingRepository(InMemoryReferenceRepository):
    def __init__(self): super().__init__(); self.snapshots=0; self.change_reads=0
    def iter_entities(self): self.snapshots+=1; return super().iter_entities()
    def changes_since(self,cursor,limit=1024): self.change_reads+=1; return super().changes_since(cursor,limit)

def setup_memory():
    repo=CountingRepository(); source=Source(SourceId.new(),"test","phase22.1",NOW); repo.put(source)
    def add(text,security=None,truth=None):
        item=Observation(ObservationId.new(),text,"text",Provenance(ProvenanceId.new(),source.id,NOW),NOW,NOW,Confidence(1),truth or TruthMetadata(),security=security)
        repo.put(item); return item
    return repo,add

def test_query_and_incremental_sync_do_not_snapshot_repository():
    repo,add=setup_memory(); first=add("Mercury migration owner Avery"); index=InvertedSeedIndex(repo); index.rebuild()
    baseline_reads=repo.change_reads; add("Juniper release checkpoint"); index.sync()
    result=RetrievalService(repo,index).recall(RecallRequest(RecallCue(text="Mercury migration owner")))
    assert first.id in {x.entity_id for x in result.working_memory}
    assert repo.snapshots==0 and repo.change_reads>baseline_reads

def test_broad_postings_are_bounded_and_observable():
    repo,add=setup_memory()
    for number in range(3000): add(f"project system memory item {number}")
    index=InvertedSeedIndex(repo); index.rebuild(); hits=index.lexical("project system memory",5)
    assert len(hits)==5 and index.generated_candidates==index.max_lexical_candidates==2048 and index.ranked_candidates==5

def test_security_and_truth_changes_apply_without_rebuild():
    repo,add=setup_memory(); item=add("private Atlas project",SecurityEnvelope(owner="user:alice"))
    index=InvertedSeedIndex(repo); index.rebuild(); service=RetrievalService(repo,index)
    alice=AccessContext(Principal("alice","agent-a"),"research",legacy_local_compatible=False)
    assert service.recall(RecallRequest(RecallCue(text="private Atlas project",access_context=alice))).working_memory
    repo.replace(replace(item,security=SecurityEnvelope(owner="user:bob")),"SECURITY_CHANGE"); index.sync()
    assert not service.recall(RecallRequest(RecallCue(text="private Atlas project",access_context=alice))).working_memory
    changed=replace(repo.get(item.id),truth=TruthMetadata(TruthState.INVALIDATED,recorded_at=NOW))
    repo.replace(changed,"INVALIDATE"); index.sync()
    assert not service.recall(RecallRequest(RecallCue(text="private Atlas project"))).working_memory

def test_query_during_writes_and_sync_is_race_safe():
    repo,add=setup_memory(); add("stable deployment checkpoint"); index=InvertedSeedIndex(repo); index.rebuild(); errors=[]
    def writer():
        try:
            for number in range(100): add(f"project memory {number}")
            index.sync()
        except Exception as exc: errors.append(exc)
    thread=Thread(target=writer); thread.start()
    while thread.is_alive():
        try: index.lexical("deployment checkpoint",5)
        except Exception as exc: errors.append(exc)
    thread.join(); assert not errors
