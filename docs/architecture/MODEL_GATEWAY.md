# ModelGateway

ModelGateway is SYUNE's provider-neutral boundary for reliable model execution. It turns a logical request into one durable semantic result while enforcing authorization, budgets, retries, structured-output validation, evidence handling, and idempotency.

## Request and result contracts

A request identifies the logical call, purpose and role; supplies trusted messages, capabilities, and an optional output schema and deterministic validator; selects permitted provider/model constraints; references timeout, retry, repair, fallback, budget, and data policies; and carries principal and access context.

The request fingerprint covers every execution-relevant field, including validator identity. Reusing a logical call ID with a different fingerprint fails with `IDEMPOTENCY_CONFLICT`.

A result records execution and semantic-commit identifiers, state, normalized failure, provider and requested/resolved model, provider request identifier, attempts, quality, usage, cost, latency, policy version, and audit facts. A unique semantic commit prevents duplicate downstream effects. Callers perform state-changing work only after receiving a committed result.

## Structured generation

The gateway supports plain JSON prompting, native JSON Schema, compact schema, explicit repair, and caller-orchestrated two-stage generation. Native schema is preferred when the selected model declares support. Repair is explicit and separately metered; it receives only the schema, sanitized malformed output, and deterministic validation errors. It is not used to change a schema-valid but semantically wrong answer.

Provider finish state is evaluated before JSON parsing. Empty, truncated, refused, invalid JSON, schema-invalid, and semantic-invalid responses remain distinct failures.

## Execution invariants

- Authorization and data policy are checked before provider routing.
- Every attempt reserves hierarchical budget before transport.
- Retry, repair, and fallback are finite and cannot bypass a denied budget.
- Fallback is opt-in and capability-equivalent; exact-model requests never fall back.
- Circuit breakers count systemic provider/model failures, not semantic-invalid answers.
- Raw provider material is sanitized before durable evidence storage.
- Cross-process recovery returns an existing committed result rather than creating a second semantic effect.
- Unknown or ambiguous remote usage remains conservatively charged.

Operational policy is documented in [ModelGateway policy](../operations/model-gateway-policy.md), telemetry in [Observability](../operations/observability.md), recovery in [Recovery](../operations/recovery.md), and handling requirements in [ModelGateway data policy](../security/model-gateway-data-policy.md).
