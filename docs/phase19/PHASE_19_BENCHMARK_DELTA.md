# Phase 19 benchmark delta

Canonical evidence:

- PRE: `docs/evals/phase19/pre/p18-b3_current_syune-562e61db-1ba0-4099-850e-4d1efcfcfa0e.json`
- POST: `docs/evals/phase19/post/p18-b3_current_syune-3d9038d3-104b-4fa0-8ed8-3d756b9537e4.json`

| Metric | PRE | POST | Delta |
|---|---:|---:|---:|
| Task success | 53.33% | 73.33% | +20.00 pp |
| Recall | 100.00% | 92.31% | -7.69 pp |
| Precision | 38.24% | 41.38% | +3.14 pp |
| Temporal accuracy | 0% | 100% | +100 pp |
| Contradiction accuracy | 0% | 100% | +100 pp |
| Provenance accuracy | 100% | 100% | 0 pp |
| Abstention accuracy | 0% | 0% | 0 pp |
| False-memory selections | 7 | 3 | -4 |
| P50 | 0.1406 ms | 0.1972 ms | +0.0566 ms |
| P95 | 0.4140 ms | 0.8676 ms | +0.4536 ms |
| P99 | 0.4140 ms | 0.8676 ms | +0.4536 ms |
| Mean context records | 2.2667 | 1.9333 | -0.3334 |

The recall reduction is the expected removal of ineligible false memories; useful task success increased. Authorization failures remain Phase 20 work. Abstention remains an explicit residual risk.
