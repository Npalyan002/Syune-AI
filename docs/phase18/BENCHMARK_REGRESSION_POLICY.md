# Benchmark regression policy

`benchmarks/config/regression_policy.v1.json` configures maximum task-success and recall regression, false-memory count, p95 latency, total tokens, and required permission-violation count. The default permission requirement is zero and is a hard gate. Thresholds are policy values, not universal quality claims.

Comparison output exposes quality, task success, context, latency, token, cost, and storage deltas separately. A candidate can improve recall while failing the latency or permission gate; the report retains that trade-off.

The default file is a starting CI policy. Teams should version policy changes and justify them against a workload. Missing measurements remain visible and do not become fabricated passes for quality claims.
