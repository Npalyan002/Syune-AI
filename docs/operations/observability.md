# ModelGateway observability

ModelGateway metrics cover logical calls, attempts, first-attempt and eventual success, retry, repair, fallback, terminal failure, normalized failure classes, attempt-latency percentiles, tokens, and cost. Cost can be grouped by role, provider, and model.

Durable attempt evidence supports schema-level analysis. Production exporters should identify schemas through non-sensitive fingerprints rather than schema contents. Provider identifiers and sanitized request metadata may be retained when policy permits; secrets and raw sensitive payloads must not appear in metrics or logs.

Operators should monitor budget denials, circuit transitions, ambiguous remote completions, fallback rate, repair overhead, unknown usage, and the difference between provider success and committed semantic success.
