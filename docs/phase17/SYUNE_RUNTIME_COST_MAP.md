# SYUNE runtime cost map — Phase 17

Evidence references resolve in [architecture](SYUNE_CURRENT_ARCHITECTURE.md). This report separates static operation counts from historical measurements and missing measurements. No extrapolated latency is presented as benchmark data. Phase 17 test durations are not service benchmarks.

## Cost by component

N = total memory entities; E = edges; L = overlay records; P = posting-list union size; T = text tokenization work; d(v) = full degree of visited node v; C = scored candidates; M = attempted Council members; B = ingestion blocks; S = selected learning signals.

| Component/path | LLM / network calls and tokens | DB / retrieval operations | Serialization / disk / CPU work | Latency and failure surface |
| --- | --- | --- | --- | --- |
| Product open | 0 model/network calls; 0 inference tokens | Four SQLite opens, schema checks, full entity SELECT/index rebuild | O(N + total indexed text) decode/token index; metadata file replacement | Exact current-host cost UNMEASURED; missing/incompatible DB or metadata write fails all operations |
| CLI MCP serve startup | 0 / 0 / 0 | Product open/close followed by gateway two-store open and another rebuild | Two full index constructions plus metadata write | Avoidable startup work; no per-request model cost |
| Study fresh text | 0 / 0 / 0 | Registry lookups/revision/transitions/checkpoints; memory exists/put_many per block; materialization ID checks; SDK/MCP index sync | Read/hash entire bounded source; parse blocks; observation + trace per block; multiple cross-store commits; sync O(N) decode | Cost depends on B, source size and fsync; no atomic transaction across registry/memory |
| Study duplicate | 0 / 0 / 0 | Hash lookup, alias update, materialization checks; public index sync still scans | Whole source reread/hash; source-history traversal/checkpoint work | Not a zero-I/O no-op; large files and repeated scans |
| Perception with injected provider | One provider.perceive callback per perceive invocation when configured; actual model/network subcalls and tokens UNMEASURED | Persist run/segments/observations | Header inspection, provider output size checks; some repeated size sums | Provider deadline checked after callback returns; hung callback unbounded; product config injects no provider |
| Index lexical | 0 / 0 / 0 | In-memory posting union, no vector service | Re-tokenizes candidate text; O(T + P log P), then seed limit; source_ids O(N) scan + sort | Common-term queries degrade; max_lexical_seeds does not bound candidate-generation work |
| Recall graph/scoring | 0 / 0 / 0 | Seed existence reads; per visited node one full adjacency query plus endpoint existence reads; candidate entity reads; optional materialization; overlay reads | Sort each full adjacency before fanout, BFS/path copies, score/sort candidates | SQLite adjacency indexes help but do not cap d(v); selected max_edges is not DB read cap |
| Learned recall view | 0 / 0 / 0 | Association overlay state lookup per considered propagated edge; two overlay lookups per scored candidate for salience/utility | Repeated rows read with no request-level batch snapshot | Read amplification and possible mixed-time view; exact call totals workload-dependent |
| Cognitive Core | 0 / 0 / 0 | One recall, second conditional recall; attention and inference memory/adjacency reads | Bounded working set, graph paths, deterministic templates | Initial inference relation sweep reads full degrees; time-budget check is late; benefit UNMEASURED |
| Profiles | 0 / 0 / 0 | Dictionary lookup; no persistence | Small policy merge/fingerprint/asdict work | Negligible in historical measurements, but no independent product value established |
| Council | 0 / 0 / 0 | Baseline + after-each-member full snapshots; each snapshot N adjacency queries plus full entity read and overlay snapshot; M cognition runs | Roughly O((M+1)(N+E+index bytes+L)) traversal/serialization plus sorting and member work | Global budget checked between members, cannot preempt initial snapshot; high cost without proven accuracy gain |
| Learning record | 0 / 0 / 0 | Target validation, duplicate lookup, signal/target/audit inserts | Signal payload duplicated into audit; append latency retained in list | Explicit only; durable transaction; target/source authenticity not verified |
| Learning consolidation | 0 / 0 / 0 | Pending SELECT/sort; full overlay snapshot; source retraction enumerates all memory; proposal/batch/audit writes | O(L + proposals); each proposal stores before/after state; repeated-target write amplification | SQL transaction atomic, precomputed proposals not a proven concurrent merge strategy |
| Learning rollback | 0 / 0 / 0 | Load proposals, later-update checks, overlay restore/status/audit writes | Work proportional to batch target/proposal history | Blocks overlapping later applied updates; no knowledge dependency retraction |
| L2 planning | 0 / 0 / 0 | No retrieval or DB in default path | Keyword classification; three-step template; validation/hash; in-memory retained plans | Static BudgetEstimate is not actual measured consumption |
| L3 execution | No LLM/network in provided sandbox adapter; external adapter internals UNMEASURED | Durable begin/finish/receipt writes; approval/gate/retry checks | Local file read/write/read-back; sandbox storage rglob; in-memory preimage; repeated receipt serialization | Filesystem effect and SQLite receipt separate transactions; deadlines between actions; restart rollback limited |
| SDK/MCP mapping | 0 model/network calls; MCP stdio is local IPC | SDK calls product services; MCP tools call gateway services | Full dataclass-to-JSON conversion; MCP metric list append per call | Synchronous work inside async tool handlers; error mapping differs; unbounded metrics retention |
| Health | 0 / 0 / 0 | Runtime health mainly flags/profile count, no storage liveness query | Metadata/version lookup in public wrappers | Cheap but may be false HEALTHY (P05); not equivalent to offline integrity audit |
| Evals/offline audit | 0 in current fixtures | Full entities, per-entity edges, registry/overlay/receipt enumeration | JSON reports, reference checks, subprocesses in test harness | Offline diagnostic cost; not wired to live health |

