# Phase 22.1 benchmark delta

Phase 22 raw results are immutable. V2 changes the single-answer workload from precision@5 to precision@1 and records candidate bounds and query classes.

| Metric | Phase 22 10K | V2 10K | Phase 22 100K | V2 100K |
|---|---:|---:|---:|---:|
| Recall | 100% | 100% | 100% | 100% |
| Precision metric | 20% @5 | 100% @1 | 20% @5 | 100% @1 |
| p95 | 5.4993 ms | 0.0969 ms | 96.2888 ms | 0.1015 ms |

The old 10K→100K p95 growth was 17.51×. V2 growth is 1.047×. This comparison applies to the deterministic lexical scale harness, not live Qdrant.
