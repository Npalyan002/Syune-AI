# SYUNE technical debt — Phase 17

Priority is based on the intended enterprise cognitive infrastructure scope. Some debt is acceptable inside the current trusted local reference scope. Evidence IDs resolve in [architecture](SYUNE_CURRENT_ARCHITECTURE.md); remediation is tracked in the [gap register](SYUNE_GAP_REGISTER.md). No item was repaired during this audit.

| Area | Priority | Debt / consequence | Evidence | Gap / proposed phase |
| --- | --- | --- | --- | --- |
| Security / access control | CRITICAL | No authenticated memory principal or scope-aware candidate/edge/direct-read policy | E02/E04/E07, P07 | G01/G10; 19/22 |
| Architecture | HIGH | SDK product and MCP build different service graphs; a facade does not imply shared behavior | E01/E03, P01/P07 | G07/G25; 19 |
| Memory contracts | HIGH | Provenance object presence does not guarantee source/parent referential integrity | E04/E14, P04 | G13; 19 |
| Temporal schema | HIGH | No valid interval/supersession/verification state; immutable records alone do not model changing truth | E04/E05/P02/P06 | G02/G03; 19 |
| Storage / lifecycle | HIGH | Append-only API without retention, tombstones, archival or deletion propagation | E04/E08 | G12; 19 |
| Performance | HIGH | Full rebuild/sync, frequent-token sorting, adjacency materialization before limits | E04/E07/E15 | G05; 20 |
| Council | HIGH | Repeated full-state snapshots rather than a cheap consistent generation; tested cost around 3 s at 10K | E11/E15/P08 | G06; 20 |
| Learning | HIGH | Unauthenticated labels, unresolved evidence IDs, fixed outcome deltas; no causal validation/generalization | E08 | G09; 21 |
| Recovery / execution | HIGH | Plans, preimages and circuit state volatile; SQLite receipt transaction separate from filesystem effect | E12/E13 | G15; 23 |
| Authorization contract | HIGH | Hash of approval fields is integrity checking, not authenticated issuer verification | E13 | G27; 23, before any remote execution |
| Versioning / migration | HIGH | Private Python-shaped JSON, schema rejection, no general migration/export/restore workflow | E04/E08/E13/E17 | G26; 19 |
| Evals / value | HIGH | Structural fixture success cannot establish answer quality, economic value or transfer improvement | E14/E15/E16 | G20/G21; 18 |
| Observability / health | HIGH | Offline invariant checks are richer than live health; closed service reports healthy | E01/E14/P05 | G08; 19 |
| Retrieval semantics | HIGH | Generic undirected propagation and structural “independence” can imply support not warranted by evidence | E07/E09/E11 | G31; 20 |
| Public API contracts | MEDIUM | Hand-maintained common envelope/error schemas leave operation data as arbitrary objects | E02/E17 | G18; 19 |
| SDK errors/config | MEDIUM | Typed-ID parsing outside central wrapper; generic domain errors classified invalid; configured result ceiling not applied in product retrieval | E01/E02/E17 | G18/G25; 19 |
| MCP interfaces | MEDIUM | Separate serializers/redaction/IDs, narrower format set, async wrappers run synchronous service work | E02/E03/E06 | G07/G17/G18; 19/20 |
| Host protocols | MEDIUM | HostContext mostly descriptive; no durable session or enforced purpose/identity handoff | E02 | G23/G27; 20/23 |
| Events | MEDIUM | Registry transitions, learning audit and receipts have no unified delivery/correlation contract | E05/E08/E13/E18 | G19; 20 |
| Metrics | MEDIUM | Per-tool and append-latency lists retain every sample; no bounded aggregation/trace export | E03/E08 | G19/G12; 20 |
| Concurrency | MEDIUM | Separate connection tests do not establish safe multiple consolidators; snapshot proposals made before write transaction | E08, phase14 concurrency tests | G28; 20 |
| Perception | MEDIUM | Registry omits full provider/model/confidence/metrics fields present in in-memory run/segments | E05/E06 | G24/G13; 20 |
| Dependencies/toolchain | MEDIUM | Existing venv references absent interpreter; successful audit used bundled 3.12.14 plus existing packages, not a fresh locked install | E17; validation report | G30; 18 |
| Packaging/release | MEDIUM | Supported Python range broader than Windows/3.12 evidence; license decision still required for public distribution | E17; phase15/16 validation | G30; 18 |
| Documentation | MEDIUM | Reserved provider/distribution/governance module names and historical phase claims can be mistaken for shipped runtime | E18 | G29; 19 |
| Maintainability | LOW | Dense semicolon-heavy orchestration, wildcard imports and several dynamic imports complicate review; changes must be behavior-tested later | E05/E09/E12/E13 | G29; later measured maintenance work |
| Placeholder folders | LOW | Empty storage/domains/governance folders duplicate conceptual boundaries implemented elsewhere | E18 | G29; 19 |

## Test evidence quality

Real behavior is covered by SQLite round-trips, local file writes/read-back, subprocess restart, official in-process MCP client calls and stdio smoke tests. These are stronger than mocks and all 230 existing tests passed in this audit.

Limitations matter:

- Multimodal semantic providers are deterministic fakes; they do not establish real transcription/vision accuracy.
- Learning tests prove fixed policy increments, bounds and rollback, not new knowledge or held-out task improvement.
- Retrieval quality fixture has two relevant observations, three chosen cues and a distractor; it is not a representative retrieval evaluation.
- Phase 16 parity compares entity type/cognition status/plan status/authority, not learned scores, retraction or degraded-state equivalence; P01 finds a missed difference.
- Public schema tests check readable schema identifiers and a handshake fixture; they do not validate every operation response against a detailed schema.
- Architecture tests use imports/AST/text checks for forbidden dependencies. They enforce selected boundaries, not semantic security or value.
- Crash injection occurs at selected code boundaries; it is not a power-loss durability guarantee.
- The ten-minute soak resets its corpus each cycle. It does not prove long-running growth control.

## Dependency and environment assessment

pyproject.toml declares Python >=3.12,<4, mcp>=2,<3 and pypdf>=6,<7; uv.lock pins the current graph. The audit reused local mcp 2.2.0, pypdf 6.19.0 and pytest 9.1.1. No dependency was upgraded or installed. A fresh installation from lock/wheel was not repeated in Phase 17; historical Phase 15/16 installation evidence is kept distinct.

Known-vulnerability status is UNKNOWN: no advisory database audit or SBOM provenance verification was performed. This is not a claim that packages are vulnerable. Dependency pins alone neither prove safety nor ensure portability. The only observed environment defect is the stale local virtual-environment launcher, worked around without altering it.

## Remediation ordering

First establish Phase 18 baseline and adversarial cells. Before enterprise sharing, address authorization and transfer boundaries. Then establish temporal truth/lineage/lifecycle and unify interface semantics/live health. Optimize durable indexing and request budgets based on measured workloads. Only then build verified learning, compression and optional execution evolution.

Do not replace SQLite merely because a larger database sounds more sophisticated. Keep it as a local reference backend; decide the production adapter using workload/consistency/isolation requirements. Do not remove optional cognition by decree; require measurable benefit to justify maintaining it as a product feature.

