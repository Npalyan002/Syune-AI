# Phase 20 benchmark delta

Canonical evidence:

- PRE: `docs/evals/phase20/pre/p18-b3_current_syune-2cc0c53e-bad3-46f6-ae73-b75a9feca82a.json`
- POST: `docs/evals/phase20/post/p18-b3_current_syune-e35e05a6-b616-46a3-ad2b-745a7f9db872.json`

| Metric | PRE | POST | Delta |
|---|---:|---:|---:|
| Task success | 73.33% | 86.67% | +13.34 pp |
| Recall / authorized recall | 92.31% | 92.31% | 0 pp |
| Precision | 41.38% | 44.44% | +3.06 pp |
| Permission accuracy | 0% | 100% | +100 pp |
| Permission violations | 2 | 0 | -2 |
| Cross-agent leakage | 1 | 0 | -1 |
| False-memory selections | 3 | 1 | -2 |
| Temporal accuracy | 100% | 100% | 0 pp |
| Contradiction accuracy | 100% | 100% | 0 pp |
| P50 | 0.1840 ms | 0.1945 ms | +0.0105 ms |
| P95 | 0.6293 ms | 0.7755 ms | +0.1462 ms |
| P99 | 0.6293 ms | 0.7755 ms | +0.1462 ms |
| Mean context records | 1.9333 | 1.8000 | -0.1333 |
