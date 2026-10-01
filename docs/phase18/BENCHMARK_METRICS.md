# Benchmark metrics

Task success requires all relevant evidence and no forbidden evidence. Abstention requires an empty result. Failures, exceptions, invalid outputs, retrieval failures, authorization failures, provider failures, timeouts, schema failures, and unsupported capabilities stay in the case count.

Retrieval metrics are recall, precision, and mean reciprocal rank. Family metrics include temporal, contradiction, provenance, abstention, and permission accuracy. The result also records false-memory count, permission-violation count, and mean returned context records. These dimensions remain separate; there is no composite score.

Telemetry records retrieval, generation, and end-to-end latency where measurable, plus p50/p95/p99, sample count, population variance, and a 95% confidence-interval half-width. Input/output/total token fields are nullable. B2 reports a deterministic token proxy over its inspected records and query; B3 reports query tokens because current retrieval exposes no model context-token accounting. This difference is explicit and must not be read as a model-token comparison.

Cost uses exactly `MEASURED_COST`, `ESTIMATED_COST`, or `UNKNOWN_COST`. Local smoke runs are `UNKNOWN_COST`; no estimate is presented as billing. Storage captures adapter state before and after execution.
