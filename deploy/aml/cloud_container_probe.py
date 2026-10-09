"""Synthetic HTTPS checks for the manually dispatched container workflow."""
from __future__ import annotations

import argparse
import json
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


PRIVATE_MARKER = "cloud-private-payload-7f19"


def request(base: str, path: str, *, token: str | None = None,
            payload: object | None = None) -> tuple[int, dict, object]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    call = urllib.request.Request(base + path, data=body, headers=headers,
                                  method="GET" if payload is None else "POST")
    context = ssl._create_unverified_context()  # Synthetic CI certificate only.
    def decode(raw: bytes) -> object:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.decode("utf-8", errors="replace")
    try:
        with urllib.request.urlopen(call, context=context, timeout=30) as response:
            raw = response.read()
            return response.status, dict(response.headers), decode(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, dict(exc.headers), decode(raw)


def add_payload(batch: int) -> dict:
    return {
        "request_id": f"cloud-batch-{batch}",
        "user_id": "cloud-user-a",
        "session_id": f"cloud-session-{batch}",
        "messages": [
            {
                "role": "user" if ordinal % 2 == 0 else "assistant",
                "content": (
                    f"cloud validation shared retrieval marker {PRIVATE_MARKER} "
                    f"batch {batch} ordinal {ordinal}"
                ),
                "timestamp": 1_704_067_200_000 + batch * 100 + ordinal,
            }
            for ordinal in range(20)
        ],
    }


def search_payload() -> dict:
    return {
        "query": "cloud validation shared retrieval marker",
        "user_id": "cloud-user-a",
        "top_k": 100,
    }


def native_100_search_payload() -> dict:
    return {
        "query": "cloud century candidate marker",
        "user_id": "cloud-user-a",
        "top_k": 100,
    }


def wait_for_health(base: str) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            status, _, payload = request(base, "/health")
            if status == 200 and payload == {"status": "ok"}:
                return
        except OSError:
            pass
        time.sleep(1)
    raise AssertionError("health did not become ready")


def initial(base: str, token: str) -> None:
    wait_for_health(base)
    assert request(base, "/health")[2] == {"status": "ok"}
    assert request(base, "/ready")[0] == 404
    assert request(base, "/search", payload=search_payload())[0] == 401
    for batch in range(5):
        status, _, response = request(base, "/add", token=token, payload=add_payload(batch))
        assert status == 200
        assert response == {
            "success": True,
            "request_id": f"cloud-batch-{batch}",
            "user_id": "cloud-user-a",
            "session_id": f"cloud-session-{batch}",
        }
    assert request(base, "/add", token=token, payload=add_payload(0))[0] == 200
    status, _, response = request(base, "/search", token=token, payload=search_payload())
    assert status == 200 and 0 < len(response["data"]) < 100
    assert all(set(item) == {"id", "content", "score", "created_at"}
               for item in response["data"])


def seed_native_100(state_root: Path) -> None:
    """Create a synthetic native graph that can legitimately expand to 100 hits."""
    from datetime import datetime, timezone
    from uuid import UUID

    from syune.core import AssociationId, ConceptId, Confidence, ProvenanceId, SourceId
    from syune.memory import Association, Concept, Provenance, SecurityEnvelope, Source
    from syune.product.config import load_config
    from syune.product.runtime import SyuneRuntime

    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    security = SecurityEnvelope(owner="user:cloud-user-a")
    source_id = SourceId(UUID(int=500_000))
    provenance = Provenance(ProvenanceId(UUID(int=500_001)), source_id, at)
    with SyuneRuntime.open(load_config(cli_state_root=state_root)) as runtime:
        runtime.memory.put(Source(source_id, "test", "cloud-native-100", at,
                                  security=security))
        concepts = []
        for index in range(100):
            concept = Concept(
                ConceptId(UUID(int=501_000 + index)),
                "cloud century candidate marker",
                provenance,
                Confidence(.5),
                at,
                security=security,
            )
            runtime.memory.put(concept)
            concepts.append(concept)
        for index in range(32, 100):
            runtime.memory.add_association(Association(
                AssociationId(UUID(int=502_000 + index)),
                concepts[(index - 32) % 32].id,
                concepts[index].id,
                "associated_with",
                provenance,
                Confidence(.8),
                at,
                1.0,
            ))
        runtime.index.sync()


def native_100(base: str, token: str) -> None:
    status, _, response = request(
        base, "/search", token=token, payload=native_100_search_payload()
    )
    assert status == 200 and len(response["data"]) == 100
    scores = [item["score"] for item in response["data"]]
    assert scores == sorted(scores, reverse=True)


def after_restart(base: str, token: str) -> None:
    wait_for_health(base)
    assert request(base, "/add", token=token, payload=add_payload(0))[0] == 200
    changed = add_payload(0)
    changed["messages"][0]["content"] = "conflicting synthetic content"
    status, _, response = request(base, "/add", token=token, payload=changed)
    assert status == 409 and response == {"detail": {"reason": "request_id conflict"}}
    status, _, response = request(base, "/search", token=token, payload=search_payload())
    assert status == 200 and 0 < len(response["data"]) < 100
    native_100(base, token)

    def concurrent(index: int) -> int:
        if index % 2:
            return request(base, "/search", token=token, payload=search_payload())[0]
        payload = {
            "request_id": f"cloud-concurrent-{index}",
            "user_id": "cloud-user-a",
            "session_id": "cloud-concurrent",
            "messages": [{"role": "user", "content": f"concurrent marker {index}"}],
        }
        return request(base, "/add", token=token, payload=payload)[0]

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(concurrent, range(4))) == [200, 200, 200, 200]

    status, _, response = request(
        base, "/add", token=token,
        payload={"request_id": "invalid", "user_id": "u", "session_id": "s",
                 "messages": [{"role": "user", "content": "x", "timestamp": "bad"}]},
    )
    assert status == 422 and response == {"detail": {"reason": "invalid request schema"}}


