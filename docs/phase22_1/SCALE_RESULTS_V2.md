# Scale results V2

Evidence: `docs/evals/phase22_1/post/POST_REMEDIATION_SCALE_V2.json`. Version `phase22.1-scale-v2`; generator `phase22-scale-v1`. Precision semantics changed to precision@1 and prior raw evidence was preserved.

| Scale | Recall | Precision@1 | p50 | p95 | p99 | Candidate max |
|---:|---:|---:|---:|---:|---:|---:|
| 10K | 100% | 100% | 0.0869 ms | 0.0969 ms | 0.1029 ms | 256 |
| 100K | 100% | 100% | 0.0871 ms | 0.1015 ms | 0.1061 ms | 256 |
| 1M | NOT_EXECUTED | — | — | — | — | — |

Dataset growth was 10×; aggregate p95 growth was 1.047×. Selective p95 grew from 0.0087 to 0.0093 ms (1.069×); broad p95 fell from 0.0950 to 0.0935 ms. A 1M run was unnecessary because 100K already demonstrated the bounded curve and live ANN remains a separate validation item.

Query classes were recorded separately for EXACT, LEXICAL_SELECTIVE, LEXICAL_BROAD, ENTITY, ASSOCIATIVE, TEMPORAL, and MIXED.
