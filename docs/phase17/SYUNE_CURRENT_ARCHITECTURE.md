# SYUNE current architecture — Phase 17

Audit date: 2026-09-25. Baseline commit: e2d9ea5f49d4eb138e37531ac1d9eae7016bc0ed. Package 0.1.0; public API, MCP contract and state schema 1. This is an implementation reconstruction, not a restatement of the blueprint.

## Actual product

SYUNE is a synchronous, local Python library/stdio MCP service for provenance-bearing source ingestion, persistent typed memory, lexical/structural recall, deterministic cognitive analysis, explicit retrieval-score adaptation, and proposal-only planning. A separately composed internal executive demonstrates approved local file effects. It is not yet a distributed cognitive fabric, a semantic memory service, or an autonomous learning agent.

No configured foundation model participates in shipped cognition, Council, or planning. No model inference bill is incurred on those paths. This makes current state structurally independent of a model but does not prove behavioral portability across models.

## Repository forensics

[Machine inventory](evidence/repository-inventory.json) records all 304 baseline tracked files, byte hashes and Python symbol locations (167 Python files; 101 files under src). All significant runtime families below were inspected; inventory/AST enumeration is not a claim that every line received manual review.

| Surface | Actual contents and role |
| --- | --- |
| src/syune | Single Python distribution: core, memory, Study, perception, retrieval, learning, cognition, Council, executive, product lifecycle, API, SDK, CLI, MCP, evals |
| contracts | Only common public result/error JSON schemas are executable-shaped contracts; most domain contracts are Python dataclasses/enums |
| config | README scaffolding; operational configuration lives in product/config.py and user TOML/environment |
| tests | Unit, contract, architecture, integration, Phase 14 failure/correctness/concurrency, Phase 15 product and Phase 16 interface tests |
| scripts | Architecture checker; synthetic subsystem/scale/soak benchmarks; installed-package checks; legacy shadow probe |
| docs | Phase 00–16 validation/design reports, ten ADRs, domain blueprints, product/host docs; docs/evals contains historical JSON results |
| Root SYUNE_PHASE_* | Phase input specifications/history, not runtime modules; overlap with docs is documentation duplication, not two engines |
| examples/host_integration | Public SDK host and MCP configuration; host selects operations explicitly |
| .venv, dist, .pytest_cache | Local dependency/build/test artifacts; not source authority. Existing .venv launcher is not usable on this audit host |
| .syune | Ignored prior local state/benchmark artifacts. Not treated as canonical product evidence or modified by the audit probes |
| events, telemetry, providers, governance, storage, domains directories | README placeholders. Real policy is in executive; real storage is inside memory/Study/learning/executive; real profiles are in cognition |
| Deprecated/experimental | No separately implemented legacy production engine found. In-memory repository and sandbox adapter are reference/test implementations. Brain-inspired semantics and profile labels are experimental value hypotheses |
| Unreachable/unwired | L3 and LearningService callable internally but not exposed by public v1. Provider protocols are injectable internally; product runtime supplies no provider. HostContext and public ExecutionRequest are data contracts without corresponding operational integration |

No AGENTS.md was found by repository file search. No subagents were used. Existing tracked working tree was clean.

## Evidence map

Paths below are relative to the repository root. Symbols make citations reproducible; their line numbers are also in the inventory. E references throughout the reports refer to this table.

