# Benchmark baselines

| ID | Baseline | State | Current implementation |
| --- | --- | --- | --- |
| B0 | MODEL_ONLY | NOT_CONFIGURED | Provider-neutral slot; requires an explicitly configured model adapter. |
| B1 | LONG_CONTEXT | NOT_CONFIGURED | Provider-neutral slot; requires an explicitly configured model and context adapter. |
| B2 | BASIC_RAG | READY | Independent benchmark-only token-overlap retrieval; no graph, policy, time, or learning. |
| B3 | CURRENT_SYUNE | READY | Actual current SYUNE memory/index/retrieval path. |
| B4 | MEM0 | NOT_CONFIGURED | External adapter slot; no fake implementation. |
| B5 | ZEP | NOT_CONFIGURED | External adapter slot; no fake implementation. |
| B6 | LETTA | NOT_CONFIGURED | External adapter slot; no fake implementation. |

B0/B1 raw runs say `NOT_EXECUTED — CREDENTIALS/PROVIDER UNAVAILABLE`. They keep all cases in the denominator and record one `unsupported_capability` error per case. Their zero task success is execution accounting, not evidence about model quality.

B2 is intentionally simple and independent. It is not presented as an industry-standard optimized RAG implementation. B3 is neither tuned nor patched for the fixture set. A later external adapter should preserve the same neutral records, query, relevant IDs, forbidden IDs, state policy, and evaluator.
