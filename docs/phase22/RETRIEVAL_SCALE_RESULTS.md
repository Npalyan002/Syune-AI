# Retrieval scale results

Evidence: `docs/evals/phase22/post/POST_PHASE_22_SCALE.json`; generator `phase22-scale-v1`, seed 2201; Windows 11, Python 3.12.14, 64 logical CPUs, AMD64 Family 23 Model 49. These runs measure the lexical derived-index path, not Qdrant ANN or embeddings.

| Scale | Status | Build | Write p95 | Query p50/p95/p99 | Index bytes | Peak memory | Recall | Precision |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 10K | EXECUTED | 418.06 ms | 0.0244 ms | 4.60 / 5.50 / 6.01 ms | 440,110 | 7,902,484 | 100% | 20% |
| 100K | EXECUTED | 5,075.94 ms | 0.0381 ms | 78.16 / 96.29 / 105.15 ms | 4,630,036 | 72,395,216 | 100% | 20% |
| 1M | NOT_EXECUTED | — | — | — | — | — | — | — |
| 10M | NOT_EXECUTED | — | — | — | — | — | — | — |
| 100M | NOT_EXECUTED | — | — | — | — | — | — | — |

Broad common-term postings and full candidate sorting cause approximately O(N)-like query growth and poor hard-negative precision. Initial local budgets: DEVELOPMENT ≤10K, p95 10 ms; STANDARD ≤100K, p95 125 ms; LARGE/STRESS unbudgeted pending ANN runs. These are observations, not enterprise SLAs.

Other O(N)-like paths: repository snapshots in sync and recall, truth pair comparison, supersession-set construction, health counting, and full rebuild recovery. Association traversal is bounded.
