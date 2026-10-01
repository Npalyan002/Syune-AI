# Phase 17 — architecture and value gap audit

PHASE_17_STATUS = PASS

Production code modified: NO. Phase 18 readiness: READY to build a competitive benchmark harness, not ready for enterprise deployment.

The audit reconstructs and challenges the Phase 00–16 foundation. Passing Phase 17 means the audit is complete; it does not certify SYUNE's competitive value. Baseline, evidence IDs and runtime reconstruction are in [current architecture](SYUNE_CURRENT_ARCHITECTURE.md). [Validation](PHASE_17_VALIDATION.md) records reproduction and limitations.

## Investment assessment

SYUNE has useful engineering foundations: source/derived separation, deterministic provenance-bearing ingestion, durable local memory, explainable retrieval, reversible explicit score adaptation, and careful separation of proposed versus approved effects. These deserve preservation.

The product has not demonstrated its proposed differentiation. Ordinary Study creates observations and traces, not semantic concepts, entity relationships or procedures. Recall is token matching plus traversal of already supplied associations. “Cognition” is deterministic structural analysis and templated responses. “Learning” changes ranking weights from caller-labelled feedback. Council compares static policies over the same substrate. Neither verified experience generalization nor controlled cross-agent knowledge transfer is implemented.

Prioritize evidence quality, scoped retrieval, temporal truth, lifecycle and retrieval quality before expanding cognitive modules. The highest-value potential differentiator is provenance-backed, independently validated experience transfer that improves another agent's held-out task outcomes. That is a hypothesis requiring Phase 18 baselines and later validation, not current value.

## Memory types: independent semantics versus labels

All durable types share the same entities JSON table and generic structural repository. All lack per-principal permissions. This common substrate is useful but does not by itself implement distinct memory systems (E04–E09).

| Type | Actual semantics and storage | Retrieval | Lifecycle/validation/consolidation | Verdict |
| --- | --- | --- | --- | --- |
| Working | Request-local RecallResult.working_memory and Cognitive WorkingContext; IDs/attention | Ranked/capacity-bounded selection | Transient; typed budgets; no durable task/session carry-over | PARTIAL: real working set, not persistent working memory |
| Episodic | Episode description + occurred_at + provenance/confidence | Description tokens; inference orders Episode timestamps | Typed fields only; no automatic experience/outcome episode formation or consolidation | PARTIAL schema/library support |
| Semantic | Claim, Concept, Evidence records can be inserted internally | Claim statement/Concept label tokens; Evidence not lexical-indexed | Evidence claim references validated; no automatic extraction, resolution or truth maintenance | PARTIAL structural ontology |
| Procedural | Procedure is a nonempty tuple of strings | Joined step token index; generic graph | No execution binding, success evidence, versioned procedure validation or learned promotion | WEAK passive record |
| Entity | Typed identity of records, generic concepts/edges | Exact typed IDs and label tokens | No real-world entity resolution, aliases or merge/split policy | MISSING entity memory capability |
| Temporal | Observation observed_at; Episode occurred_at; source revisions and created times | Optional creation-age score; Episode BEFORE inference | No valid interval, as-of enforcement, automatic supersession or invalidation | PARTIAL timestamps/history |
| Organizational | Shared store available to callers | No organization/department/project policy | No ownership, authority, institutional validity or shared promotion workflow | MISSING |
| Cross-agent | Multiple callers can reuse one state root | Same unscoped data/overlay if same service composition | No agent identity, validation, abstraction or transfer consent | MISSING controlled cognition; shared storage exists |

The Study encoder does not create Episode, Claim, Concept, Evidence, Procedure or Association. Tests often construct richer graphs directly. Those tests prove library behavior over supplied structures, not an operational knowledge-building pipeline.

## Memory truth: field existence and operational enforcement

