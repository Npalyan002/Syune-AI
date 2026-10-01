# SYUNE competitive capability gap — Phase 17

Research date: 2026-09-25. SYUNE judgments use repository implementation and executable evidence only. External entries below are narrowly scoped official documentation claims, not independently tested capabilities, measured superiority, enterprise certification or promises about every edition. No external product was installed or benchmarked.

Documentation is changing: the Mem0 open-source graph URL redirects to a Platform page, and old Letta tutorials redirect to its home page. Therefore the comparison explicitly names editions/paths and avoids treating older snippets as current universal behavior. EXTERNAL_VALIDATION_REQUIRED (EVR) means this audit has not established the capability; it does not mean the competitor lacks it.

## Verified documentation observations

- Mem0 **Platform** documents native entity connections and ranking combining vector, BM25 and entity-derived contributions. The page distinguishes graph entities from user/agent/app/run scoping IDs and states that its native graph does not assign typed labelled relations. These are documentation claims; no ranking/latency/security result was reproduced. [Mem0 Platform Graph Memory](https://docs.mem0.ai/platform/features/graph-memory).
- Zep v3 documents facts as time-stamped edge claims, with created_at, valid_at, invalid_at and expired_at, and updating/invalidation as new data arrives. It explicitly cautions that derived time bounds do not establish factual truth. [Zep Facts](https://help.getzep.com/v3/facts).
- Zep's Graphiti documentation advertises semantic, keyword and graph retrieval. This is Graphiti documentation, not proof of parity with the commercial Zep edition. The commercial search page could not be fetched successfully, so exact commercial fusion/reranking semantics require validation. [Graphiti introduction](https://help.getzep.com/graphiti/getting-started/welcome).
- Letta documents persistent core memory blocks and shared memory in its **v1 SDK** documentation. Its archive API documents passage insertion with embeddings for vector storage. Treat new Agent SDK and legacy v1 behavior separately in a benchmark. [Core memory](https://docs.letta.com/v1-sdk/memory/memory-blocks), [shared memory](https://docs.letta.com/v1-sdk/memory/shared-memory), [archive insertion API](https://docs.letta.com/api/typescript/resources/archives/subresources/passages/methods/create).
- Letta now recommends organization-owned Git-backed shared memory repositories for cloud-hosted agents; agents commit/push and other agents pull changes. Its legacy shared-block page recommends migration. This is shared state, not proof of independently verified cross-agent learning. [Current shared repositories](https://docs.letta.com/concepts/shared-memory).
- As one example of modern frontier-model infrastructure, Anthropic documents external memory/context management for long-running agent workflows and MCP integration. This establishes a relevant baseline class; it does not establish a complete temporal, permissioned organizational knowledge system. [Agent workflow guidance](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prompt-templates-and-variables), [MCP](https://docs.anthropic.com/en/docs/agents-and-tools/mcp).

No vendor benchmark uplift, exact pricing, context-window number, throughput figure or product ranking is adopted here. Sources describe capability availability, not effectiveness.

## Capability comparison

D = documented on the cited official page; EVR = EXTERNAL_VALIDATION_REQUIRED. Basic RAG and long-context columns define proposed experimental arms, not universal claims about all implementations.

| Capability | SYUNE after Phase 16 | Mem0 Platform | Zep v3 / Graphiti distinction | Letta v1/archive and current cloud repositories | Modern frontier-agent infrastructure | Basic RAG benchmark arm | Long-context LLM arm |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Persistent state | Local SQLite entities/history/overlay | Memory records D | Time-stamped graph facts D | Persistent blocks/archive D; cloud Git repositories D | External memory integration D; chosen implementation EVR | Persist corpus/index | Resupply saved transcript/corpus; separate host persistence |
| Semantic + lexical retrieval | No semantic/BM25; token matching + supplied graph | Vector/BM25/entity ranking D | Graphiti hybrid D; exact commercial behavior EVR | Vector archive D; hybrid details EVR | Tool-dependent; EVR | Specify vector or BM25 baseline and report variant | No external retrieval in this arm |
| Temporal knowledge | Timestamps/revisions, no validity enforcement | EVR | Fact validity/invalidation D | EVR | EVR | Timestamp metadata only unless explicitly added | Dates in prompt; no external truth ledger |
| Provenance | Locators/version/process IDs; incomplete enforcement | EVR for equivalent end-to-end guarantees | Fact/episode relationship D; full guarantee EVR | Passage metadata D; full lineage EVR | Host/tool dependent; EVR | Source/chunk IDs | Explicit source labels supplied in context |
| Entity/graph capability | Manual generic associations; no entity resolution | Entity extraction/connections D | Facts on relationships D | Equivalent entity graph EVR | Tool-dependent; EVR | None in basic arm | Model reasoning over supplied text |
| Working/core context | Transient bounded IDs | EVR | Context temporal ranges D | Core blocks D | Context management D | Retrieved top-k | Full allowed context |
| Controlled cross-agent transfer | MISSING; shared store only | Scope IDs D; validated learning EVR | Policy/transfer guarantees EVR | Legacy shared blocks / current cloud Git repositories D; verified learning EVR | Host-dependent; EVR | Shared index only if explicitly configured | No transfer protocol in arm |
| Verified experiential learning | Explicit score overlay, no evidence-to-generalization | EVR | EVR | EVR | EVR | None by baseline design | In-context examples only |
| Compression | No abstraction pipeline | EVR | EVR | EVR for equivalent traceable abstraction | Context management D; evidence-preserving guarantees EVR | None unless separate variant | Optional compaction must be separate variant |
| Cognitive ACL/purpose controls | MISSING | Scoping is not established purpose control; EVR | Exact policy semantics EVR | Attachment is not established purpose control; EVR | EVR | Explicit host ACL extension, separately measured | Host controls supplied input |
| Model portability | Data independent, behavior UNKNOWN | EVR | EVR | Model configuration exists in docs; state/behavior swap EVR | Provider/harness-specific; EVR | Same corpus/index, swap answer model | Same supplied text, swap model |
| Scale/cost/value | Selective 100K local historical fixture; no comparative task win | EVR | EVR | EVR | Workload/model selection required | MEASURE in Phase 18 | MEASURE in Phase 18 |

## Strategic interpretation

Industry parity requirements inferred from the documented feature set are persistent state, useful retrieval beyond exact token overlap, source-aware updates, temporal handling where facts change, controllable state sharing, and usable integration. This is an architectural inference, not a market census.

Possible SYUNE strengths: clear observation-versus-truth distinction, explicit provenance-bearing immutable records, deterministic explainable structural scoring, auditable reversible overlay, and sandbox approval/recovery mechanics. None currently demonstrates an advantage over the cited products.

Likely weaknesses against the documented baseline: no semantic/BM25 retrieval, no automatic entity extraction/linking, no operational fact validity, no persistent agent working state, no per-principal memory authorization, no memory deletion lifecycle, and no verified cross-agent learning. “Council” and a larger cognitive taxonomy do not compensate for these gaps.

The differentiation opportunity is evidence-validated reusable learning and permissioned transfer with demonstrable downstream task uplift. Competitor equivalent capabilities remain EVR; do not claim this opportunity is unique.

## Benchmark requirements

Use frozen product editions/API versions rather than brand names. Archive input/configuration/output provenance, dated documentation references, model/embedding version, retrieval settings and supported/unsupported cells. Do not use vendor-reported scores as measurements.

Compare answer/task success and groundedness at equal corpus, answer-model and context/cost budgets. Include paraphrases, changing facts, conflicting sources, source withdrawal, dense relations, poisoned text, multi-agent permission boundaries, held-out experiences and long-running state accumulation. Record ingest cost separately from warm query cost; include cold initialization and model-switch results. Rank neither products nor architectures until those runs exist.

All competitive latency, accuracy, retention, privacy enforcement and monetary comparisons remain UNMEASURED / EXTERNAL_VALIDATION_REQUIRED. Phase 18 prerequisites are listed in the main audit; no external service calls involving repository data were performed.

