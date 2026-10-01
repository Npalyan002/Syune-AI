# Benchmark results

`benchmarks/lean_product.py` measures remember, recall, context, and authorized context with p50/p95/p99 over a local deterministic corpus. ModelGateway correctness is covered separately with contract adapters so provider/network latency is not mislabeled as SYUNE overhead.

`STRONG_RAG` is defined as the same retrieval payload without authorization, lifecycle filtering, provenance projection, temporal filtering, or audit. `LEAN_SYUNE` adds those controls. The benchmark reports end-to-end lean latency; governance cost must be measured as a paired delta on the deployment corpus. No unsupported superiority claim is made.

Validation run (25 iterations, Windows local SQLite, growing 26-record corpus): remember 188.601/231.409/290.785 ms; recall 22.320/23.817/29.484 ms; context 22.345/25.520/26.554 ms; authorized context 8.582/9.176/9.336 ms (p50/p95/p99). These are smoke-scale measurements, not capacity claims; the faster authorized result reflects this corpus/filter path and is not claimed as a general optimization.
