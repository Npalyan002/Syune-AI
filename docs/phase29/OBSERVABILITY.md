# Observability

Metrics expose logical calls, attempts, first/eventual success, retry, repair, fallback, terminal
failure, every normalized failure class, p50/p95/p99 attempt latency, tokens and cost. Cost is
grouped by role, provider and model. Durable attempt evidence supports schema-level analysis;
production exporters should label schema by a non-sensitive schema fingerprint.
