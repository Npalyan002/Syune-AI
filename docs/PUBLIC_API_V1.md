# Public API v1

Package `1.1.0` exposes the frozen public API version `1`. `Syune` is synchronous,
lifecycle-managed, persistent across restart, and returns typed result envelopes with a
correlation ID and serializable `data`.

| Operation | Primary arguments | Result | Authorization/persistence |
|---|---|---|---|
| `remember` | text or `RememberRequest`; optional aware ISO 8601 `observed_at` | `RememberResult` | writes source + observation; optional security envelope |
| `add_batch` | `BatchAddRequest` with scoped request ID and ordered messages | `BatchAddResult` | atomic durable idempotent source + observation writes |
| `context` | cue/`ContextRequest`, identity, purpose, provenance mode | `ContextResult` | authorized bounded context; durable correlated audit |
| `revise` | typed memory ID, replacement content, identity/purpose | `RevisionResult` | requires access; old immutable; new revision persists |
| `forget` | typed memory ID, reason | `MemoryResult` | durable lifecycle exclusion and audit |
| `history` | typed memory ID | `HistoryResult` | persisted truth, provenance and lifecycle history |
| `audit` | limit/correlation | `AuditResult` | reads durable redacted audit |
| `model` | `ModelExecutionRequest` | `ModelResult` | requires configured gateway; gateway evidence and audit persist |
| `health` | optional correlation | `HealthResult` | read-only component state |

Recall, memory lookup, Study/source status, status, capabilities and handshake are also
stable v1 support surfaces. Principal identity is a user, agent, or service plus optional
organization/project/department scopes. Secured records deny missing principals, wrong
purpose and wrong scope with stable typed errors.

`RememberRequest.observed_at` is the source/event time. It must include `Z` or an
explicit UTC offset and is normalized to UTC. If omitted, it retains the historical
behavior of using the ingestion instant. It does not set fact-validity time. Source
registration, provenance creation, observation creation, and truth recording remain
separate ingestion/knowledge concepts.

## Idempotent batch ingestion

`Syune.add_batch()` is the reusable boundary for a future Agent Memory Leaderboard HTTP
adapter. A request contains a nonempty `request_id`, exact `user_id` and `session_id`, and
a nonempty tuple of `AddMessage` values whose ordinals are contiguous from zero. Request
ID uniqueness is scoped to the exact `(user_id, session_id)` pair.

SYUNE hashes the canonical normalized message payload. Repeating the same scoped request
ID and payload returns the original durable result and identifiers. Reusing it with a
different payload raises `IDEMPOTENCY_CONFLICT` without modifying memory. Each message is
stored as one owned Source and one owned Observation with deterministic IDs.

Entities, lifecycle rows, change-journal rows, and the completed idempotency record commit
in one SQLite `BEGIN IMMEDIATE` transaction. A crash before commit leaves no batch. A
crash after commit is a completed request: retry returns its stored result, synchronizes
the derived retrieval index, and only then acknowledges success. The audit database is a
separate downstream journal and is not the authority for idempotency or memory atomicity.

`SyuneError` exposes `code`, message, category, retryable/blocked metadata, safe resource
and operation IDs, and correlation ID. Stable codes include `UNAUTHORIZED`,
`MISSING_PRINCIPAL`, `PURPOSE_DENIED`, `SCOPE_DENIED`, `RECORD_NOT_FOUND`, lifecycle
states, `REVISION_CONFLICT`, model/provider availability, budget denial, and structured
output failure. Callers must not parse messages.

## Stability classification

- **STABLE_V1:** public `syune` exports, Lean SDK operations above, Lean MCP tools,
  public result/error serialization, state schema 1 semantics.
- **EXPERIMENTAL:** cognition, Council, Planner, Executive, learning and evaluation
  packages; disabled by default and not v1 product capabilities.
- **DEPRECATED:** legacy research MCP and lazy cognitive SDK compatibility calls.
- **INTERNAL:** repositories, SQLite adapters, provider adapters, product bootstrap,
  benchmark/test modules and implementation packages not exported by `syune.__all__`.

Additive optional fields are compatible. Removing/renaming required fields, changing
their meaning, or silently changing durable semantics is breaking. Scores indicate
retrieval relevance, not truth probability. No public API grants side-effect execution.