Disk I/O byte totals, exact database call counts per general request, context token savings, production latency and provider costs are UNMEASURED unless specified below. Absence of internal model calls does not mean the external host's model is free; host inference is outside existing SYUNE benchmarks.

## Historical measured evidence

Source: docs/evals/phase14_scale_v1.json and scripts/benchmark_phase14.py:scale. Windows 11 / CPython 3.12.10. “Entities” in the JSON is requested observation count; fixture also inserts one Source and a single association. Query unique0 matches one observation, with a connected second observation; most distractors have unique tokens. This is selective retrieval, not representative dense or frequent-term search. Warm recall has 20 samples; Council has three samples and only runs at <=10K.

| Corpus size | Historical index build ms | Warm recall p50 ms | Restart rebuild ms | Council p50 ms | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| 10K | 440.8722 | 0.62525 | 525.8467 | 2998.1799 | Full snapshots overwhelm bounded member work |
| 100K | 5980.8566 | 0.76675 | 6368.2379 | UNMEASURED | Selective warm recall remains small; cold index cost grows |
| 1M | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | Full resident index/entity decode is an algorithmic risk |
| 10M | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | Durable incremental indexing, partitioning/isolation likely required; selection must follow benchmark |
| 100M | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | No supported architecture or evidence for service-level scale |

At 100K the historical artifact records 109,379,584 DB bytes and 180,215,808 process RSS bytes. RSS includes the process and is not isolated index heap usage. Do not multiply these values to claim 1M–100M capacity.

Source: docs/PHASE_16_VALIDATION.md and scripts/benchmark_phase16.py. Historical median ms for direct / SDK / in-process MCP respectively: recall 1.4862 / 1.8038 / 6.3640; cognition 5.5593 / 5.8554 / 13.5214; planning 0.4362 / 1.1309 / 2.4124. Direct/SDK 20 samples; MCP 10. This excludes stdio startup and does not test learned-state parity (P01 disproves that broader claim).

Source: docs/PHASE_14_VALIDATION.md and docs/evals/phase14_subsystems_v1.json. Historical small-pipeline execution gate p50 0.0129 ms, capability 5.0243 ms, execution overhead 404.7010 ms, verification 4.2583 ms. Overhead already includes verification; do not add it again. Metadata persistence dominates the local sandbox case; enterprise adapters remain unmeasured.

The historical soak ran 601.878 seconds, 123 cycles, no recorded errors, using a newly created TemporaryDirectory/state per cycle. This proves short-lived pipeline churn within a fixture, not lifetime memory growth, append-only learning growth, resident MCP metrics growth or multi-tenant concurrency.

## Scale risks and highest-cost paths

1. Whole-memory index rebuild at each runtime open; duplicate work on MCP startup.
2. Full index sync after Study, including duplicate sources.
3. Frequent-token posting union, retokenization and global sort before seed cap.
4. High-degree adjacency read/sort before fanout cap; per-edge endpoint queries.
5. Council snapshot full graph serialization repeated M+1 times (P08 observes three full enumerations for two members).
6. Whole-overlay consolidation snapshot and full-memory source-retraction scan.
7. Repeated SQL overlay lookups during graph scoring.
8. Per-block registry and memory commits; separate transaction domains amplify write/recovery work.
9. MemoryTrace duplicates provenance alongside Observation; learning audit repeats signal payload and proposals persist before/after states. These copies serve audit purposes but their retention cost is not measured.
10. Sync provider/file/DB work and cooperative deadlines; long calls block the host/tool handler.
11. Volatile plans, MCP per-tool metric lists and learning latency lists accumulate for process lifetime.

The largest demonstrated unnecessary complexity is Council snapshotting on an explicitly invoked optional path. The largest universal opening cost is eager full-store initialization/index rebuilding, not Council execution. There is no evidence that every request invokes all cognitive modules.

Phase 18 should measure these paths under frequent terms, dense hubs, revisions, repeated feedback, cold/warm instances, interrupted writes and growing-state soak before choosing databases or adding infrastructure.

