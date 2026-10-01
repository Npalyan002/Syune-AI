# Lifecycle growth evaluation

The deterministic synthetic replay contains 1,000 observations: 40% unique useful facts and 60% repeated evidence. This is synthetic evidence, not production traffic.

| Measure | Lifecycle off | Lifecycle on |
| --- | ---: | ---: |
| Canonical records | 1,001 | 1,001 |
| Active records | 1,001 | 413 |
| Archived records | 0 | 588 |
| Search index records | 1,000 | 412 |
| Returned hits | 8 | 8 |
| Context size | 8 | 8 |
| Retrieval P95 | 22.426 ms | 7.204 ms |

Active growth fell 58.74%. Ingestion/lifecycle maintenance cost was 56.457 ms total, or 0.0565 ms/interaction. Run `scripts/benchmark_phase23.py` to reproduce. The Phase 18 checkpoints remain compatible; only the 1,000 checkpoint was executed here.