| Attribute | Representation | Operational meaning / limitation |
| --- | --- | --- |
| source | SourceId, Source version/hash/URI | Study deduplicates by content; repository does not require a derived record's source to exist (P04). Source row retains initial revision metadata because ensure_source is insert-only |
| provenance | Mandatory object on derived records; locators/process/version | Survives persistence, returned in results, score feature; missing source/parent references are caught by offline invariant audit, not universal write enforcement |
| evidence | Evidence with claim_ids/polarity/confidence | Referenced claims must exist on insert; evidence is not lexical indexed; inference does not consume Evidence polarity to adjudicate truth |
| confidence | Bounded typed number; extraction confidence separately labelled | Affects recall and metacognitive assessment; not calibrated probability; Study extraction confidence unknown; trace 1.0 means encoding success |
| observed_at | UTC field on Observation | Stored; temporal recall scores created_at instead; not an as-of boundary (P06) |
| valid_from | Absent | MISSING |
| valid_until | Absent | MISSING |
| supersession | Study previous_revision_id exists | Source history preserved, but obsolete observations remain retrievable (P02); no canonical truth supersession |
| contradictions | Evidence CONTRADICTS, relation labels containing contrad/conflict | Explicit edge labels produce conflict signals; generic traversal does not reason over relation direction/polarity; no automatic detection or resolution |
| verification state | Execution verification enum/receipt; no memory fact verification lifecycle | Verified filesystem state is not verified knowledge or causal outcome attribution |
| lineage | Parent provenance tuple; source revisions; trace targets | Partial traceability; parent references not write-enforced; perception registry persists subset of in-memory run metadata |
| permissions | No memory principal/ACL/purpose fields | Study roots and execution scopes do not authorize memory knowledge |
| scope | Source/context IDs and host correlation/task fields | Retrieval relevance hints, not tenant/agent/task access restrictions |

Additional “stored but not sufficient” cases: LearningSignal.outcome_value is range-validated and persisted, but policy selects fixed deltas from signal kind/label rather than magnitude; source is caller-declared enum, not authenticated identity; provenance_id is not resolved as evidence before promotion; retraction_flag persists but the retrieval view exposes only deltas (P03). Profile/domain labels do not supply expertise. HostContext fields are not accepted as an enforced session/security context by SDK operations. Schema versions reject unsupported layouts; they are not a general migration system.

## Memory lifecycle

| Stage | Status | Evidence and actual boundary |
| --- | --- | --- |
| INGEST | IMPLEMENTED | Bounded local text/Markdown/text-PDF Study; media metadata route (E05/E06) |
| NORMALIZE | PARTIAL | Parser blocks, hashes and cue whitespace/token casing; no semantic normalization |
| CLASSIFY | PARTIAL | File modality, content kind and revision state; no epistemic/memory-role classifier |
| LINK | PARTIAL | Provenance/trace references and manual association insertion; Study creates no semantic association graph |
| STORE | IMPLEMENTED | Durable immutable typed entities and ledgers; local transaction domains |
| RETRIEVE | IMPLEMENTED | Lexical/exact/structural retrieval; no claim of semantic or governed retrieval |
| REINFORCE | PARTIAL | Explicit positive/negative/coactivation overlay; no verified outcome attribution |
| CONSOLIDATE | PARTIAL | Transactional signal-to-overlay batches; no raw-to-knowledge consolidation |
| COMPRESS | MISSING | Working-set truncation is selection, not cognitive compression |
| DECAY | MISSING | Hop decay is traversal attenuation, not memory ageing/lifecycle decay |
| ARCHIVE | MISSING | No memory archive state/tier or automatic policy |
| FORGET | MISSING | No memory deletion/tombstone API, dependency invalidation or retention policy |

Long-running landfill risk is HIGH: changed revisions add observations/traces even for unchanged blocks in the new revision; old revisions stay searchable; signals/proposals/audit rows accumulate; MCP timing arrays and LearningService latency arrays grow; every Study index sync deserializes the full entity set. Whole-file duplicate hashes prevent identical re-ingestion but not semantic duplicates or revision-level accumulation. The ten-minute historical soak builds disposable state each cycle; it cannot prove bounded lifetime growth (E15).

## Retrieval pipeline and capability audit

1. Exact entity/context IDs seed at full activation; explicit source IDs add the source and a scan-derived list of its records.
2. Text is casefolded into word tokens. Posting sets are unioned. All matching records are tokenized/scored and sorted before limiting lexical seeds.
3. Queue-based association propagation uses canonical edges, strength, hop decay and optional learned coactivation. It treats links as undirected neighbors.
4. Each expanded node retrieves all adjacency rows, checks endpoints, sorts neighbors, then slices fanout. Limits bound selected expansion, not all underlying reads.
5. Candidate scoring combines seed, activation, salience, context, confidence, creation-age recency, provenance, convergence bonus and learned utility/salience.
6. Rank deterministically, cap results, select a capacity-bounded working set with optional source diversity. Cognition then applies its own attention/inference layer.
7. No permission filter exists. No validity interval filter exists. Materialization validation is an optional per-source callback: wired in gateway, absent in product SDK (P07).

