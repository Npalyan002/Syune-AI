# Frozen Lean v1 absolute performance gate

Frozen before final measurement on 2026-09-29. Dataset: 100,000 deterministic local
records, warm in-process index, 10 measured repetitions after two warmups.

Release ceilings:

- selective retrieval p95 <= 100 ms
- broad retrieval p95 <= 1,500 ms
- selective context assembly p95 <= 150 ms

These ceilings preserve the already-demonstrated interactive selective path, put a
finite production bound around the known local-linear broad worst case, and permit
provenance construction plus durable audit without using an intentionally simpler
RAG percentage as a proxy for product latency. Authorization, temporal eligibility,
lifecycle filtering, provenance, and audit may not be disabled to pass.
