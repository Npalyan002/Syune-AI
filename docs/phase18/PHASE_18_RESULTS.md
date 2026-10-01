# Phase 18 results

Canonical deterministic smoke runs use dataset `syune-competitive-baseline@1.0.0`, seed 1801, generator 1.0.0, and 15 cases.

| Baseline | Status | Passed | Task success | Recall | Precision | MRR | P95 retrieval | False memories | Permission violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B0 MODEL_ONLY | NOT_CONFIGURED | 0/15 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| B1 LONG_CONTEXT | NOT_CONFIGURED | 0/15 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| B2 BASIC_RAG | READY | 6/15 | 0.400 | 0.846 | 0.344 | 0.547 | 0.071 ms | 7 | 2 |
| B3 CURRENT_SYUNE | READY | 8/15 | 0.533 | 1.000 | 0.382 | 0.628 | 0.411 ms | 7 | 2 |

B3’s measured strengths are associative and two-hop retrieval plus complete relevant-record recall on this tiny deterministic fixture. Its measured weaknesses match the Phase 17 architecture: stale/future facts, contradictions, unauthorized/cross-agent records, and unverified alternatives remain retrievable. B3 also returns more context and has higher local p95 latency than B2. These figures are harness validation, not enterprise performance claims.

B0/B1 were not executed because no model/provider credentials were configured. Their raw files contain unsupported errors for every case; the table uses n/a because zero execution success is not model-quality evidence. B4–B6 were not configured and were not run.

Canonical raw evidence:

- `p18-b0_model_only-8885eb18-e9b2-48db-b416-a9e0ccdc2c83.json`
- `p18-b1_long_context-65a1ee65-5eed-4232-b3b9-f7000fdf3d05.json`
- `p18-b2_basic_rag-47c0a54f-e628-42be-a60f-744125d7ebcb.json`
- `p18-b3_current_syune-d3976b97-c88e-4a8d-8262-95a8ae218ea2.json`

The two earlier B2/B3 raw files are preserved as preliminary evaluator-development evidence and are superseded by the canonical IDs above; they were not overwritten.
