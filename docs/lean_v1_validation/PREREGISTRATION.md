# SYUNE Lean v1 preregistration

Frozen before release-gate treatment measurements on 2026-09-29.

## Compared systems

- STRONG_RAG: the same frozen records, deterministic embeddings, local vector index, lexical/entity/exact routes, top-k and context budget, without SYUNE governance filtering.
- LEAN_SYUNE: the same retrieval stack plus authorization, temporal/version and lifecycle filtering, provenance projection, bounded context and audit.

No learning, cognition, Council, Planner, query-time synthesis, or post-result optimization is permitted.

## Quality margins

Noninferiority requires LEAN_SYUNE minus STRONG_RAG to be at least -0.05 absolute for retrieval recall, retrieval precision, context precision, task success and correct abstention. The governance strata additionally require 100% authorization and temporal/version accuracy, 100% required-provenance completeness, and zero unauthorized/future leakage. A governance failure cannot be offset by average quality.

## Latency and storage limits

- Governed retrieval/context overhead must be both <=25 ms absolute p95 and <=30% relative p95 versus STRONG_RAG on the same host, excluding provider latency.
- Selective retrieval p95: <=100 ms at 1K, <=250 ms at 10K, <=750 ms at 100K.
- Broad retrieval p95: <=250 ms at 1K, <=750 ms at 10K, <=2,500 ms at 100K.
- Empty/default startup p95 <=2,000 ms with zero background jobs.
- Durable core storage <=8 KiB per record at 100K, excluding optional gateway evidence; growth must be approximately linear.

## Release policy

Every required release gate must pass. Missing product-level audit reconstruction, missing provenance fields, unavailable deployment modes, failed clean installation, or an unmeasured mandatory 100K gate produces `LEAN_V1_NEEDS_FIXES`; it is never silently treated as a pass.
