# Performance impact

Two hundred deterministic operations measured the boundary on the workspace filesystem:

| Path | p50 | p95 |
|---|---:|---:|
| legacy in-memory semantic contract | 0.025 ms | 0.032 ms |
| durable gateway + cognitive transaction | 412.27 ms | 505.24 ms |
| gateway-added overhead | 412.24 ms | 505.21 ms |

Fake-provider latency was 0.2 ms; usage was 2,000 input and 1,000 output tokens with synthetic cost
$0.003. This measures worst-case singleton SQLite durability in the sandbox, not live provider
latency. The overhead is material but bounded and buys raw evidence, semantic commit and atomic
cognitive application. Evidence: `evidence/performance_v1/report.json`.
