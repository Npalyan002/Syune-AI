# Phase 15 validation

**Result: PASS for standalone local productization.** Package version 0.1.0 is pre-1.0. Cognitive and authority behavior remains the Phase 14 baseline. Public distribution remains blocked by `LICENSE_DECISION_REQUIRED`; that decision is explicitly outside internal Phase 15 acceptance.

## Build and installed product

Baseline: clean `main` at `b52d27f`. `uv lock` resolved the same 38-package graph and changed only the local project metadata from 0.1.0.dev0 to 0.1.0. No runtime dependency was added, removed or upgraded.

`uv build` produced standard artifacts:

| Artifact | Size | Members | Result |
| --- | ---: | ---: | --- |
| `syune-0.1.0-py3-none-any.whl` | 126,130 bytes | 96 | PASS |
| `syune-0.1.0.tar.gz` | 96,059 bytes | 101 | PASS |

The wheel was installed with declared dependencies into a newly created Python 3.12.10 environment. From another working directory, `import syune` resolved to that environment's `site-packages`, `syune --version` returned 0.1.0, and no checkout path was on the product import path. Version comes from `pyproject.toml` package metadata; `syune.__version__` calls `importlib.metadata` and contains no duplicate release string.

## CLI and state lifecycle

Fresh installed commands passed: version, init, repeated init, health, status, config show, config validate and upgrade check. Init created state schema 1 and four component databases. Repeated init returned `created: false`, retained the same local instance UUID and did not modify existing domain data. Human and JSON modes, invalid config/command handling and exit codes are covered.

Two explicit state roots receive different instance IDs and independent empty stores. An initialized root reopens from another working directory. A deterministic pre-metadata partial structure can be completed; once metadata exists, missing databases block rather than being recreated. Uninitialized, unknown-entry, corrupt metadata, future schema, missing component and simulated read-only metadata cases return explicit errors. No init/reset/delete path removes data.

Config precedence is defaults < TOML < environment < CLI. Tests cover each layer, unknown keys, malformed types, relative paths, invalid roots/enums, environment parsing and the hard recall limit. Telemetry remains OFF even if an unrecognized telemetry environment variable exists. Resolved config contains no secrets.

State layout and schema inventory:

| Component | Durable location | Schema |
| --- | --- | ---: |
| Product metadata | `metadata/state.json` | 1 |
| Shared Memory | `memory/memory.sqlite3` | 1 |
| Study + perception | `study/study.sqlite3` | 1 |
| Learning ledger/overlay | `learning/learning.sqlite3` | 1 |
| Execution audit | `execution/execution.sqlite3` | 1 |
| Profiles | built-in definitions | 1 |
| Council | not durable | none |
| Planner | in-memory host-supplied plans | none |

Current state needs no migration. `upgrade check` reports compatible, migration required false, migration available false, downgrade supported false. Since Phase 15 introduces the first product-state schema and changes no component schema, no migration framework or mutating upgrade command was created. Future/unknown schemas fail closed and opening state never migrates it.

## Runtime and MCP

The runtime factory opens metadata, all four stores, retrieval index, profiles, Cognition, Council and planner, reports every requested component HEALTHY, records successful open, then closes all handles. Base init/health uses no external provider, credential, cloud, network or legacy repository.

The final wheel was launched as `syune mcp serve` from outside the checkout using the unified state root/config and explicit local Study root. The official `mcp.Client` connected over stdio, discovered exactly the five existing allowlisted tools, received healthy gateway/retrieval status, studied one synthetic local source and recalled it. Gateway contract version remains 1 and authority remains L1 ADVISORY. No MCP tool or wire contract was redesigned.

## Artifact and security audit

Wheel/sdist member inspection found zero `.git`, `.syune`, local database, `.env`, bytecode/cache, log, execution-state, or hard-coded local-path entries. The wheel contains the console entry point and product modules. It contains no credentials or local state. The deliberately narrow sdist includes package/build metadata and product-facing docs, while excluding tests, internal eval evidence and historical development material. Runtime code has no host-application dependency, generic shell/eval/exec, HTTP/socket client, telemetry sender, destructive reset or L4 path.

Package removal has no state hook, so uninstall preserves the state root. The state root is the documented backup boundary; cache/logs may be omitted. No destructive state command exists.

## Regression and performance

Final full suite: **221 passed**, zero failed, errors or skipped. This includes all 203 Phase 14 tests plus 18 Phase 15 cases; existing Cognitive, Council, planning, approval, execution, recovery and provenance tests remain unchanged except MCP process setup now initializes unified product state. Architecture check and whitespace check pass.

