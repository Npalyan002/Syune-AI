# Phase 21 benchmark delta

Canonical evidence:

- PRE: `docs/evals/phase21/pre/p18-b3_current_syune-546c03e3-e472-47b3-bf3d-6995c0bdef13.json`
- POST: `docs/evals/phase21/post/p18-b3_current_syune-dbceb68a-518e-4a3e-9a77-d98aab43d496.json`

| Metric | PRE | POST | Delta |
|---|---:|---:|---:|
| Task success | 86.67% | 100% | +13.33 pp |
| Recall / authorized useful recall | 92.31% | 100% | +7.69 pp |
| Precision | 44.44% | 61.90% | +17.46 pp |
| MRR | 0.6722 | 0.7278 | +0.0556 |
| Abstention | 0% | 100% | +100 pp |
| False-memory selections | 1 | 0 | -1 |
| Mean context | 1.8000 | 1.4000 | -0.4000 |
| Temporal | 100% | 100% | 0 pp |
| Contradiction | 100% | 100% | 0 pp |
| Permission violations | 0 | 0 | 0 |
| Cross-agent leakage | 0 | 0 | 0 |
| P50 | 0.1639 ms | 0.2490 ms | +0.0851 ms |
| P95 | 0.6754 ms | 0.6302 ms | -0.0452 ms |
| P99 | 0.6754 ms | 0.6302 ms | -0.0452 ms |

Provenance accuracy is 86.67% because the harness counts correct empty abstention and permission results as lacking provenance; no selected item lost provenance.
