import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from syune import AddMessage, BatchAddRequest, RecallRequest, Syune, SyuneError
from syune.memory import SQLiteMemoryRepository
from syune.product.config import load_config
from syune.product.state import DATABASES, initialize_state


def initialized_state(tmp_path):
    state = (tmp_path / "state").resolve()
    initialize_state(load_config(cli_state_root=state))
    with Syune.open(state_root=state):
        pass
    return state


def request(request_id="req-1", *, user_id="alice", session_id="session-1", suffix=""):
    return BatchAddRequest(request_id, user_id, session_id, (
        AddMessage(0, "alpha durable memory" + suffix, "2026-01-01T12:00:00-05:00"),
        AddMessage(1, "beta durable memory" + suffix),
    ))


def table_count(state, table):
    with sqlite3.connect(state / DATABASES["memory"]) as db:
        return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_first_batch_and_identical_replay_are_logically_identical(tmp_path):
    state = initialized_state(tmp_path)
    with Syune.open(state_root=state) as client:
        first = client.add_batch(request())
        replay = client.add_batch(request())
        assert first.data == replay.data
        assert len(first.data["messages"]) == 2
        assert first.data["messages"][0]["observed_at"] == "2026-01-01T17:00:00Z"
        assert client.recall(RecallRequest(cue="alpha durable", user_id="alice")).data["candidates"]
    assert table_count(state, "entities") == 4
    assert table_count(state, "idempotent_ingestion") == 1


def test_reused_id_with_different_payload_conflicts_without_mutation(tmp_path):
    state = initialized_state(tmp_path)
    with Syune.open(state_root=state) as client:
        original = client.add_batch(request())
        with pytest.raises(SyuneError) as error:
            client.add_batch(request(suffix=" changed"))
        assert error.value.code == "IDEMPOTENCY_CONFLICT"
        assert client.add_batch(request()).data == original.data
    assert table_count(state, "entities") == 4


@pytest.mark.parametrize("bad", [
    BatchAddRequest("r", "u", "s", ()),
    BatchAddRequest("", "u", "s", (AddMessage(0, "x"),)),
    BatchAddRequest("r", "", "s", (AddMessage(0, "x"),)),
    BatchAddRequest("r", "u", "s", (AddMessage(1, "x"),)),
    BatchAddRequest("r", "u", "s", (AddMessage(0, ""),)),
    BatchAddRequest("r", "u", "s", (AddMessage(0, "x", "2026-01-01T12:00:00"),)),
])
def test_empty_and_malformed_requests_fail_without_writes(tmp_path, bad):
    state = initialized_state(tmp_path)
    with Syune.open(state_root=state) as client, pytest.raises(SyuneError):
        client.add_batch(bad)
    assert table_count(state, "entities") == 0
    assert table_count(state, "idempotent_ingestion") == 0


def test_partial_batch_failure_rolls_back_everything(tmp_path, monkeypatch):
    state = initialized_state(tmp_path)
    original = SQLiteMemoryRepository._insert_entities
    def partial(self, entities):
        original(self, entities[:1])
        raise RuntimeError("injected partial write")
    monkeypatch.setattr(SQLiteMemoryRepository, "_insert_entities", partial)
    with Syune.open(state_root=state) as client, pytest.raises(SyuneError) as error:
        client.add_batch(request())
    assert error.value.code == "INTERNAL"
    assert table_count(state, "entities") == 0
    assert table_count(state, "lifecycle") == 0
    assert table_count(state, "idempotent_ingestion") == 0


def test_crash_before_commit_rolls_back_and_retry_writes_once(tmp_path, monkeypatch):
    state = initialized_state(tmp_path)
    original = SQLiteMemoryRepository._idempotent_fault
    def crash(self, stage):
        if stage == "before_commit":
            raise RuntimeError("injected pre-commit crash")
    monkeypatch.setattr(SQLiteMemoryRepository, "_idempotent_fault", crash)
    with Syune.open(state_root=state) as client, pytest.raises(SyuneError):
        client.add_batch(request())
    assert table_count(state, "entities") == 0
    monkeypatch.setattr(SQLiteMemoryRepository, "_idempotent_fault", original)
    with Syune.open(state_root=state) as client:
        client.add_batch(request())
    assert table_count(state, "entities") == 4


