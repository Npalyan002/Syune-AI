from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from syune.adapters.aml import AdapterSettings, create_app


TOKEN = "evaluation-secret-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def make_client(tmp_path, **overrides):
    settings = AdapterSettings(
        state_root=(tmp_path / "aml-evaluation").resolve(),
        bearer_token=TOKEN,
        **overrides,
    )
    return TestClient(create_app(settings))


def add_payload(request_id="request-1", user_id="user-1", messages=None):
    return {
        "request_id": request_id,
        "messages": messages or [{"role": "user", "content": "The launch code is violet."}],
        "user_id": user_id,
        "session_id": "session-1",
    }


def search_payload(query="launch code", user_id="user-1", top_k=100, **extra):
    return {"query": query, "user_id": user_id, "top_k": top_k, **extra}


def test_health_is_public_and_exact(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_add_and_search_have_exact_contract_shapes(tmp_path):
    with make_client(tmp_path) as client:
        added = client.post("/add", headers=AUTH, json=add_payload())
        assert added.status_code == 200
        assert added.json() == {"success": True, "request_id": "request-1",
                                "user_id": "user-1", "session_id": "session-1"}
        searched = client.post("/search", headers=AUTH, json=search_payload())
    assert searched.status_code == 200
    body = searched.json()
    assert set(body) == {"data"} and body["data"]
    assert set(body["data"][0]) == {"id", "content", "score", "created_at"}
    assert body["data"][0]["content"] == "The launch code is violet."
    assert isinstance(body["data"][0]["score"], float)


def test_unicode_ordered_messages_and_millisecond_timestamps(tmp_path):
    messages = [
        {"role": "user", "content": "Առաջին հիշողություն 🚀", "timestamp": 1704067200123},
        {"role": "assistant", "content": "第二条记忆 café"},
    ]
    with make_client(tmp_path) as client:
        assert client.post("/add", headers=AUTH, json=add_payload(messages=messages)).status_code == 200
        first = client.post("/search", headers=AUTH,
                            json=search_payload(query="Առաջին հիշողություն")).json()["data"]
        second = client.post("/search", headers=AUTH,
                             json=search_payload(query="第二条记忆")).json()["data"]
    assert first[0]["content"] == messages[0]["content"]
    assert first[0]["created_at"] == "2024-01-01T00:00:00.123000Z"
    assert second[0]["content"] == messages[1]["content"]


@pytest.mark.parametrize("payload", [
    {},
    {"request_id": "r", "user_id": "u", "session_id": "s", "messages": []},
    add_payload(messages=[{"role": "system", "content": "x"}]),
    add_payload(messages=[{"role": "user", "content": " "}]),
    add_payload(user_id=" "),
    add_payload(messages=[{"role": "user", "content": "x", "timestamp": "1704067200000"}]),
])
def test_invalid_add_parameters_are_sanitized(payload, tmp_path):
    with make_client(tmp_path) as client:
        response = client.post("/add", headers=AUTH, json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": {"reason": "invalid request schema"}}


@pytest.mark.parametrize("payload", [
    {}, search_payload(query=""), search_payload(user_id=" "),
    search_payload(top_k=0), search_payload(top_k=101), search_payload(top_k="100"),
    search_payload(options=["A", " "]), search_payload(filters={}),
])
def test_invalid_search_parameters_are_sanitized(payload, tmp_path):
    with make_client(tmp_path) as client:
        response = client.post("/search", headers=AUTH, json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": {"reason": "invalid request schema"}}


def test_bearer_authentication_and_no_secret_echo(tmp_path):
    with make_client(tmp_path) as client:
        for headers in ({}, {"Authorization": "Bearer wrong"},
                        {"Authorization": f"Token {TOKEN}"}):
            response = client.post("/search", headers=headers, json=search_payload())
            assert response.status_code == 401
            assert TOKEN not in response.text and "wrong" not in response.text


def test_identical_replay_and_global_conflict(tmp_path):
    payload = add_payload()
    with make_client(tmp_path) as client:
        first = client.post("/add", headers=AUTH, json=payload)
        replay = client.post("/add", headers=AUTH, json=payload)
        conflict = client.post("/add", headers=AUTH,
                               json=add_payload(messages=[{"role": "user", "content": "changed"}]))
        cross_user = client.post("/add", headers=AUTH,
                                 json=add_payload(user_id="user-2"))
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert conflict.status_code == cross_user.status_code == 409
    assert conflict.json() == {"detail": {"reason": "request_id conflict"}}


def test_restart_persistence_and_immediate_searchability(tmp_path):
    with make_client(tmp_path) as client:
        assert client.post("/add", headers=AUTH, json=add_payload()).status_code == 200
        assert client.post("/search", headers=AUTH, json=search_payload()).json()["data"]
    with make_client(tmp_path) as restarted:
        assert restarted.post("/add", headers=AUTH, json=add_payload()).status_code == 200
        assert restarted.post("/search", headers=AUTH, json=search_payload()).json()["data"]


def test_cross_user_isolation_and_empty_result(tmp_path):
    with make_client(tmp_path) as client:
        client.post("/add", headers=AUTH, json=add_payload())
        response = client.post("/search", headers=AUTH,
                               json=search_payload(user_id="different-user"))
    assert response.status_code == 200
    assert response.json() == {"data": []}


def test_top_k_100_and_legitimately_fewer_results(tmp_path):
    with make_client(tmp_path) as client:
        client.post("/add", headers=AUTH, json=add_payload())
        response = client.post("/search", headers=AUTH, json=search_payload(top_k=100))
    assert response.status_code == 200
    assert 0 < len(response.json()["data"]) < 100


def test_options_are_accepted_but_do_not_generate_answers(tmp_path):
    with make_client(tmp_path) as client:
        client.post("/add", headers=AUTH, json=add_payload())
        response = client.post("/search", headers=AUTH,
            json=search_payload(options=["A. violet", "B. orange"]))
    assert response.status_code == 200
    assert response.json()["data"][0]["content"] == "The launch code is violet."


def test_concurrent_add_and_search_use_bounded_owned_connections(tmp_path):
    client = make_client(tmp_path, max_concurrency=4)
    with client:
        client.post("/add", headers=AUTH, json=add_payload("seed"))
        def add(index):
            return client.post("/add", headers=AUTH,
                json=add_payload(f"concurrent-{index}", messages=[{
                    "role": "user", "content": f"concurrent marker {index}"}])).status_code
        def search(_):
            return client.post("/search", headers=AUTH,
                               json=search_payload(query="launch code")).status_code
        with ThreadPoolExecutor(max_workers=4) as pool:
            statuses = tuple(pool.map(lambda pair: pair[0](pair[1]),
                                      ((add, 1), (search, 0), (add, 2), (search, 0))))
    assert statuses == (200, 200, 200, 200)


def test_oversized_payload_is_rejected_before_parsing(tmp_path):
    with make_client(tmp_path, max_body_bytes=1024) as client:
        response = client.post("/add",
            content=b'{"request_id":"r","user_id":"u","session_id":"s","messages":[{"role":"user","content":"'
                    + b"x" * 2000 + b'"}]}',
            headers={**AUTH, "Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json() == {"detail": {"reason": "request body too large"}}


def test_non_dedicated_existing_state_root_is_rejected(tmp_path):
    root = (tmp_path / "not-dedicated").resolve(); root.mkdir()
    (root / "personal.sqlite3").write_text("do not touch", encoding="utf-8")
    with pytest.raises(ValueError, match="non-dedicated"):
        create_app(AdapterSettings(root, TOKEN))