Installed-wheel fresh-process measurements on Windows 11 / Python 3.12.10:

| Operation | p50 ms | p95 ms | Samples |
| --- | ---: | ---: | ---: |
| version process | 2,362.51 | 2,683.22 | 5 |
| status process | 2,976.49 | 3,014.02 | 5 |
| full health/bootstrap/close | 3,419.53 | 3,602.33 | 5 |
| MCP connect + health | 4,020.55 | one sample | 1 |
| first recall after installed MCP Study | 8.11 | one sample | 1 |

Health includes config/metadata resolution, four SQLite opens/schema checks, retrieval rebuild, service graph, metadata update and graceful close. Phase 14's small-fixture direct Python process median was 1,599 ms; the installed full health median adds about 1,821 ms, while the first selective recall remains within Phase 14's coarse absolute/relative regression policy. Process timings include Windows interpreter/console/endpoint-scanner overhead and five-sample p95/p99 are maxima, not production tails. No cognitive benchmark regression was introduced; the complete Phase 14 test corpus passes.

## Decisions, deviations and unresolved risks

- `pypdf` and `mcp` remain core dependencies because Study imports PDF support and MCP is a required Phase 15 installed command. There are no heavy optional providers/media libraries to place in an extra; no unnecessary extra was invented.
- No migration framework exists because there is no known source-to-target product schema transition. This follows the brief's “only if actually required” rule.
- Only Windows was validated. Declared Python support is 3.12 through pre-4; cross-platform hardening is Phase 17.
- Public release is blocked by `LICENSE_DECISION_REQUIRED`. No authors, URLs or license were fabricated.
- MCP startup requires an explicit existing Study root; base init/health/status do not. This preserves its source-access boundary.
- The state read-only case is fault-injected because Windows permissions are ACL-dependent; production ACL/backup hardening remains Phase 17.
- Phase 14 limitations are carried forward: host plan restoration, process-local rollback/circuit state, cooperative provider deadlines, compressed-media gaps, bounded concurrency, trusted local sandbox, historical perception preservation, synthetic quality coverage and Council scaling.
- No ADR was created or modified. The Phase 15 architecture document records lifecycle decisions without relaxing frozen invariants.

## Exit checklist

- [x] standard package build succeeds
- [x] wheel installs in clean environment
- [x] package imports outside repo
- [x] one canonical version source exists
- [x] semantic version policy documented
- [x] CLI entry point exists
- [x] `syune --version` works
- [x] `syune init` works
- [x] repeated init is idempotent
- [x] `syune health` works
- [x] `syune status` works
- [x] `syune config show` works
- [x] config validation works
- [x] unified typed config exists
- [x] config precedence tested
- [x] canonical state-root model exists
- [x] no hard-coded repository runtime dependency
- [x] multiple state roots isolated
- [x] product state metadata exists
- [x] instance ID exists
- [x] runtime bootstrap/factory exists
- [x] graceful shutdown works
- [x] component schema inventory exists
- [x] product state schema version exists
- [x] incompatible future schema blocks
- [x] upgrade compatibility check exists
- [x] migration framework not required because no schema transition exists
- [x] no automatic destructive migration
- [x] package uninstall does not delete state
- [x] installed MCP gateway launches
- [x] MCP uses unified state/config
- [x] no ART-DEP-AI dependency
- [x] no network/provider required for base health
- [x] build artifact contains no local DB/secrets/state
- [x] optional heavy dependencies appropriately classified; none exist
- [x] README product section exists
- [x] QUICKSTART exists
- [x] CONFIGURATION docs exist
- [x] LOCAL_OPERATIONS docs exist
- [x] CHANGELOG exists
- [x] compatibility statement exists
- [x] known limitations documented
- [x] full existing test suite passes
- [x] packaging/CLI tests pass
- [x] architecture check passes
- [x] `git diff --check` passes
- [x] bootstrap/performance impact documented
- [x] ART-DEP-AI untouched
- [x] no PHASE 16 work started
- [x] local commit created (closing postcondition verified after the enclosing commit)
- [x] working tree clean (closing postcondition verified after the enclosing commit)
- [x] no remote/push

Versioned evidence: `evals/phase15_installed_validation_v1.json`, `evals/phase15_artifact_audit_v1.json`, and `evals/phase15_bootstrap_v1.json`. The exact changed-file inventory is the enclosing local commit. Dependencies changed: none; only project version/range and console entry point metadata changed.