| ID | Implementation / executable evidence | What it establishes |
| --- | --- | --- |
| E01 | src/syune/product/runtime.py: SyuneRuntime.open, health; product/state.py: DATABASES, initialize_state | Four-store product graph, full index rebuild, static health flags, metadata write |
| E02 | src/syune/sdk/client.py: Syune; api/model.py; api/serialization.py | Public call paths, modes, error wrapping, untyped result data, no principal |
| E03 | src/syune/gateway/mcp/server.py: open_gateway, create_syune_mcp_server; cli/app.py: run | Separate MCP graph, missing learning overlay, materialization callback, double startup graph |
| E04 | src/syune/memory/model.py; repository.py; sqlite_repository.py: put_many, iter_entities, associations_for | Typed entities/provenance; immutable inserts; JSON persistence; indexed edges; full enumeration |
| E05 | src/syune/study/service.py: study, materialization_status; encoder.py; parsers.py; registry.py | Hash/revision/checkpoint ingestion, observation/trace creation, no semantic extraction or associations |
| E06 | src/syune/perception/router.py: perceive; providers.py; inspect.py; tests/integration/test_multimodal_study.py | Metadata fallback, optional callback protocols, fake-provider semantic tests, cooperative timing |
| E07 | src/syune/retrieval/index.py: sync, lexical, source_ids; service.py: recall; model.py | Lexical union, bounded structural expansion, score features, no ACL/as-of filtering |
| E08 | src/syune/learning/service.py; policy.py; store.py; model.py | Explicit score adaptation, negative signals/retraction, transactional overlay, rollback, no verified generalization |
| E09 | src/syune/cognition/service.py; inference.py; metacognition.py; model.py | Attention, structural paths, heuristic readiness, fixed response templates |
| E10 | src/syune/cognition/profiles.py; tests/integration/test_profile_cognition.py | Six static policy profiles sharing memory; structural differences rather than expert agents |
| E11 | src/syune/council/service.py: snapshot, run; analysis.py; synthesis.py | Sequential profile runs, repeated whole-store fingerprints, overlap-based agreement |
| E12 | src/syune/executive/planner.py; service.py; policy.py; validation.py | Keyword action selection, three-step template, constraints/envelopes, volatile plan repository |
| E13 | src/syune/executive/execution.py; approval_runtime.py; runtime_gate.py; capabilities.py; execution_store.py | Internal host-composed approved sandbox execution, receipts, reconciliation, local preimages |
| E14 | src/syune/evals/runner.py, invariants.py, metrics.py, regression.py; tests/phase14 | Fail-closed checks and structural metrics; offline integrity checks exceed live health |
| E15 | scripts/benchmark_phase14.py: scale, soak; docs/evals/phase14_scale_v1.json, phase14_soak_v1.json | Historical selective synthetic scale and fresh-state churn soak, not cumulative lifetime validation |
| E16 | tests/phase16/test_mcp_v1.py: test_sdk_mcp_semantic_parity; docs/PHASE_16_VALIDATION.md | Historical parity assertions compare entity type/status, not learned scores or degraded states |
| E17 | pyproject.toml, uv.lock; product/config.py, schema.py; contracts/schemas/public/v1 | Packaging/config/version boundaries; two broad schemas; no general migration facility |
| E18 | docs/ADR/ADR-0002*, ADR-0004*, ADR-0010*; placeholder READMEs | Distributed/provider aspirations versus implemented local substrate; observation is not truth |
| P01–P08 | audit_probes.py and evidence/audit-probes.txt | Fresh, isolated executable characterization of gaps; see validation report |

## Runtime topology

~~~mermaid
flowchart TD
  Host[Host explicitly chooses operation] --> SDK[Syune SDK]
  Host --> MCP[stdio MCP]
  SDK --> Product[SyuneRuntime: 4 stores + index]
  MCP --> Gateway[GatewayServices: memory + Study + index]
  Product --> Study[Study and metadata perception]
  Gateway --> Study
  Study --> Registry[(Study SQLite)]
  Study --> Memory[(Memory SQLite)]
  Product --> Recall[Lexical and graph recall]
  Gateway --> Recall
  Memory --> Index[In-memory inverted index]
  Index --> Recall
  Learning[(Learning SQLite overlay)] --> Recall
  Recall --> Cog[Optional cognition]
  Cog --> Council[Optional sequential Council]
  Host --> Plan[Explicit goal: template planner]
  Plan --> Plans[In-memory plans and envelopes]
  Host --> Internal[Separate internal L3 composition]
  Plans --> Internal
  Internal --> Receipts[(Execution SQLite)]
  Internal --> Sandbox[Local sandbox file adapter]
~~~

The Learning edge applies to product/SDK recall and explicitly composed services; shipped MCP uses NullPlasticityView. Council calls cognition itself; invoking cognition does not invoke Council. Public planning accepts goal/criteria and does not automatically use prior recall/cognition/Council results. Internal ExecutiveRequest can carry those results.

## Subsystem operational reconstruction

“Public” means SDK/MCP callable in the shipped graph, not enterprise-ready. Storage listed is actual, including absence.

