# ModelGateway operational policy

The default structured-output strategy is native JSON Schema when the selected model supports it; otherwise deployments may select an explicitly configured supported strategy. Strategy choice is policy, not implicit provider behavior.

## Retry and repair

The default retry policy permits at most two attempts and retries only rate limits, timeouts, connection/provider failures, and provider-declared truncation. `Retry-After` is honored only within the overall timeout. A transport failure after request start without a durable response is `REMOTE_COMPLETION_AMBIGUOUS` and is terminal by default.

Repair is explicit, separately metered, and bounded. It receives sanitized malformed data and deterministic schema errors. It is never invoked for valid-but-wrong output.

## Fallback

Fallback is opt-in. `EXACT_MODEL` uses one route. `CAPABILITY_EQUIVALENT` may traverse only explicitly configured routes, and the result is marked `FALLBACK` so callers can reject non-normal quality.

## Budgets

Every attempt, including retry, repair, and fallback, reserves call count, estimated input, maximum output, and estimated cost before transport. Request, task, agent, project, organization, and experiment scopes share an atomic hierarchy. Any parent denial wins. Measured usage reconciles reservations; unknown usage remains conservatively charged.

## Circuit breaking and failures

Provider/model circuits open after the configured systemic-failure threshold. After the recovery interval, one half-open probe is admitted; success closes the circuit and failure reopens it. Rate limits, timeouts, connection failures, provider 5xx responses, and model unavailability contribute. Schema and semantic failures do not.

Normalized failures distinguish authentication, authorization, rate limit, timeout, connection or remote ambiguity, provider unavailable/5xx, missing model or capability, concurrency exhaustion, empty or truncated output, refusal, invalid JSON, schema-invalid, semantic-invalid, unknown usage, budget denial, open circuit, idempotency conflict, and unknown provider failure.

Production SLOs must be based on representative deployment evidence. The project does not infer reliability guarantees from small development benchmarks.