def test_crash_after_commit_replays_after_restart_without_duplicates(tmp_path, monkeypatch):
    state = initialized_state(tmp_path)
    original = SQLiteMemoryRepository._idempotent_fault
    crashed = False
    def crash_once(self, stage):
        nonlocal crashed
        if stage == "after_commit" and not crashed:
            crashed = True
            raise RuntimeError("injected lost acknowledgment")
    monkeypatch.setattr(SQLiteMemoryRepository, "_idempotent_fault", crash_once)
    with Syune.open(state_root=state) as client, pytest.raises(SyuneError):
        client.add_batch(request())
    assert table_count(state, "entities") == 4
    assert table_count(state, "idempotent_ingestion") == 1
    monkeypatch.setattr(SQLiteMemoryRepository, "_idempotent_fault", original)
    with Syune.open(state_root=state) as restarted:
        replay = restarted.add_batch(request())
        assert restarted.recall(RecallRequest(cue="beta durable", user_id="alice")).data["candidates"]
    assert len(replay.data["messages"]) == 2
    assert table_count(state, "entities") == 4


def test_concurrent_identical_requests_commit_once(tmp_path):
    state = initialized_state(tmp_path)
    def invoke():
        with Syune.open(state_root=state) as client:
            return client.add_batch(request()).data
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(lambda _: invoke(), range(2)))
    assert results[0] == results[1]
    assert table_count(state, "entities") == 4
    assert table_count(state, "idempotent_ingestion") == 1


def test_concurrent_conflicting_requests_have_one_winner(tmp_path):
    state = initialized_state(tmp_path)
    def invoke(suffix):
        try:
            with Syune.open(state_root=state) as client:
                return "ok", client.add_batch(request(suffix=suffix)).data
        except SyuneError as exc:
            return exc.code, None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(invoke, (" A", " B")))
    assert sorted(code for code, _ in results) == ["IDEMPOTENCY_CONFLICT", "ok"]
    assert table_count(state, "entities") == 4
    assert table_count(state, "idempotent_ingestion") == 1


def test_request_id_scope_is_user_and_session(tmp_path):
    state = initialized_state(tmp_path)
    with Syune.open(state_root=state) as client:
        alice = client.add_batch(request()).data
        bob = client.add_batch(request(user_id="bob")).data
        other_session = client.add_batch(request(session_id="session-2")).data
    assert alice["messages"][0]["memory_id"] != bob["messages"][0]["memory_id"]
    assert alice["messages"][0]["memory_id"] != other_session["messages"][0]["memory_id"]
    assert table_count(state, "entities") == 12


def test_user_ownership_blocks_cross_user_reads(tmp_path):
    state = initialized_state(tmp_path)
    with Syune.open(state_root=state) as client:
        result = client.add_batch(request()).data
        memory_id = result["messages"][0]["memory_id"]
        assert client.memory_get(memory_id, user_id="alice").data["entity_type"] == "Observation"
        with pytest.raises(SyuneError) as denied:
            client.memory_get(memory_id, user_id="bob")
        assert denied.value.code in {"UNAUTHORIZED", "SCOPE_DENIED"}
        assert not client.recall(RecallRequest(cue="alpha durable", user_id="bob")).data["candidates"]


def test_restart_rebuild_preserves_searchability_and_result(tmp_path):
    state = initialized_state(tmp_path)
    with Syune.open(state_root=state) as client:
        first = client.add_batch(request()).data
    with Syune.open(state_root=state) as restarted:
        assert restarted.add_batch(request()).data == first
        recalled = restarted.recall(RecallRequest(cue="alpha durable", user_id="alice"))
        assert recalled.data["candidates"]
