from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (LifecycleService, LifecycleState, MemoryClass, Observation,
                          Provenance, RetentionPolicy, SQLiteMemoryRepository, Source)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService


def fixture(path: Path):
    at=datetime(2024,1,1,tzinfo=timezone.utc); source_id=SourceId(UUID(int=1))
    repo=SQLiteMemoryRepository(path); repo.put(Source(source_id,"file","source",at))
    provenance=Provenance(ProvenanceId(UUID(int=2)),source_id,at)
    return repo,at,provenance


def observation(number, text, at, provenance):
    return Observation(ObservationId(UUID(int=number)),text,"text",provenance,at,at,Confidence(.8))


def test_archive_forget_purge_and_no_resurrection(tmp_path):
    path=tmp_path/"memory.sqlite3"; repo,at,p=fixture(path)
    a=observation(10,"durable orchard fact",at,p); repo.put(a)
    index=InvertedSeedIndex(repo); index.rebuild(); lifecycle=LifecycleService(repo)
    assert index.lexical("orchard",5)
    lifecycle.archive(a.id); index.sync(); assert not index.lexical("orchard",5)
    explicit=RetrievalService(repo,index).recall(RecallRequest(RecallCue(entity_ids=(a.id,),include_archived=True)))
    assert explicit.candidates[0].entity_id==a.id
    repo.close(); repo=SQLiteMemoryRepository(path); index=InvertedSeedIndex(repo); index.rebuild()
    assert not index.lexical("orchard",5)
    LifecycleService(repo).restore(a.id); index.sync(); assert index.lexical("orchard",5)
    LifecycleService(repo).forget(a.id); index.sync(); assert not index.lexical("orchard",5)
    with pytest.raises(ValueError): LifecycleService(repo).restore(a.id)
    LifecycleService(repo).purge(a.id); index.sync(); assert repo.get(a.id) is None
    repo.close(); repo=SQLiteMemoryRepository(path); index=InvertedSeedIndex(repo); index.rebuild()
    assert not index.lexical("orchard",5); assert repo.lifecycle(a.id).state is LifecycleState.PURGED


def test_duplicate_reinforcement_is_distinct_from_access(tmp_path):
    repo,at,p=fixture(tmp_path/"memory.sqlite3"); service=LifecycleService(repo)
    first=observation(10,"same fact",at,p); second=observation(11," SAME   fact ",at,p)
    assert service.register(first,MemoryClass.SEMANTIC) is None
    assert service.register(second,MemoryClass.SEMANTIC)==first.id
    assert repo.lifecycle(second.id).state is LifecycleState.ARCHIVED
    assert repo.lifecycle(second.id).source_memory_ids==(first.id,)
    assert repo.lifecycle(first.id).reinforcement_count==1
    service.access(first.id); assert repo.lifecycle(first.id).access_count==1
    assert repo.lifecycle(first.id).reinforcement_count==1


def test_bounded_decay_protection_and_truth_orthogonality(tmp_path):
    repo,at,p=fixture(tmp_path/"memory.sqlite3"); service=LifecycleService(repo)
    old=observation(10,"old episode",at,p); protected=observation(11,"policy",at,p)
    service.register(old,MemoryClass.WORKING)
    service.register(protected,MemoryClass.WORKING,protected=True)
    cursor,count=service.maintain(limit=1,now=at+timedelta(days=400))
    assert count==1 and cursor==1
    service.maintain(cursor=cursor,limit=10,now=at+timedelta(days=400))
    assert repo.lifecycle(old.id).state is LifecycleState.FORGOTTEN
    assert repo.lifecycle(protected.id).state is LifecycleState.ACTIVE
    assert old.truth.state.value=="OBSERVED"


def test_active_budget_triggers_bounded_policy_evaluation(tmp_path):
    repo,at,p=fixture(tmp_path/"memory.sqlite3")
    service=LifecycleService(repo,RetentionPolicy(active_budget=2))
    for number in range(10,14): service.register(observation(number,f"fact {number}",at,p))
    service.maintain(limit=10,now=at)
    assert repo.lifecycle_metrics().active==2
