# Failure injection

Phase 29 supplies transport, 429, 5xx, timeout, truncation, JSON, schema, semantic, budget, circuit,
model and provider failure injection. Phase 30 asserts that a non-committed gateway result invokes
no cognitive mutator. Multi-write mutation failure rolls back both effect and transaction marker.
Replay and eight concurrent applications create one effect. Gateway owns model retry, repair and
fallback; the cognitive service has no nested provider recovery loop.

Terminal failures map to explicit `MODEL_EXECUTION_UNAVAILABLE:<class>`. Callers may translate that
to ABSTAIN, DEFER or UNAVAILABLE but may not fabricate cognitive output.