| Mechanism | Status / scope |
| --- | --- |
| Semantic embedding retrieval | MISSING |
| Lexical | FUNCTIONAL token-overlap index |
| BM25/full-text engine | MISSING; lexical matching is not BM25 |
| Exact | FUNCTIONAL typed-ID lookup |
| Entity | PARTIAL record IDs/labels; no entity resolution |
| Graph | FUNCTIONAL bounded manual-association traversal |
| Temporal | WEAK age score; no as-of exclusion (P06) |
| Associative | FUNCTIONAL structural activation/convergence |
| Metadata filtering | PARTIAL source/context hints; no general predicate filtering |
| Hybrid | PARTIAL lexical + exact + graph features; no semantic/lexical ranked-list fusion |
| Reranking | PARTIAL deterministic scoring; no independent semantic reranker |
| Context optimization | PARTIAL count limits/attention/source diversity; no tokenizer, token budget or minimal sufficient evidence reconstruction |

## Learning and transfer

The implemented chain is explicit signal → target check → fixed/diminishing policy delta → transactional overlay → changed ranking. Negative feedback lowers utility/salience; source retraction penalizes derived records; rollback restores prior overlay when it would not overwrite a later applied update. These are genuine adaptive retrieval mechanics, not merely feedback storage (E08).

The requested experience → outcome → evidence → attribution → hypothesis → repeated evidence → validation → generalization → reusable procedure chain is missing beyond caller-provided outcome labels and separately verified sandbox receipts. L3 emits LearningSignalDraft with auto_commit false. It does not close that chain. No semantic unlearning, fact-confidence reduction, supersession or learned-procedure rollback exists.

Agent A can affect Agent B by writing shared state and, for SDK readers, a shared overlay. No first-class agent identity, authenticated assessor, independent evidence threshold, abstraction stage or knowledge grant intervenes. This is shared storage/ranking with contamination exposure, not safe cross-agent learning. MCP also omits the overlay, so even raw transfer is inconsistent across interfaces.

## Cognitive compression and portability

Raw observations → episodes is not automated. Episode → pattern, pattern → knowledge and knowledge → procedure are not implemented. Graph convergence is a transient structural signal, not compressed knowledge. Current code does not generate summaries that destroy raw evidence; therefore destructive compression is a future risk, not an observed implementation defect. Evidence availability still depends on source accessibility and recorded locators: raw source bytes are not archived by SYUNE.

Memory/source history/overlay/receipts survive a model change because no cognition model is embedded. Agent identity and world state are missing, plans/working contexts are transient, profiles/policies are code-defined. Perception provider outputs and configuration are model-dependent, and deterministic perception records persist only partial run metadata. Model-independent encoding is useful; cross-model task equivalence is UNKNOWN. No operational LLM gateway or multi-provider replacement test proves it.

## Council, planner and executive value

Council members are distinct weight/budget/ordering policies over the same deterministic engine and evidence, not independent expert models. Structural diversity is tested. Decision improvement is UNMEASURED. Its repeated full-memory snapshots dominate known scale cost. Keep optional; do not sell overlap as independent corroboration.

Planner generates a standard three-stage proposal around keyword-derived action categories. It is useful contract/approval scaffolding, but insufficient task decomposition. Keep the validation/envelope boundary; replace the generation strategy only if benchmarks justify providing planning inside SYUNE at all.

L3 provides meaningful sandbox safety/replay/reconciliation behavior. It remains an internal reference workflow with host-supplied plans, test approvals, process-local rollback preimages and no enterprise identity verifier. State-equivalence read-back does not establish who caused an outcome. Keep optional, outside the minimum memory runtime.

## Access control and governance

| Dimension | Enforced memory authorization? | Existing neighboring mechanism |
| --- | --- | --- |
| User | NO | Host owns user identity; not passed as principal |
| Agent | NO | No agent memory ownership/grants |
| Organization | NO | Separate state roots can be operationally isolated, not multi-tenant ACLs |
| Project | NO | Study directory root confines ingestion only |
| Department | NO | No policy dimension |
| Task | NO | Correlation/task contracts are not authorization |
| Memory type | NO | Typed IDs validate type, not access |
| Sensitivity | NO | No label or propagation policy |
| Purpose | NO | No purpose-bound use constraint |

Authorization is absent from candidate generation, graph traversal, scoring, working context and direct memory_get. Adding only output filtering later would be too late for hidden-node influence, caches, diagnostics and derived summaries. The target must prefilter candidates/edges and recheck final use. Execution approval is a different boundary. Local trusted-process scope limits current exposure; enterprise multi-user use would make this a release-blocking gap.

