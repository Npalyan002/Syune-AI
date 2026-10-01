# Cross-agent ablation

| Condition | Task success | Cold-agent success | Repeated errors | Contamination |
| --- | ---: | ---: | ---: | ---: |
| ISOLATED | 50% | 50% | 50% | 0% |
| RAW_SHARED | 70% | 70% | not used | 20% |
| LOCAL_VERIFIED | 70% | 50% | 30% | 0% |
| CROSS_AGENT_VERIFIED | 90% | 90% | 10% | 0% |

`RAW_SHARED` is benchmark-only and intentionally naïve; production never exposes that path. Controlled cross-agent learning outperforms local-only learning when useful cases are distributed among agents. Exact machine-readable results are in `docs/evals/phase25/POST_PHASE_25.json`.
