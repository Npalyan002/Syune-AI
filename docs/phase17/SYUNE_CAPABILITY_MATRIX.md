# SYUNE capability matrix — Phase 17

Each component/capability below has exactly one primary disposition. FUNCTIONAL means working within the stated reference scope, not enterprise-ready. No capability is rated STRONG without comparative value evidence. Current/target maturity are explicit descriptions rather than arbitrary maturity scores. References resolve in [architecture](SYUNE_CURRENT_ARCHITECTURE.md); gaps in [register](SYUNE_GAP_REGISTER.md). Proposed phases beyond 18 are not approved work.

| Capability | Current status | Evidence | Current maturity | Target maturity | Gap | Disposition | Priority | Benchmark required | Target phase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Typed identity/contracts | FUNCTIONAL | E04/E17 | Local typed invariants | Validated portable contracts | References not fully enforced; G13/G18 | KEEP_CORE | HIGH | Reference corruption, schema compatibility | 19 |
| Source/observation/provenance ontology | FUNCTIONAL | E04/E05/P04 | Persistent non-epistemic records | Resolvable source/version/lineage | G13; weak source existence checks | KEEP_CORE | HIGH | Locator/source/parent integrity | 19 |
| Study ingestion/registry/parsers | FUNCTIONAL | E05 | Local text/PDF checkpoints | Revision-aware scalable ingestion | G02/G12/G13 | EXTEND | HIGH | Revision delta/dedup/throughput | 19 |
| Multimodal perception | PARTIAL | E06 | Metadata and injected callbacks | Evaluated optional adapters | G24; semantic quality UNKNOWN | OPTIONAL | MEDIUM | Real OCR/ASR/vision accuracy + timeout | 20 |
| Memory repository contract | FUNCTIONAL | E04 | Insert/get/edges/enumeration | Scoped transactional state access | G01/G12/G13 | MODIFY | HIGH | Scope isolation and lifecycle invariants | 19 |
| SQLite persistence adapter | FUNCTIONAL | E04/E15 | Single-process local reference | Reliable local reference backend | G26; distributed scale not claimed | KEEP | MEDIUM | Restart/corruption/restore | 19 |
| In-memory reference repository | FUNCTIONAL | E04; unit tests | Test/local fixture adapter | Small deterministic reference | Linear edge scan acceptable only for bounded fixtures | KEEP | LOW | Contract parity | 18 |
| Working memory/task context | PARTIAL | E07/E09 | Transient bounded IDs | Persistent minimal task reconstruction | G23; no session state | EXTEND | MEDIUM | Restart task continuity per token | 20 |
| Episodic memory | PARTIAL | E04/E09 | Passive Episode + timestamp ordering | Outcome/evidence-linked experience | G09; no automatic episode lifecycle | EXTEND | HIGH | Attribution and negative outcome tests | 21 |
| Semantic memory | PARTIAL | E04/E05 | Claim/Concept/Evidence types | Verified versioned knowledge | G03/G09; not Study-generated | EXTEND | HIGH | Claim precision, contradictions, provenance | 19 |
| Procedural memory | WEAK | E04/E08 | Stored step strings | Validated reusable procedure versions | G09/G11; no learned execution semantics | EXTEND | HIGH | Held-out procedure success/unlearning | 21 |
| Entity memory/world state | MISSING | E04/E05 | Record identity only | Resolved entities/current-as-of projections | G22 | MISSING | HIGH | Entity resolution and merge/split errors | 20 |
| Temporal truth | PARTIAL | E04/E07/P02/P06 | Timestamps/revision history | Bitemporal retrieval/supersession | G02 | MODIFY | HIGH | As-of, stale and future exclusion | 19 |
| Organizational memory | MISSING | E02/E04 | Shared store only | Scoped institutional knowledge | G01/G10 | MISSING | CRITICAL | Department/project isolation and transfer | 22 |
| Cross-agent learning | MISSING | E02/E08 | Shared raw data/overlay | Validated permissioned transfer | G10 | MISSING | CRITICAL | Agent B held-out improvement + contamination | 22 |
| Confidence/evidence/contradiction semantics | PARTIAL | E04/E07/E09 | Score inputs + explicit conflict edges | Calibrated epistemic states | G03/G31 | EXTEND | HIGH | Calibration and contradictory evidence cases | 19 |
| Memory lifecycle | PARTIAL | E04/E05/E08 | Ingest/store/read/reinforce | Retention/archive/forget/invalidation | G12 | EXTEND | HIGH | Growing corpus and deletion propagation | 19 |
| Lexical seed index | FUNCTIONAL | E07/E15 | Volatile token posting sets | Incremental durable bounded retrieval | G04/G05 | REPLACE | HIGH | Frequent terms, cold start, update lag | 20 |
| Associative retrieval service | FUNCTIONAL | E07 | Bounded structural propagation | Relation-aware hybrid relevance | G31/G04 | KEEP_CORE | HIGH | Multi-hop uplift, hubs, contradiction paths | 20 |
| Semantic/BM25 hybrid retrieval | MISSING | E07 | No embeddings/BM25 | Measured lexical/vector/graph fusion | G04 | MISSING | HIGH | Paraphrase recall, ablation and token cost | 20 |
| Context optimization | PARTIAL | E07/E09 | Count limits/attention | Minimum necessary evidence by token budget | G04/G11 | EXTEND | HIGH | Task accuracy versus context tokens | 21 |
| Explicit learning ledger/overlay | FUNCTIONAL | E08/P03 | Bounded adaptation + rollback | Auditable reliable ranking adaptation | G09/G28; not truth learning | KEEP_CORE | HIGH | Held-out ranking uplift/rollback/concurrency | 21 |
| Verified experience learning | MISSING | E08/E13 | Outcome labels, separate receipts | Evidence-backed generalization | G09 | MISSING | HIGH | Independent repeated evidence + holdout | 21 |
| Cognitive compression | MISSING | E05/E08/E09 | No abstraction pipeline | Traceable patterns/knowledge/procedures | G11 | MISSING | HIGH | Compression non-inferiority and traceability | 21 |
| Cognitive Core heuristics | PARTIAL | E09 | Structural inference/readiness/templates | Only measured useful analysis | G20/G31; task benefit UNMEASURED | RESEARCH | MEDIUM | Against recall + foundation model | 18 |
| Activation profiles | FUNCTIONAL | E10 | Six static weight policies | Explicit inexpensive task policies | G20; expertise unproven | OPTIONAL | LOW | Per-domain benefit versus default | 18 |
| Cognitive Council | FUNCTIONAL | E11/P08 | Sequential structural comparison | Optional evidence-beneficial deep path | G06/G20 | OPTIONAL | HIGH | Task quality per full cost versus single run | 18 |
| L2 plan generation | WEAK | E12 | Keyword + three-step template | Useful optional task planning | G14 | REPLACE | MEDIUM | Feasible plans versus host/model | 23 |
| Plan validation/envelopes | FUNCTIONAL | E12/E13 | Constraints/version/scope boundary | Durable reviewed proposals | G15/G27 | KEEP_CORE | HIGH | Scope drift and restart reauthorization | 23 |
| L3 supervised runtime/capability registry | FUNCTIONAL | E13 | Internal sandbox reference | Optional authenticated/recoverable executor | G15/G27; no public execution | OPTIONAL | HIGH | Unauthorized effects, recovery, attribution | 23 |
| Sandbox file adapter | FUNCTIONAL | E13 | Fixed-purpose local demonstration | Reference-only fixture adapter | Rollback preimages process-local | KEEP | MEDIUM | Recovery/preimage and confinement | 23 |
| Cognitive access control | MISSING | E02/E07/P07 | No memory principal | Pre-retrieval and use authorization | G01 | MISSING | CRITICAL | Direct/graph/cache/derived leakage | 19 |
| Action governance | PARTIAL | E12/E13 | Trusted-host object verification | Authenticated external authority | G27 | MODIFY | HIGH | Issuer/revocation/scope matrix | 23 |
| Public API/SDK | FUNCTIONAL | E02/E16 | Local synchronous facade | Consistent stable typed contracts | G07/G18/G25 | MODIFY | HIGH | Learned/degraded/error parity | 19 |
| MCP gateway | FUNCTIONAL | E03/P01 | stdio local allowlist | One consistent service composition | G07/G19/G25 | MODIFY | HIGH | SDK/MCP semantic and score parity | 19 |
| Host integration protocol | PARTIAL | E02/E16 | Handshake/example/context types | Operational scoped state handoff | G23/G27 | EXTEND | MEDIUM | Session/restart/model handoff | 20 |
| Product lifecycle/configuration | FUNCTIONAL | E01/E17 | Four-store initialization/open | Lazy bounded coherent runtime | G25/G26 | MODIFY | MEDIUM | Config ceiling parity + cold costs | 19 |
| Model gateway/adapters | MISSING | E06/E18 | Perception protocols only | Portable processor boundary | G16 | MISSING | HIGH | Same state through two providers/local | 20 |
| Model portability guarantee | UNKNOWN | E01/E06/E12 | Model-neutral data; no swap evidence | Behavioral continuity with measured loss | G16/G23 | UNKNOWN | HIGH | Provider swap identity/knowledge/task retention | 18 |
| Events and audit delivery | PARTIAL | E05/E08/E13/E18 | Separate transition/audit/receipt rows | Traceable minimal event contract | G19 | EXTEND | MEDIUM | Correlation/replay/no lost state transitions | 20 |
| Live health/observability | PARTIAL | E01/E03/E14/P05 | Timers/static health/offline checks | Bounded live probes/traces | G08/G19 | MODIFY | HIGH | Closed/corrupt/unavailable health matrix | 19 |
| Evals/regression harness | FUNCTIONAL | E14/E15 | Structural synthetic checks | Held-out controlled comparisons | G20/G21 | EXTEND | HIGH | All baseline arms + quality/cost ablation | 18 |
| Distributed enterprise storage | MISSING | E01/E04/E18 | Local SQLite only | Workload-justified scale/isolation | G05/G21/G26 | MISSING | HIGH | 1M/10M/100M only with resource plan | 20 |
| Reserved brain-inspired placeholders | STUB | E18 | Documentation boundaries | No mandatory runtime role | G29 | DEPRECATE | LOW | No benchmark until concrete value hypothesis | 19 |
| Packaging/release reproducibility | PARTIAL | E17; audit validation | Windows local package, recovered test runner | Reproducible distribution | G30 | MODIFY | MEDIUM | Clean install/OS CI/release review | 18 |

Disposition reasoning: KEEP_CORE preserves aligned contracts/mechanics, not every current implementation detail. KEEP preserves useful reference infrastructure. MODIFY addresses a required existing boundary. EXTEND adds missing behavior to a credible foundation. OPTIONAL keeps explicit opt-in surfaces outside mandatory paths. RESEARCH reserves claims lacking task-level utility. REPLACE targets specific weak mechanisms, not wholesale subsystem removal. DEPRECATE targets unsupported architecture framing/placeholders, preserving historical artifacts. MISSING and UNKNOWN are not implied PASS.

