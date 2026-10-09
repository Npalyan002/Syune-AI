import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from syune import RememberRequest, Syune
from syune.adapters.aml import AdapterSettings, cleanup_evaluation_state, create_app
from syune.core import AssociationId, ConceptId, Confidence, ProvenanceId, SourceId
from syune.memory import Association, Concept, Provenance, SecurityEnvelope, Source
from syune.product.config import load_config
from syune.product.runtime import SyuneRuntime
from syune.product.state import DATABASES


TOKEN = "phase03-evaluation-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def root_for(tmp_path): return (tmp_path / "evaluation-state").resolve()


def client_for(tmp_path, **settings):
    return TestClient(create_app(AdapterSettings(root_for(tmp_path), TOKEN, **settings)))


def add(request_id, content, *, user="u1", session="s1", timestamp=None):
    message = {"role": "user", "content": content}
    if timestamp is not None: message["timestamp"] = timestamp
    return {"request_id": request_id, "messages": [message],
            "user_id": user, "session_id": session}


def search(query, *, user="u1", top_k=100):
    return {"query": query, "user_id": user, "top_k": top_k}


def test_legacy_unscoped_memory_does_not_leak_to_http_identity(tmp_path):
    root = root_for(tmp_path)
    with client_for(tmp_path): pass
    with Syune.open(state_root=root) as sdk:
        sdk.remember(RememberRequest("legacy unscoped secret"))
    with client_for(tmp_path) as client:
        result = client.post("/search", headers=AUTH, json=search("legacy unscoped secret"))
    assert result.status_code == 200 and result.json() == {"data": []}


def test_long_twenty_message_chunk_and_multi_session_recall(tmp_path):
    messages = [{"role": "user" if n % 2 == 0 else "assistant",
                 "content": f"conversation marker item {n}"} for n in range(20)]
    with client_for(tmp_path) as client:
        first = {"request_id": "long", "messages": messages,
                 "user_id": "u1", "session_id": "session-a"}
        assert client.post("/add", headers=AUTH, json=first).status_code == 200
        assert client.post("/add", headers=AUTH,
            json=add("other", "second session telescope fact", session="session-b")).status_code == 200
        assert client.post("/search", headers=AUTH,
            json=search("conversation marker item 19")).json()["data"]
        assert client.post("/search", headers=AUTH,
            json=search("telescope fact")).json()["data"]


def test_temporal_multilingual_and_overlapping_user_facts(tmp_path):
    timestamp = 1704067200123
    with client_for(tmp_path) as client:
        client.post("/add", headers=AUTH, json=add("a", "Գաղտնաբառը կապույտ է", timestamp=timestamp))
        client.post("/add", headers=AUTH, json=add("b", "Гաղտնաբառը կարմիր է", user="u2"))
        first = client.post("/search", headers=AUTH, json=search("Գաղտնաբառը", user="u1")).json()["data"]
        second = client.post("/search", headers=AUTH, json=search("կարմիր", user="u2")).json()["data"]
    assert first[0]["content"] == "Գաղտնաբառը կապույտ է"
    assert first[0]["created_at"] == "2024-01-01T00:00:00.123000Z"
    assert all("կարմիր" not in item["content"] for item in first)
    assert second and all("կապույտ" not in item["content"] for item in second)


def test_relevance_order_and_legitimate_empty_result(tmp_path):
    with client_for(tmp_path) as client:
        client.post("/add", headers=AUTH, json=add("relevant", "orchard budget allocation plan"))
        client.post("/add", headers=AUTH, json=add("noise", "coastal rainfall weather report"))
        ranked = client.post("/search", headers=AUTH, json=search("orchard budget")).json()["data"]
        empty = client.post("/search", headers=AUTH, json=search("orchard", user="unknown")).json()
    assert ranked[0]["content"] == "orchard budget allocation plan"
    assert empty == {"data": []}


