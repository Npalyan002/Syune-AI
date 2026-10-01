# Evidence store scale

| Attempts | DB size | Bytes/attempt | Write p95 | Lookup p95 | Audit p95 | Health aggregation |
|---:|---:|---:|---:|---:|---:|---:|
| 1K | 2,859,008 B | 2,859.0 | 51.50 ms | 0.089 ms | 0.013 ms | 0.335 ms |
| 10K | 27,996,160 B | 2,799.6 | 41.64 ms | 0.125 ms | 0.016 ms | 2.92 ms |
| 100K | 279,990,272 B | 2,799.9 | 0.214 ms* | 0.120 ms | 0.015 ms | 24.42 ms |

The 1K/10K points measure per-attempt commits. The 100K tail uses 1K-row transaction batching, so
its write latency is per-row within a batch and must not be compared directly with durable singleton
writes. Query plans use indexes for logical call, attempt ID, provider/model, state/timestamp and
request fingerprint. No required hot-path full scan remains. Evidence: `store_scale_v2/report.json`.