def limits(base: str, token: str) -> None:
    oversized = {
        "request_id": "oversized",
        "user_id": "u",
        "session_id": "s",
        "messages": [{"role": "user", "content": "x" * 1_100_000}],
    }
    status, _, response = request(base, "/add", token=token, payload=oversized)
    assert status == 413 and PRIVATE_MARKER not in str(response)
    limited = None
    for _ in range(64):
        status, headers, _ = request(base, "/search", token=token, payload=search_payload())
        if status == 429:
            limited = headers
            break
    assert limited is not None and limited.get("Retry-After") == "1"


def persistence(base: str, token: str) -> None:
    wait_for_health(base)
    assert request(base, "/add", token=token, payload=add_payload(0))[0] == 200
    status, _, response = request(base, "/search", token=token, payload=search_payload())
    assert status == 200 and 0 < len(response["data"]) < 100
    native_100(base, token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase", required=True,
        choices=("initial", "seed-native-100", "native-100", "after-restart",
                 "persistence", "limits"),
    )
    parser.add_argument("--base", default="https://127.0.0.1")
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--state-root", type=Path)
    args = parser.parse_args()
    if args.phase == "seed-native-100":
        if args.state_root is None:
            parser.error("--state-root is required for seed-native-100")
        seed_native_100(args.state_root)
        print(json.dumps({"phase": args.phase, "status": "passed"}))
        return
    if args.token_file is None:
        parser.error("--token-file is required for HTTP probe phases")
    token = args.token_file.read_text(encoding="utf-8").strip()
    {"initial": initial, "native-100": native_100, "after-restart": after_restart,
     "persistence": persistence, "limits": limits}[
        args.phase](args.base, token)
    print(json.dumps({"phase": args.phase, "status": "passed"}))


if __name__ == "__main__":
    main()
