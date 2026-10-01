# Phase 18 implementation

`PHASE_18_STATUS = PASS`

Phase 18 adds a permanent, production-isolated benchmark system under `benchmarks/`. It does not change code under `src/syune/`. The harness runs baseline-neutral cases through a provider-neutral adapter contract, records immutable raw JSON, compares quality and operating trade-offs, and evaluates configurable regression gates.

Implemented components:

- B0–B6 adapter registry; B2 and B3 execute locally, while unavailable providers return `NOT_CONFIGURED`.
- Fifteen benchmark families spanning recall, time, contradictions, provenance, association, multi-hop, updates, abstention, permission, cross-agent behavior, learning, compression, task success, context efficiency, and performance.
- Deterministic synthetic fixtures with dataset identity and content hashes.
- Repeated-run samples, latency variance and 95% confidence interval support.
- Longitudinal points at 10, 100, 1,000, and 10,000 interactions.
- Scale points at 10K, 100K, 1M, 10M, and 100M records with smoke, standard, heavy, and stress invocation tiers.
- Append-only raw evidence, canonical schema, comparison reports, and configurable regression policy.

Phase 19 may use the temporal, contradiction, permission, provenance, update, and lifecycle families without changing their externally observable expectations.
