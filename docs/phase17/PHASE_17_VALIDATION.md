# Phase 17 validation

PHASE_17_STATUS = PASS

Phase 18 readiness: READY for competitive baseline and benchmark-harness work.
Enterprise production readiness: NOT_READY.
Production code modified: NO.

## Scope and baseline

Date: 2026-09-25. Repository: local SYUNE source checkout. Baseline HEAD: e2d9ea5f49d4eb138e37531ac1d9eae7016bc0ed. Initial tracked working tree clean. Phase 16 PASS is the canonical historical milestone; this audit does not revise that historical acceptance decision.

The requested docs/phase17 directory is used. Previous phases used top-level docs/PHASE_* reports, but no repository instruction mandates that placement; the user's explicit Phase 17 path is preserved. No source, contract, package, dependency, schema, runtime config or historical phase artifact was changed. No production fix, migration, provider installation, refactor, commit or push was performed.

## New execution evidence

| Check | Actual result | Evidence |
| --- | --- | --- |
| Existing full regression suite | 230 passed in 314.98 seconds | [existing-suite.txt](evidence/existing-suite.txt) |
| Audit-only gap probes | 8 passed in 48.53 seconds | [audit-probes.txt](evidence/audit-probes.txt), [probe source](audit_probes.py) |
| Existing architecture checker | PHASE 16 architecture boundary checks: PASS | [architecture-check.txt](evidence/architecture-check.txt) |
| Baseline tracked-file inventory | 304 tracked files, 167 Python files, 101 src files | [repository-inventory.json](evidence/repository-inventory.json) |
| Baseline byte integrity / output structure | See final recorded machine check | [artifact-check.json](evidence/artifact-check.json) |
| Git diff whitespace / scope | See final machine check; baseline tracked files unchanged | [artifact-check.json](evidence/artifact-check.json) |

These test durations include this audit environment and concurrent test processes; they are not performance benchmarks. No historical scale/soak numbers were rerun or silently relabelled as fresh measurements.

### Probe interpretation

| Probe | Executed observation | Finding |
| --- | --- | --- |
| P01 | Same persisted target: SDK learned utility 0.2; MCP 0.0 | Public learned-state parity gap |
| P02 | Changed source preserves same SourceId; old marker still recalled | No automatic revision supersession |
| P03 | Retraction flag set; corresponding observation still recalled | Retraction penalizes ranking rather than excluding it |
| P04 | SQLite accepts derived observation with missing source; offline audit reports memory:source_missing | Provenance presence is weaker than referential integrity |
| P05 | Runtime closed; health overall remains HEALTHY | Live health does not establish storage operability |
| P06 | Future-created/observed memory returned under earlier temporal_context | Temporal cue is not as-of eligibility |
| P07 | Product retrieval materialization_check is None; RecallCue has no principal/scope policy fields | Composition and authorization gaps |
| P08 | Two-member Council enumerates full memory three times | Baseline and per-member full snapshots |

Probe assertions intentionally characterize present deficiencies. Their PASS confirms the finding, not acceptable future behavior. Temporary synthetic sources/databases live only under docs/phase17/_tmp; probes do not open the user's existing state. Probe P08 wraps a repository method in the test process to count enumerations; it does not edit production implementation.

## Environment and reproducibility

The first .venv/Scripts/python.exe invocation failed because its configured base Python312 installation was unavailable. A first bundled-Python attempt using PYTHONPATH alone could not load pywintypes during MCP collection. Processing existing site-packages .pth files with site.addsitedir resolved that dependency activation without installation or edits. An initial default-temp run had 109 passes and 121 fixture errors caused by temporary-directory permission restrictions. One intermediate workspace-temp attempt had a missing parent directory. The final full run used a created, workspace-local base directory and passed all 230 tests.

Successful runtime: CPython 3.12.14 using the locked project dependencies, including mcp 2.2.0, pypdf 6.19.0, and pytest 9.1.1. PYTHONDONTWRITEBYTECODE=1; pytest cache provider disabled. The dependency lock remained unchanged. This is a source regression run, not a new clean-wheel installation claim.

Reproduction: [run_audit.ps1](run_audit.ps1) accepts a compatible Python executable and activates the existing dependency directory for the current process and child processes. It creates a fresh GUID-named temporary base inside docs/phase17/_tmp and runs the existing suite followed by audit probes and the existing architecture checker. It is an audit runner, not a Phase 18 benchmark harness. The recorded run used equivalent explicit commands before the convenience runner was written.

## Repository inspection coverage

