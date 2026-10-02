# Public API v1

Package `1.0.3` exposes the frozen public API version `1`. `Syune` is synchronous,
lifecycle-managed, persistent across restart, and returns typed result envelopes with a
correlation ID and serializable `data`.

| Operation | Primary arguments | Result | Authorization/persistence |
|---|---|---|---|
| `remember` | text or `RememberRequest` | `RememberResult` | writes source + observation; optional security envelope |
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