## Failure and contamination register

Likelihood is qualitative conditional on intended enterprise workloads, not a measured incident frequency. “High” does not assert an exploit occurred. Gap IDs in the register provide remediation tracking.

| Failure | Likelihood | Impact | Existing mitigation | Residual risk | Required future mitigation |
| --- | --- | --- | --- | --- | --- |
| False memory | High with untrusted sources | High | Observation explicitly non-epistemic | Host may treat recalled text as truth | Verification states and claim/evidence checks; G03/G09 |
| Stale memory | High under updates | High | Revision history | Old revisions returned; P02 | Supersession and as-of policy; G02 |
| Contradictory memory | High | High | Explicit conflict edge signals | Natural-language conflicts undetected | Truth ledger, signed relation semantics; G03 |
| Memory poisoning | High for shared writers | Critical | Root confinement, no automatic trusted Claim | Approved-root text can steer recall | Source trust, quarantine, authenticated writes; G01/G09 |
| Agent hallucination promotion | High if callers integrate feedback | High | No automatic L3 learning commit | Caller-labelled positive signal needs no evidence | Evidence-bound promotion thresholds; G09 |
| Cross-agent contamination | High if shared state adopted | Critical | Local deployment boundary | No agent scopes or transfer controls | Validated abstraction + grants; G10 |
| Incorrect generalization | UNKNOWN currently absent | High future impact | No generalization implemented | Proposed differentiator unproven | Holdout, negative evidence, rollback; G09 |
| Bad compression | UNKNOWN currently absent | High future impact | Raw observations retained | Future summaries could discard exceptions | Evidence-preserving compression eval; G11 |
| Permission leakage | High in multi-principal use | Critical | Separate roots/host process trust | All memory readable within instance | Pre-retrieval/edge/use authorization; G01 |
| Retrieval poisoning | High under adversarial lexical content | High | Bounded selected candidates | Token stuffing/common postings and graph hubs | Adversarial corpus, calibrated fusion; G04/G05 |
| Temporal confusion | High | High | UTC checks, Episode ordering | Future/stale data eligible; P06 | Bitemporal truth and as-of tests; G02 |
| Feedback loops | Medium now, High if automated | High | Explicit signals, bounded deltas | Repeated new signal IDs amplify unverified labels | Assessor independence/evidence dedup; G09 |
| Cascading learned errors | Medium now | High | Overlay rollback; canonical records immutable | Shared ranking amplifies bad signals, no dependency invalidation | Lineage-aware revocation and transfer rollback; G09/G10 |
| Misleading health | High after lifecycle/fault errors | High | Offline invariant audit | Closed runtime still HEALTHY; P05 | Live probes and explicit closed/degraded state; G08 |
| Resource exhaustion | High at growth/high-degree nodes | High | Selected graph/candidate caps | Full scans/sorts precede caps; sync callbacks nonpreemptible | Storage-level limits, cancellation, budgets; G05/G06/G17 |

## Value analysis by major subsystem

The foundation-model/RAG columns assess architectural substitution, not measured superiority. All outcome benefits need controlled comparisons.

