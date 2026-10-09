# Python SDK v1

Install the package and initialize an absolute state root:

```console
pip install syune==2.0.0
syune init --state-root /absolute/path/to/state
```

SDK v1 is synchronous, local, and in-process. It requires no LLM or provider credential
for governed memory, context, lifecycle, audit, or Study.

## Lean memory and context

```python
from pathlib import Path
from syune import AddMessage, BatchAddRequest, ContextRequest, ProvenanceMode, RememberRequest, ReviseRequest, Syune, TypedId

with Syune.open(state_root=Path("/absolute/path/to/state")) as client:
    stored = client.remember("The deployment window is Friday at 18:00 UTC.")
    timestamped = client.remember(RememberRequest(
        "The sensor reported 21.4 C.",
        observed_at="2026-05-01T14:30:00-04:00",
    ))
    batch = client.add_batch(BatchAddRequest(
        request_id="add-00042",
        user_id="user-7",
        session_id="session-9",
        messages=(
            AddMessage(0, "First ordered message"),
            AddMessage(1, "Second ordered message", observed_at="2026-05-01T18:30:00Z"),
        ),
    ))
    context = client.context(ContextRequest(
        "deployment window",
        purpose="release-planning",
        provenance_mode=ProvenanceMode.FULL,
    ))
    memory_id = TypedId.parse(stored.data["memory_id"])
    revised = client.revise(ReviseRequest(memory_id, "The window is Friday at 19:00 UTC."))
    history = client.history(stored.data["memory_id"])
    audit = client.audit()
```

The stable Lean client covers open/close, remember, recall/context, revise, history,
lifecycle operations, audit, and optional model execution through an explicitly attached
ModelGateway. Prefer the context manager; closing is idempotent.

## Stable single-file Study

Configure allowed absolute source directories with `SYUNE_STUDY_ROOTS` or
`config.toml`, then use `StudyRequest` with an absolute TXT, Markdown, or text-PDF path:

```python
from pathlib import Path
from syune import StudyRequest, Syune, TypedId

with Syune.open(state_root=Path("/absolute/path/to/state")) as client:
    studied = client.study(StudyRequest(str(Path("/approved/library/notes.md"))))
    status = client.source_status(source_id=TypedId.parse(studied.data["source_id"]))
```

See [Study and ingestion](INGESTION.md) for formats, provenance, deduplication, revision,
and unsupported-input details. Study is an SDK operation, not a canonical Lean MCP tool.

## Errors and limits

Catch `SyuneError` and branch on its stable `code` or `category`. `retryable` is
explicit. A client owns one runtime graph and is limited-concurrency; create separate
clients for independently scheduled work and serialize writes to one state root.

`RememberRequest.observed_at` represents source/event time, not ingestion time,
knowledge-recording time, or fact-validity time. It accepts timezone-aware ISO 8601 and
normalizes it to UTC. Naive or malformed timestamps are rejected. Future event times are
stored as supplied and are not silently converted into truth validity intervals.

A future AML HTTP adapter receiving Unix milliseconds should convert at its boundary and
pass the SDK an aware ISO timestamp, for example:

```python
from datetime import datetime, timezone
from syune import RememberRequest

observed_at = datetime.fromtimestamp(unix_ms / 1000, tz=timezone.utc).isoformat()
request = RememberRequest(text=payload["text"], observed_at=observed_at)
```

The SDK API intentionally does not interpret a bare integer as a timestamp.

There is no async client, repository/DB accessor, reset, implicit initialization, folder
ingestion, or public execution-approval shortcut in v1.

## Experimental compatibility

Research cognition, Council, and Planner methods remain source-compatible for historical
consumers, but are experimental/deprecated, disabled by default, and outside the stable
Lean v1 product contract. New applications should not build on them.
