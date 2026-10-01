# Frozen Lean v1 quality comparison

Frozen before execution on 2026-09-29. STRONG_RAG and LEAN_SYUNE use the same
synthetic non-sensitive records, local deterministic embedding/index, queries, top-8,
and context relevance definition. Lean adds authorization, temporal, lifecycle,
provenance and audit behavior; no learning, cognition or query-time synthesis is used.

Primary paired endpoint is correct authorized useful recall plus correct abstention.
Noninferiority passes when the lower two-sided 95% paired bootstrap confidence bound
for `LEAN_SYUNE - STRONG_RAG` is at least -0.05. Precision and context precision are
reported separately. Governance exclusions must be exact and leakage must be zero.
