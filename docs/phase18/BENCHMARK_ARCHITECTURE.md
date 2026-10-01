# Benchmark architecture

The benchmark package is deliberately outside `src/syune`, so evaluation code cannot become a product dependency. `model.py` defines baseline-neutral records, edges, cases, datasets, responses, and the adapter protocol. `datasets.py` generates deterministic synthetic workloads. `adapters.py` contains independent baseline integrations. `runner.py` owns isolation, telemetry, metric aggregation, failure accounting, and raw-result validation. `reporting.py` owns deltas and regression gates. `cli.py` is the stable command surface.

Every adapter implements `prepare`, `reset`, `ingest`, `query`, `execute_task`, `export_state_metrics`, and `cleanup`. Every case declares `FRESH`, `PERSISTENT`, or `SHARED`; current fixtures are `FRESH`. The runner resets before each fresh case, and adapters use separate state objects, preventing B0–B3 leakage.

B3 uses the real current `InMemoryReferenceRepository`, `InvertedSeedIndex`, `RetrievalService`, `RecallCue`, and `RecallRequest`. The adapter only translates neutral fixture records to current SYUNE memory entities and maps returned entity IDs back to fixture IDs. It does not add temporal, authorization, learning, or compression behavior.

CI tiers are `UNIT`, `BENCHMARK_SMOKE`, `BENCHMARK_STANDARD`, `BENCHMARK_EXTERNAL`, and `BENCHMARK_STRESS`. Only deterministic harness tests and smoke execution belong in normal CI. Paid/provider and high-scale runs are explicit.
