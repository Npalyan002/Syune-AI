# Phase 29 model execution inventory

| Location | Current responsibility | Classification | Phase 29 disposition |
|---|---|---|---|
| `src/syune/model_gateway/` | Production text-generation execution | KEEP | Canonical production boundary |
| `benchmarks/phase26.py` | OpenAI Responses experiment transport, parsing, usage and cost | BENCHMARK_ONLY | Frozen evidence; do not import into production |
| `benchmarks/phase27.py` | OpenAI Responses experiment transport and accounting | BENCHMARK_ONLY | Frozen evidence |
| `benchmarks/phase28_provider.py` | Phase 28 provider bridge and JSONL ledger | BENCHMARK_ONLY | Design evidence superseded by gateway |
| `benchmarks/phase28r1_execution.py` | Phase 28R.1 execution ledger | BENCHMARK_ONLY | Frozen runner |
| `benchmarks/phase28r2_execution.py` | Raw-first Phase 28R.2 runner | BENCHMARK_ONLY | Source evidence for Phase 29 failure semantics |
| `src/syune/retrieval_integrations.py` | Embedding and reranking HTTP integrations | KEEP | Different workload; future migration may share transport primitives |
| `src/syune/perception/providers.py` | Multimodal perception provider protocols | KEEP | Different typed boundary; no text-generation execution |
| `src/syune/perception/router.py` | Optional perception-provider routing | KEEP | Does not parse generative structured output |
| `src/syune/executive/` | Approved action retry and idempotency | KEEP | Side-effect runtime remains downstream of the gateway |

Production cognition, council, planner, learning, SDK, API and MCP code contained no direct
text-generation provider transport at the Phase 29 audit point. They must depend on
`ModelGateway.execute(ModelExecutionRequest)` when generative execution is introduced.

Provider status:

- OpenAI Responses API: **IMPLEMENTED**, not live-validated in Phase 29 without credentials.
- Local/OpenAI-compatible Responses API: **IMPLEMENTED**, not live-validated.
- Anthropic and Gemini: **CONTRACT_ONLY** through `ContractOnlyAdapter`; no live claims.

No Phase 28 treatment data was interpreted as task-performance evidence.
