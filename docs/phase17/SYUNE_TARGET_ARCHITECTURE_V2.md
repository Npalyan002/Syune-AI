# SYUNE target architecture V2 — proposal only

No implementation, migration, module removal or public-interface change is authorized by this document. The target is a small, measurable cognitive state service; optional reasoning/execution remains separable. See the [audit](PHASE_17_AUDIT.md), [matrix](SYUNE_CAPABILITY_MATRIX.md) and [gaps](SYUNE_GAP_REGISTER.md) for evidence and dispositions.

## Proposed structure

~~~mermaid
flowchart TD
  Host[Host or agent: authenticated principal, task, purpose] --> Boundary[Versioned SDK and protocol boundary]
  Boundary --> Policy[Policy decision and scoped query compiler]
  Policy --> Router[Cognitive router: budget and task requirements]
  Router --> Fast[FAST: exact or cached authorized evidence]
  Router --> Standard[STANDARD: scoped hybrid retrieval]
  Router --> Deep[DEEP: explicit measured escalation]
  Deep --> Planner[Optional planner]
  Deep --> Council[Optional Council]
  Fast --> Fabric
  Standard --> Fabric
  Planner --> Standard
  Council --> Standard
  subgraph Fabric[Cognitive state fabric: logical capabilities, not mandatory services]
    Raw[Immutable observations and source versions]
    Truth[Claims, evidence, validity and contradiction ledger]
    Entity[Entity and relationship projections]
    Experience[Outcome and verified experience ledger]
    Working[Task and world-state projections]
    Raw --> Truth
    Truth --> Entity
    Experience --> Truth
    Truth --> Working
  end
  Fabric --> Pack[Evidence selection and token-budget context assembly]
  Pack --> UseCheck[Final purpose and disclosure check]
  UseCheck --> HostResult[Host context or answer request]
  HostResult --> Model[Optional model adapter: cloud or local]
  Model --> HostResult
  Planner --> Proposal[Typed action proposal]
  HostResult --> Proposal
  Proposal --> Approval[Host approval and action policy]
  Approval --> Executive[Optional supervised executor or host executor]
  Executive --> Outcome[Outcome receipt and independent verification]
  Outcome --> Experience
  Experience --> Validation[Repeated evidence, attribution, held-out validation]
  Validation --> Knowledge[Versioned reusable knowledge or procedure]
  Knowledge --> Truth
  Knowledge --> Transfer[Scoped cross-agent grant and revocation]
  Transfer --> Policy
~~~

Authorization precedes retrieval rather than appearing only after it. Final disclosure/use checks are defense in depth; they do not substitute for candidate/edge filtering. The model is an optional processor used by the host, extraction or planning as needed. It is not behind every memory read or every executive action. A validated deterministic capability can execute without a model call.

## Boundaries and invariants

| Boundary | Responsibility | Required invariant |
| --- | --- | --- |
| Public interface | One request/context/error vocabulary and composition policy | SDK/MCP semantics match for same principal/state/configuration |
| Identity/policy | User/agent/org/project/department/task/type/sensitivity/purpose | Unauthenticated or out-of-scope reads/writes fail before retrieval influence |
| State fabric | Source versions, observations, claims/evidence, relations, experiences, projections | Raw observation is not verified truth; projections are rebuildable and versioned |
| Truth ledger | Observed/valid/recorded times, supersession, contradictions, verification | Current/as-of queries explicitly choose eligible fact versions; no silent overwrite |
| Retrieval | Lexical/vector/exact/entity/graph candidates and fusion | Every candidate/edge is authorized and temporally eligible; limits apply at storage boundaries |
| Context assembly | Minimal relevant evidence under explicit token budget | Every compressed/selected assertion retains evidence links and uncertainty |
| Experience learning | Outcome evidence, attribution, hypotheses, validation, generalization | No caller label or single success silently promotes organizational knowledge |
| Transfer | Publish approved abstraction to eligible agents | Grants are explicit; revocation invalidates downstream derived/cached use |
| Optional planner/Council | Evidence-based escalation with cost budget | Absence never prevents basic state/retrieval; benefit is benchmarked |
| Optional execution | Exact reviewed proposal, authenticated approval, idempotency, receipt/recovery | No implicit approval; uncertain effect is reconciled, not blindly retried |
| Adapters | Model/storage/host capabilities with explicit versions | Data identity and policies independent of provider; capabilities reported honestly |
| Operations | Bounded metrics/traces, migration/backup, live health | Health reflects actual operability; long-running storage growth is measurable |

These are logical boundaries. Start with a coherent modular process and a reference SQLite backend; no need to create a microservice, database or queue for each box. Add a remote service/index only when scale or isolation evidence requires it.

## Routing policy proposal

| Route | Entry criteria | Mandatory work | Optional work | Proof required |
| --- | --- | --- | --- | --- |
| FAST | Exact known object or reusable authorized context; no unresolved temporal/policy ambiguity | Principal/purpose check, validity check, bounded lookup, evidence envelope | Cached materialization check | No leakage/stale cache; low cold/warm cost |
| STANDARD | Ordinary recall/context reconstruction | Scoped hybrid retrieval, bounded fusion/ranking, evidence/token selection | Small deterministic structural checks | Task success versus basic RAG at equal budget |
| DEEP | Explicit host request or measured uncertainty/complexity threshold within budget | Same policy/truth constraints; bounded evidence gathering | Planner, Council, additional retrieval or model calls | Incremental quality benefit exceeds latency/token cost |