| Required area | Inspected evidence and conclusion |
| --- | --- |
| Relevant repository | Inventory/AST symbol map plus targeted manual reads of all significant runtime families and public wiring |
| Phase 00 | Architecture freeze/validation and ADR decisions; design-only foundation |
| Phase 01 | Skeleton/validation; reserved modules are not operational implementations |
| Phase 02 | Memory kernel/validation, model/repository/contracts/unit tests |
| Phase 03 / 03A | Study/durable-memory validation, registry/encoder/parsers/restart/materialization tests |
| Phase 04 | Retrieval validation/index/service/config/tests and synthetic benchmark design |
| Phase 05 / 06 | Gateway/shadow validation and stdio/shadow tests; historical live legacy host claim not rerun |
| Phase 07 | Learning validation/policy/store/service, retrieval integration and rollback tests |
| Phase 08 / 09 | Cognition/profile validation, runtime heuristics and structural-diversity tests |
| Phase 10 | Perception validation/router/protocol/inspector/registry; semantic provider tests are fakes |
| Phase 11 | Council validation/service/analyzer/synthesizer and member/state-drift tests |
| Phase 12 / 13 | Planning/execution validation, contracts, approval/gate/adapter/persistence, supervised tests |
| Phase 14 | Validation/release limitations, JSON scale/soak/eval evidence, benchmark algorithms and failure/concurrency tests |
| Phase 15 | Product config/state/schema/CLI/packaging, installed-validation claims, release/license limits |
| Phase 16 | SDK/API/MCP/host docs, schemas/fixture, public tests, installed validation and parity claim checked against implementation |
| Contracts and schemas | Python models/enums/protocols, SQLite DDL and private serializers; two broad public JSON schemas |
| ADRs | ADR-0001 through ADR-0010; physical distribution/provider gateway remain unimplemented aspirations |
| Unreachable/duplicate/experimental | Distinct product/gateway composition; internal-only L3/learning/provider seams; placeholder directories; static research-value cognitive heuristics |
| Generated artifacts | dist/.venv/test caches and ignored prior .syune outputs separated from source authority; not evidence of deployed capabilities |

Depth is not uniform: all tracked files were inventoried, major executable paths were traced, and existing tests were executed. No claim of exhaustive formal verification, third-party dependency source review or proof of absence of every latent bug is made.

## Audit acceptance mapping

| User step | Artifact / coverage |
| --- | --- |
| 1 Repository forensics | Current architecture inventory and evidence manifest |
| 2 Architecture reconstruction | Current architecture subsystem/path/storage/failure table |
| 3 Disposition | Capability matrix: one primary disposition per row |
| 4 Memory types | Main audit independent eight-type analysis |
| 5 Truth | Main audit field-versus-enforcement table |
| 6 Lifecycle | Main audit twelve-stage table and landfill analysis |
| 7 Retrieval | Main audit pipeline/mechanisms and cost map |
| 8 Learning | Main audit implemented adaptation versus missing verified generalization |
| 9 Cross-agent | Main audit transfer/contamination and G10 |
| 10 Model portability | Main audit and architecture state-survival boundaries |
| 11 Routing | Architecture mandatory stages and target FAST/STANDARD/DEEP |
| 12 Council/planner/executive | Main audit value/disposition plus runtime costs |
| 13 Compression | Main audit raw-to-abstraction absence; target invariants |
| 14 Governance | Main audit nine scope dimensions and early authorization requirement |
| 15 Scale | Cost map 10K/100K/1M/10M/100M; missing measurements explicit |
| 16 Runtime cost | Cost map calls/tokens/DB/I/O/CPU/failure surfaces |
| 17 Failure/contamination | Main audit likelihood/impact/mitigation/residual/future matrix |
| 18 Competition | Competitive gap report with dated official sources and EVR cells |
| 19 Product tiers | Main audit Tier 1/2/3 assessment |
| 20 Technical debt | Technical debt priority table and test limitations |
| 21 Target V2 | Proposal-only architecture and invariants |
| 22 Capability matrix | Complete requested columns |
| 23 Gap register | Complete requested columns and dependencies |
| 24 Value analysis | Main audit per-major-subsystem substitution/metric table |
| 25 Phase 18 readiness | READY with explicit harness prerequisites; nothing implemented |

All eleven PASS criteria are satisfied as audit deliverables: architecture, dispositions, capabilities, gaps, memory/learning, portability, cross-agent cognition, cost/failure, target V2, no production refactor, and explicit Phase 18 decision.

## Evidence limitations and status rationale

UNKNOWN: production provider quality, cross-model task continuity, comparative value, vulnerability-advisory status and unprobed concurrent consolidation race. UNMEASURED: broad/dense retrieval scale, 1M/10M/100M, real provider cost, lifetime state growth and context savings. EXTERNAL_VALIDATION_REQUIRED: competitor capabilities not directly supported by the cited edition-specific official documentation, and all independent competitive performance.

These are established missing capabilities or future benchmark questions, not unavailable canonical evidence preventing the audit. The repository and historical artifacts are available, fresh regression and targeted behavior evidence ran, and findings distinguish observation from inference. Therefore Phase 17 is PASS rather than CONDITIONAL_PASS. Phase 18 can measure shortcomings as shortcomings. This does not waive any enterprise readiness gap.

## Files and scope

Nine requested Markdown reports exist in docs/phase17. Supporting additions are audit_probes.py, audit_inventory.py, verify_artifacts.py, run_audit.ps1, a local .gitignore and evidence files. Temporary databases/source fixtures are ignored under _tmp. No production path was modified, and no recommendation was implemented.

