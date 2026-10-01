# Phase 29 production model-gateway policy

Policy version: `phase29-v1`.

The default structured strategy is native JSON schema when the selected model declares that
capability. Plain JSON remains available as a high-quality explicit strategy. Compact schema,
repair calls, and two-stage generation are represented but are not automatically deployed;
they require measured comparative evidence. Phase 29 makes no reliability SLO guarantee without
a live benchmark.

The frozen default retry policy is finite: two attempts, bounded backoff, and retries only for
rate limits, timeouts, connection/provider failures, and provider-declared truncation. Budget
reservation occurs before every attempt and therefore wins over retry or fallback. A transport
failure after request start but without a durable response is classified as
`REMOTE_COMPLETION_AMBIGUOUS`; it is not automatically retried by the default policy.

Fallback is opt-in. `EXACT_MODEL` uses one route. `CAPABILITY_EQUIVALENT` may traverse explicitly
configured routes and labels the result `FALLBACK`; callers may reject non-normal quality.
Circuit breakers count only systemic provider/model failures, not semantic-invalid answers.

Raw provider evidence is sanitized and durably stored before parsing or validation. API keys,
authorization headers, credentials, cookies, and session secrets are redacted. Provider request,
resolved model/version, finish metadata, usage, latency, cost reservation, policy version and all
attempts remain auditable. A unique logical-call commit prevents duplicate cognitive effects;
callers perform any cognitive transaction only after receiving a committed result.

Candidate SLOs for a future live benchmark are structured commit success, first-attempt success,
terminal failure rate, gateway-added latency, fallback rate, and repair overhead. Thresholds must
be set from production-representative evidence rather than invented here.
