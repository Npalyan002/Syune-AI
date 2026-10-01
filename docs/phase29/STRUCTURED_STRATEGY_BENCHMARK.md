# Structured strategy benchmark

| Strategy | Commits | Median latency | Cost | Cost/commit |
|---|---:|---:|---:|---:|
| Plain JSON | 7/7 | 1709.9 ms | $0.005952 | $0.000850 |
| Native structured | 7/7 | 1717.4 ms | $0.006104 | $0.000872 |
| Compact schema | 7/7 | 2040.4 ms | $0.006557 | $0.000937 |
| Plain + repair eligible | 7/7 | 1704.0 ms | $0.005889 | $0.000841 |
| Native + repair eligible | 7/7 | 1353.0 ms | $0.005848 | $0.000835 |
| Two stage | 7/7 | 5016.2 ms | $0.018363 | $0.002623 |

No repair was triggered naturally, so repair rows measure eligibility overhead, not recovery.