def test_sqlite_lock_wait_recovers_without_partial_response(tmp_path):
    root = root_for(tmp_path)
    with client_for(tmp_path): pass
    lock = sqlite3.connect(root / DATABASES["memory"], timeout=1, check_same_thread=False)
    lock.execute("BEGIN IMMEDIATE")
    def release():
        time.sleep(.2); lock.rollback(); lock.close()
    releaser = threading.Thread(target=release)
    releaser.start()
    with client_for(tmp_path) as client:
        response = client.post("/add", headers=AUTH, json=add("locked", "lock recovery fact"))
    releaser.join()
    assert response.status_code == 200


def test_sqlite_and_disk_faults_are_sanitized_and_recoverable(tmp_path, monkeypatch):
    from syune.memory import SQLiteMemoryRepository
    original = SQLiteMemoryRepository.put_idempotent_batch
    def disk_full(*_args, **_kwargs):
        raise sqlite3.OperationalError("database or disk is full: private-path")
    monkeypatch.setattr(SQLiteMemoryRepository, "put_idempotent_batch", disk_full)
    with client_for(tmp_path) as client:
        failed = client.post("/add", headers=AUTH, json=add("disk", "private payload"))
    assert failed.status_code == 500
    assert failed.json() == {"detail": {"reason": "durable ingestion failed"}}
    assert "private" not in failed.text and "disk is full" not in failed.text
    monkeypatch.setattr(SQLiteMemoryRepository, "put_idempotent_batch", original)
    with client_for(tmp_path) as client:
        assert client.post("/add", headers=AUTH, json=add("disk", "private payload")).status_code == 200


def test_global_request_conflict_is_atomic_across_users(tmp_path):
    with client_for(tmp_path) as client:
        def invoke(user):
            return client.post("/add", headers=AUTH,
                json=add("global-request", f"fact for {user}", user=user)).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = sorted(pool.map(invoke, ("u1", "u2")))
    assert statuses == [200, 409]


def test_cleanup_deletes_complete_marked_tree_and_refuses_unsafe_targets(tmp_path):
    root = root_for(tmp_path)
    with client_for(tmp_path) as client:
        client.post("/add", headers=AUTH, json=add("cleanup", "cleanup memory"))
    for relative in ("logs/private.log", "artifacts/backup.sqlite3", "cache/temp.bin",
                     "metadata/session.json", "memory/snapshot.bak"):
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("synthetic")
    with pytest.raises(ValueError):
        cleanup_evaluation_state(root, confirm_root=str(root) + "-wrong")
    unmarked = (tmp_path / "personal-state").resolve(); unmarked.mkdir()
    with pytest.raises(ValueError):
        cleanup_evaluation_state(unmarked, confirm_root=str(unmarked))
    cleanup_evaluation_state(root, confirm_root=str(root))
    assert not root.exists()


def test_one_hundred_native_candidates_remain_ordered_through_http(tmp_path):
    root = root_for(tmp_path)
    with client_for(tmp_path): pass
    config = load_config(cli_state_root=root)
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    security = SecurityEnvelope(owner="user:u1")
    with SyuneRuntime.open(config) as runtime:
        sid = SourceId(UUID(int=1)); provenance = Provenance(ProvenanceId(UUID(int=2)), sid, at)
        runtime.memory.put(Source(sid, "test", "quality", at, security=security))
        concepts = []
        for n in range(100):
            item = Concept(ConceptId(UUID(int=100+n)), "century candidate marker", provenance,
                           Confidence(.5), at, security=security)
            runtime.memory.put(item); concepts.append(item)
        for n in range(32, 100):
            runtime.memory.add_association(Association(AssociationId(UUID(int=10000+n)),
                concepts[(n-32) % 32].id, concepts[n].id, "associated_with", provenance,
                Confidence(.8), at, 1.0))
        runtime.index.sync()
    with client_for(tmp_path) as client:
        response = client.post("/search", headers=AUTH, json=search("century candidate marker"))
    data = response.json()["data"]
    assert response.status_code == 200 and len(data) == 100
    assert [item["score"] for item in data] == sorted((item["score"] for item in data), reverse=True)