| Subsystem / purpose | Input → output | Dependencies / storage | Runtime path and external interface | Failure behavior / tests / operational status |
| --- | --- | --- | --- | --- |
| Core identity | UUID/time/confidence → validated values | stdlib; no store | Imported throughout; internal typed IDs mapped publicly | Reject invalid IDs/UTC/ranges; tests/unit/test_core.py; FUNCTIONAL |
| Study | Approved local path → source revision + observations/traces | Parsers, memory, registry SQLite | SDK study; MCP text/PDF only | Typed failures/checkpoints; byte/page/segment caps; durable Study integration tests; FUNCTIONAL local text |
| Perception | Media bytes + optional callback → segments/metadata/run | Local headers/WAV inspector; registry rows | Internal injection; SDK default metadata only | Unavailable/partial provider recorded; synthetic providers; PARTIAL semantic media |
| Shared Memory | Typed entities/edges → immutable records | Memory SQLite JSON, or in-memory test adapter | Study writes; public memory_get/recall reads | Duplicate/direct endpoint rejection, decode errors; unit/contracts/restart tests; FUNCTIONAL local store |
| Retrieval | Text/IDs/context → ranked IDs, paths, working selection | In-memory index, memory, optional overlay | SDK/MCP recall; cognition dependency | Empty results, typed errors, truncation; retrieval/restart tests; FUNCTIONAL lexical/structural |
| Learning | Explicit typed signal → bounded overlay and audit | Learning SQLite + memory target checks | Internal record/consolidate/rollback; SDK reads overlay | Batch rollback and bounded deltas; learning integration tests; FUNCTIONAL score adaptation only |
| Cognitive Core | Cue/profile/budget → context/inferences/readiness/templates | Retrieval + memory + profiles; transient | SDK/MCP cognize | Gaps/conflict/limits; callback exceptions; cognitive integration tests; PARTIAL product cognition |
| Profiles | Explicit profile ID → weight/budget policy | Six immutable built-ins; transient registry | Public profile names; internal registry | Unknown/inactive/version errors; profile tests; FUNCTIONAL policy overlays |
| Council | Cue + profile members → overlap/disagreement/minority report | Repeated cognition + full-store snapshots; transient | SDK/MCP council only | Member isolation, state-drift failure, coarse budgets; Council tests; FUNCTIONAL structural comparison |
| L2 Planner | Explicit goal/constraints, optional internal results → draft/envelope | Static rules, validation; in-memory plan repo | SDK/MCP plan; richer internal request | Ambiguity/constraint blocks; no execution; executive tests; WEAK task planning |
| L3 Executive | Exact plan + approval + registered capability → receipt | Host-composed plans/registry; execution SQLite; sandbox | Internal Python API only | Gate, idempotency, unknown outcomes, read-back; supervised/fault tests; FUNCTIONAL reference execution |
| Governance | Action scope/risk/budget → allow/wait/block | Executive policies/approval verifier; no identity service | L2/L3 only; Study roots/modes at public boundary | Trusted-host approval data; no memory authorization; PARTIAL |
| Evals | Declared checks/expectations → typed reports | Caller fixtures; JSON reports | Offline scripts/tests only | Missing metrics/check errors fail; regression tests; FUNCTIONAL engineering harness |
| API/SDK | v1 dataclasses → result/error envelopes | Product runtime + serializer; no separate store | Local sync Python | Partial normalization; lifecycle/schema errors; Phase 16 tests; FUNCTIONAL limited |
| MCP | Allowlisted tool args → tool result dictionaries | MCP 2; separate gateway graph | stdio only, ten normal tools | Root confinement, bounded ToolError; in-process/stdio tests; FUNCTIONAL with parity gaps |
| Host protocol | Negotiation/correlation → host-owned orchestration | SDK contracts; no durable session service | Example host and handshake | Version rejection; identity/context not an ACL; PARTIAL |
| Persistence/lifecycle | Config/root → four stores and metadata | SQLite + filesystem; index rebuilt | CLI init/health/status/upgrade check, SDK open | Schema rejection, some exact v0 adoption; no coordinated migration; FUNCTIONAL local |
| Model adapters | Provider protocols → optional perception outputs | No concrete shipped model adapter | Internal injection only | Callback-dependent; no cognition gateway; MISSING general gateway |
| Events | Reserved vocabulary; some local ledger rows | Study transitions, learning audit, receipts | No common event bus/outbox | No delivery/replay guarantee; PARTIAL fragmented local events |
| Observability | Timings/counters/health → diagnostics | In-memory timing lists; eval reports | SDK/MCP health/diagnostics | Health mostly static, no production trace backend; PARTIAL |
| Storage/domains placeholder boundaries | Documentation only | Real code elsewhere | No runtime path | STUB directories, not missing actual persistence/profiles |

## Mandatory stages and reachability

SDK open validates metadata, opens all four databases, rebuilds the whole index, constructs cognition/Council/planner/Study, then writes last-successful-open metadata. This occurs even when the caller only wants health or planning. Plan and Council construction is cheap compared with index rebuilding; no inference or Council run happens at open.

CLI MCP startup opens and closes SyuneRuntime as a check, then open_gateway opens two stores and rebuilds another index. Gateway cognition/Council/planner are independently composed. This duplication explains why the supposedly shared service graph does not guarantee behavior parity.

Recall performs no model call, learning commit, Council or planner invocation. Cognition performs one recall, potentially a second when exactly one candidate is found, then attention, structural inference and readiness/templates. Council performs one full snapshot before members and another after each attempted member. Planning performs no retrieval. L3 is not reachable through any public execution tool; importing its module is not the same as exposing execution authority.

FAST/STANDARD/DEEP are not implemented routing policies. Explicit recall/cognize/council operations provide useful future seams. A router must preserve host choice and measurable escalation criteria, not force all calls through every component.

## Persistence and portability boundaries

Memory, observations, typed knowledge records, source revisions, learning ledger/overlay and execution receipts survive restart. Profiles/policies are recreated from code. Plan state, working context, Council output, circuit state and rollback preimages are process-local. Persistent instance ID is not an agent identity system. A comprehensive world state does not exist.

Private JSON serializers preserve Python type names and IDs. This is portable across model providers at the data level, but not a public cross-language state export/migration contract. Provider/model IDs occur in perception metadata; changing provider/configuration changes derived fingerprints. No embeddings or tokenizer-dependent chunks currently create embedding-model lock-in. Actual model replacement, semantic parity and learned-procedure transfer remain UNKNOWN.