| Subsystem | Measurable problem / without it | Could a foundation model suffice? | Could ordinary RAG suffice? | Complexity justified now? / value metric |
| --- | --- | --- | --- | --- |
| Core IDs/contracts | Identity/reference errors; ad hoc values without it | No durable enforcement | RAG still needs contracts | Yes; invalid-reference/replay defect rate |
| Study/perception | Repeat ingestion and lost locators; manual parsing otherwise | Extraction possible, durable lifecycle external | Often yes for text ingestion | Yes local core; duplicate rate, locator accuracy, ingest throughput |
| Persistent memory/provenance | Cross-session state loss; no auditable evidence | Context alone cannot persist independently | Yes for documents, partly for typed history | Yes; restart fidelity, provenance completeness |
| Retrieval/index | Find evidence within bounded context; full prompts otherwise | Long context may suffice for small corpora | Strong substitute; SYUNE superiority UNKNOWN | Core capability justified, current index insufficient; recall/MRR/cost at scale |
| Learning overlay | Feedback-driven ranking; static ranking otherwise | Prompt examples may suffice | Feedback reranking can suffice | Conditional; held-out retrieval uplift and rollback correctness |
| Cognitive Core | Structural support/gap report; host reasoning otherwise | Likely sufficient for many tasks; untested | RAG plus model may suffice | Flag for ablation; grounded task success per token/ms |
| Profiles | Explicit domain policy; one default policy otherwise | Prompt policies may suffice | Retrieval weight presets equivalent | Low cost but value unproven; subgroup task gain |
| Council | Compare policy results; single analysis otherwise | One strong model may suffice | Multiple retrieval configurations can substitute | Optional, flagged; accuracy gain versus latency |
| L2 planner | Validated proposals; host must plan otherwise | Can generate plans, validation still needed | RAG alone not action governance | Envelope/validator useful; generation weak; feasible-plan rate |
| L3 executive | Approved/replay-safe effects; host owns execution otherwise | Model alone cannot enforce authority | RAG not execution layer | Optional; zero unauthorized effects, safe recovery rate |
| Governance | Prevent unauthorized use/effects | No reliable model-only enforcement | RAG also requires external ACLs | Essential; leakage and unauthorized-effect rate |
| SDK/API/MCP/host | Reusable integration; custom internal coupling otherwise | Model needs interface | Standard tools can wrap RAG | Yes; integration effort, parity/error consistency |
| Persistence/product config | Repeatable startup/state ownership | No | RAG needs operational lifecycle too | Yes but eager graph excessive; recovery/open cost |
| Evals | Detect regressions and quantify value | Cannot self-certify | Same necessity | Yes; held-out regressions caught, baseline reproducibility |
| Events/observability | Trace and diagnose failures | No | Standard telemetry sufficient | Extend ordinary tooling, avoid bespoke bus without need; trace completeness/MTTR |
| Model gateway | Replace processors without losing state | Provider-specific host may suffice | Standard provider adapters viable | Add narrow boundary when real integration needed; swap success/cost |
| Compression | Minimize necessary context over time | Model summaries possible | Summarized RAG viable | Missing; retain only if token savings preserve task/evidence accuracy |

## Strategic layers and disposition

Tier 1: memory/provenance/local persistence and interfaces are useful foundations; temporal truth, contradiction handling, full hybrid retrieval, lifecycle, scale, governance, live observability and general adapters are incomplete or missing.

Tier 2: score adaptation is not verified experience learning; shared memory is not controlled cross-agent learning; bounded context is not compression; absent model coupling is not tested portability. Minimum necessary cognition is achievable through current explicit operation seams. Cognitive access control is absent.

Tier 3: cognitive readiness analogies, profile expertise and Council benefit remain research hypotheses. No implemented emotion, curiosity, artificial self or conscious-access subsystem was found. Do not add those to satisfy a neuroscience checklist.

Every significant component has exactly one primary disposition in the [capability matrix](SYUNE_CAPABILITY_MATRIX.md). [Gap register](SYUNE_GAP_REGISTER.md), [cost map](SYUNE_RUNTIME_COST_MAP.md), [technical debt](SYUNE_TECHNICAL_DEBT.md), [competitive comparison](SYUNE_COMPETITIVE_GAP.md) and [target architecture](SYUNE_TARGET_ARCHITECTURE_V2.md) contain the actionable audit outputs. Recommendations are not implemented.

## Phase 18 readiness decision

READY for PHASE 18 — COMPETITIVE BASELINE & BENCHMARK HARNESS.

The current implementation is callable, all 230 existing tests pass, eight adverse behaviors are reproduced, and limitations can be benchmarked without pretending missing capabilities exist. No production feature must be silently repaired to start measurement.

Phase 18 must first pin datasets/model versions, evaluator rules, reproducible environment and budget policy; isolate synthetic/publicly licensed data; define unsupported-operation results; preserve this commit as the baseline. Provider credentials, exact frontier models and external system editions are not configured/selected by this audit. Their results remain UNKNOWN until actually run.

Required arms: frontier LLM with minimal supplied context, the same model with long context, basic RAG, and SYUNE plus the same model. Include Mem0/Zep/Letta only where version/edition, data policy and reproducible access are available. Compare equal task/corpus/answer budgets; disclose any added host glue. Ablate lexical-only, association expansion, overlay, cognition, profiles and Council. Track task success, groundedness, stale/contradictory answers, leakage, transfer improvement, tokens, calls, cold/warm latency, ingestion/storage growth, and recovery. Pre-register thresholds in Phase 18 before tuning. A missing capability is an explicit failed/unsupported cell, never an omitted hard case.

Phase 18 should not expand the architecture during baseline collection. Enterprise release remains NOT_READY pending critical/high gaps.

