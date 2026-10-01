# Complexity and cost map

Measured host results are stored in `docs/evals/phase25_5/PHASE_25_5_RESULTS.json`; they are not service-level promises. This run used 1,338,244 bytes, 22 counted setup/learning operations, zero LLM calls, and zero tokens.

| Capability | Value/cost classification | Evidence |
| --- | --- | --- |
| Ordinary authorized retrieval | HIGH VALUE / LOW COST | 0.33 ms p50, 0.47 ms p95 |
| Local verified maintenance | LOW INCREMENTAL VALUE / HIGH COST | 77.82 ms p50, 103.96 ms p95; tied RAG |
| Organizational maintenance | HIGH VALUE / HIGH COST | 35.05 ms p50, 61.00 ms p95; +12.5 points |
| Temporal/security/lifecycle gates | HIGH VALUE / LOW COST | preserve invariants; quality delta not isolated here |
| Council snapshots | LOW MEASURED PRODUCT VALUE / HIGH COST | prior 10K scaling near 3 seconds |

Maintenance remains off the ordinary decision path. Context averaged 0.75 applicable learned procedures per held-out task.