FAST/STANDARD/DEEP are proposals. The host can directly request an operation; automatic escalation must be observable and bounded, with a reason and cost estimate. Unknown confidence does not justify unlimited cognition. Neither Study nor learning consolidation belongs on every query's critical path.

## Memory and lifecycle proposal

Retain immutable observations/source versions and distinguish assertions from evidence. Add explicit provenance referential integrity, assessor/agent identity, scope and sensitivity. Use separate valid time and recorded/observed time. Model contradiction/supersession as typed relationships and verification states, not a keyword in an edge label.

Working context, episodic experience, semantic knowledge and procedural knowledge can share a storage substrate while having different validation, retrieval and retention semantics. Entity/world-state projections must be derived from eligible evidence and rebuilt after revocation.

Ingestion becomes normalize/classify/link/store with explicit unknown states. Learning becomes experience/outcome/evidence/attribution/hypothesis/repeated evidence/validation/generalization/promotion. Background consolidation, compression, decay and archive are policy-governed jobs; forgetting must traverse derivatives/indexes/caches and retain only permitted audit evidence. Do not infer human-style memory categories that have no distinct operational contract.

## Verified experience and transfer proposal

An experience record links the task, conditions, action/procedure version, exact evidence, outcome measurement, independent verifier and failure cases. Attribution must distinguish “target state observed” from “this action caused the outcome.” Candidate hypotheses retain supporting and negative cases. Promotion requires pre-registered validation over held-out tasks or contexts and an explicit scope of applicability.

Knowledge transfer publishes a versioned abstraction, not a raw private episode. Agent B receives only authorized evidence and applicability conditions. Benchmark B's task improvement, leakage, erroneous generalization and rollback after source withdrawal. Propagate revocations through lineage. Keep current score overlay as a bounded ranking signal, clearly separate from epistemic confidence.

Compression must retain source references, exceptions, contradictory evidence and reconstruction paths. Raw evidence retention should obey policy; lossless permanent retention is not automatically appropriate. Measure whether smaller context preserves task correctness and auditability.

## Storage and model choices

Preserve MemoryRepository as a reference seam but replace unbounded enumeration-centric query methods with scoped/paginated/indexed operations when implementing V2. Persist index generations and incremental changes; avoid Council fingerprints that rescan every record. Full-text/vector/graph indexes are derived views, not independent truth stores.

Use a consistent state generation for queries and Council members. Define supported writer concurrency before picking transaction/outbox machinery. A transactional outbox is a candidate for cross-store events, not an instruction to deploy a broker now. Backup/export/migration and restoration tests precede truth/ACL schema rollout.

A narrow model adapter should describe modality, schema-output support, context limit, cancellation, token accounting and provider/version provenance. Keep prompts, token budgets and embedding versions explicit. Swapping a model must preserve memory identity/policy and quantify changes in task quality; no promise of identical outputs is required.

## Disposition-to-target mapping

- Preserve typed IDs, non-epistemic observations, source provenance, deterministic ingestion, local durable reference store, bounded associative retrieval, explicit overlay audit/rollback and plan-validation boundaries.
- Modify public composition, live health, memory integrity, governance and lifecycle before enterprise sharing.
- Replace volatile full-scan indexing and keyword-template planning as product mechanisms when measurements justify replacement. Keep old mechanisms as reproducible baseline/reference where useful.
- Keep perception providers, profiles, Council and L3 opt-in. Treat structural metacognition as research until an ablation demonstrates benefit.
- Deprecate placeholder-based capability claims and compulsory brain-mimic framing; preserve historical phase documents.
- Add temporal truth, semantic hybrid retrieval, cognitive access control, verified experience, controlled transfer and compression in dependency order.

## Proposed roadmap and gates

| Phase | Proposed scope | Dependency / acceptance gate |
| --- | --- | --- |
| 18 | Competitive baseline/harness only | Reproducible fixtures, models/editions, budgets, metrics and unsupported cells; no hidden product fixes |
| 19 | Trust/contracts/lifecycle foundation | Scoped reads/writes, temporal/lineage semantics, interface parity, live health, migration/deletion tests |
| 20 | Retrieval/scale/portable operational baseline | Hybrid quality gains, bounded common-token/hub cost, incremental indexes, adapters, traceability and model-swap evidence |
| 21 | Verified experience and compression | Independent evidence/negative cases; held-out task uplift; compressed context non-inferiority; rollback |
| 22 | Organizational and cross-agent cognition | Agent B uplift under permission constraints; contamination/revocation tests |
| 23 | Optional planning/execution evolution | Incremental planning value, authenticated authority, durable recovery; keep host-owned alternatives |

This ordering is a proposal, not a commitment to six implementation phases. Phase 18 may demonstrate that some modules should remain reference-only or disappear from the product. Enterprise release requires critical gaps closed and benchmarked operational objectives, not completion of this diagram.

