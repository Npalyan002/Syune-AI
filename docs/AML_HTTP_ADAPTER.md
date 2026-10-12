# Agent Memory Leaderboard Textual HTTP adapter

This v2.0 adapter implements the current published Textual Memory Add/Search contract
from the [official AML API guide](https://agentmemoryleaderboard.ai/api-guide), inspected
on 2026-10-11. Deployment configuration is maintained separately under `deploy/aml`.

## Contract mapping

- `GET /health` is unauthenticated and returns a 2xx response.
- `POST /add` accepts exact `request_id`, `user_id`, `session_id`, and one to twenty
  ordered `{role, content, timestamp?}` messages. Roles are `user` or `assistant`,
  Textual content is a nonempty string, and timestamp is an optional strict Unix-ms
  integer.
- `/add` returns exactly `success`, `request_id`, `user_id`, and `session_id` after the
  SDK transaction commits and its native retrieval index synchronizes.
- `POST /search` accepts string `query`, exact `user_id`, `top_k` from 1 through 100,
  and an optional array of string `options`. Options are validated but never used to
  infer answers.
- `/search` calls native `Syune.recall()`. It returns candidates in native rank order as
  `{id, content, score, created_at}` and returns `{"data":[]}` for no matches.

The published guide calls `request_id` the unique logical chunk identifier but does not
state whether its namespace is global or user/session scoped. The SDK’s general-purpose
contract is scoped to `(user_id, session_id, request_id)`. This AML adapter deliberately
enforces the stricter global `request_id` interpretation using a reservation committed in
the same SQLite transaction. Reuse under another user, another session, or another
payload returns HTTP 409. This global namespace is stricter than the SDK scope and
should be disclosed to integrators.

## Local launch

Choose a new, dedicated absolute directory. The adapter refuses a populated directory
unless it contains the adapter ownership marker created inside SYUNE metadata.

```powershell
$env:SYUNE_AML_STATE_ROOT = 'C:\absolute\aml-evaluation-state'
$env:SYUNE_AML_BEARER_TOKEN = '<evaluation-only-secret>'
python -m uvicorn syune.adapters.aml.v1:app_from_environment --factory --host 127.0.0.1 --port 8080
```

Optional settings are `SYUNE_AML_MAX_BODY_BYTES` (default 1 MiB) and
`SYUNE_AML_MAX_CONCURRENCY` (default 4). Do not point the adapter at personal or
development SYUNE state.

## Examples

```json
{
  "request_id": "eval:run:sample:chunk-0",
  "messages": [
    {"role": "user", "content": "The launch code is violet.", "timestamp": 1704067200000}
  ],
  "user_id": "eval:run:user-1",
  "session_id": "eval:run:session-1"
}
```

```json
{"success":true,"request_id":"eval:run:sample:chunk-0","user_id":"eval:run:user-1","session_id":"eval:run:session-1"}
```

```json
{"query":"What is the launch code?","options":["A. violet","B. orange"],"user_id":"eval:run:user-1","top_k":100}
```

```json
{"data":[{"id":"ObservationId:...","content":"The launch code is violet.","score":7.25,"created_at":"2024-01-01T00:00:00Z"}]}
```

## Security and operations

Add and Search require exact `Authorization: Bearer <token>` authentication using
constant-time token comparison. Health is public. Request bodies are size-limited before
JSON parsing. Validation and internal failures return sanitized responses without request
content, database details, or secrets. No request/payload logging is configured.

Calls run through a bounded executor. Each worker opens and closes its own public SDK
  client, so SQLite connections never migrate across arbitrary request threads. The state
  root config fixes native retrieval output capacity at 100. The adapter does not call a
  generative model, assemble context, rerank, interpret options, or produce answers.
  Native retrieval does use the default local `deterministic-token-v1` feature-hashing
  provider to create 64-dimensional vectors for its semantic route. This is not a
  network model call, but it is vectorization through the embedding-provider interface.

This module supports Textual Memory only. Multimodal content arrays and Coding-specific
payloads are unsupported. TLS termination, rate limiting, secret files, and container
controls are supplied by the separate [deployment runbook](AML_DEPLOYMENT_RUNBOOK.md);
they are not implemented inside the FastAPI application.

The deterministic feature-hashing interpretation remains under AML organizer review.
No official AML Smoke, Full score, leaderboard rank, or organizer approval is claimed.

## Evaluation-data deletion

AML evaluation data must be deleted within 30 days after a run. For an ordinary
directory-backed state root, stop the adapter first, then call
`cleanup_evaluation_state()` with the exact resolved evaluation root as both
the target and explicit confirmation. Cleanup refuses relative paths, symlink roots,
broad filesystem roots, confirmation mismatches, and roots without the AML ownership
marker.

For the Docker named volume `aml_aml_state`, do not attempt to remove its mounted root
from inside a running container. Follow the separately approval-gated exact-volume
procedure in `deploy/hetzner/PHASE06B_PRODUCTION_READINESS.md`. Never use a broad volume
prune or delete TLS, bearer-token, configuration, or deployment-source files.

The operation removes the entire marked evaluation tree, including memory, audit and
learning databases, idempotency records, state/session metadata, artifacts, cache,
temporary files, logs, and any backups or snapshots kept inside that tree. Backups stored
outside the marked root are not discoverable by the adapter and must be deleted through
the operator's backup system within the same 30-day deadline.

```python
from pathlib import Path
from syune.adapters.aml import cleanup_evaluation_state

root = Path(r"C:\absolute\aml-evaluation-state").resolve()
cleanup_evaluation_state(root, confirm_root=str(root))
```

## Operational readiness

- Run one application process with the configured bounded executor. Multiple web-server
  workers create independent in-memory indexes and increase SQLite writer contention.
- Start with `SYUNE_AML_MAX_CONCURRENCY=4`; reduce it if Add latency or lock waits rise.
- SQLite is a single-writer database. Keep the state on local durable storage, monitor
  database/WAL and free-disk growth, and retain enough headroom for temporary journals.
- AML permits requests to run for up to 30 minutes. Reverse-proxy and application
  timeouts must be aligned without returning success before SDK completion.
- Public operation requires HTTPS termination, an external rate limiter, securely
  injected/rotated bearer secrets, and monitoring of status, latency, queue saturation,
  disk space, database errors, and counts only—never request or response payloads.
- `/health` is a liveness endpoint. A deployment should add infrastructure readiness
  checks for writable disk and database access without exposing private state.
