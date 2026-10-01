# Pre-remediation profile

The immutable Phase 22 scale result remains under `docs/evals/phase22/post`. At 10K, p50/p95/p99 were 4.5993/5.4993/6.0129 ms. At 100K they were 78.1589/96.2888/105.1489 ms.

An actual cProfile run of twenty 100K broad queries produced 7,979,741 calls and 5.098 seconds cumulative. `ScalePostingIndex.search` consumed 5.098 seconds; `sorted` consumed 2.448 seconds; candidate dictionary lookups executed 4,000,040 times. This confirmed candidate flooding and complete sorting as the principal measured benchmark hot path.
