# Phase 15 productization and packaging

## Preflight and drift record

Baseline was clean `main` at `b52d27f`; the execution brief was repository-locally excluded. The Phase 14 release result was READY_WITH_LIMITATIONS and contained no blocker to local productization. Its scale, provider, crash-model, rollback/circuit persistence, concurrency and synthetic-quality limits remain binding.

Before implementation, packaging already used Hatch with a `src/syune` wheel target and locked MCP/PDF dependencies. Drift was limited to product lifecycle concerns: development version metadata, no console entry point, MCP-specific relative state, no unified config/bootstrap, no product metadata/schema inventory, no safe init/status/upgrade check, and no installed-wheel evidence. Component schemas were Memory 1, Study/perception 1, Learning 1, Execution 1, profiles 1; Council and planner have no durable store. There was no product state schema and no schema transition to perform.

## Package and identity

The distribution name is `syune`, display name SYUNE, description Persistent Cognitive Intelligence, and canonical version is `[project].version = 0.1.0` in `pyproject.toml`. Runtime `syune.__version__` derives from installed distribution metadata. Python support is `>=3.12,<4`. Phase 15 is pre-1.0 and makes no finalized public SDK/API promise.

Semantic Versioning policy is documented in CHANGELOG: breaking stable contract/schema behavior is MAJOR, backward-compatible capability is MINOR, compatible fix is PATCH. Pre-1.0 minor releases may refine surfaces with explicit compatibility notes. No release publishing is implemented.

Runtime dependencies are `mcp>=2,<3` (existing stdio gateway) and `pypdf>=6,<7` (imported by core Study PDF support). Neither is a newly added dependency. Pytest remains in the `dev` dependency group. There are no optional heavy media/provider dependencies to separate: built-in image/audio/video inspection uses the standard library and external provider adapters are not installed. No license choice exists; `LICENSE_DECISION_REQUIRED` blocks later public release.

## Configuration and state

`SyuneConfig` is immutable and typed. Precedence is hard defaults, TOML file, environment, CLI. Supported variables and file schema are in CONFIGURATION.md. Paths must be absolute, Study roots must already exist, recall remains capped at 32, logging is one of four levels, and telemetry is fixed OFF. Unknown sections/keys or malformed types fail before runtime open.

Default state is `%LOCALAPPDATA%/SYUNE` on Windows and XDG/user-local state elsewhere. `SYUNE_STATE_ROOT` or `--state-root` selects an isolated instance. No path points at the checkout/package. Layout:

```text
<state_root>/
  memory/memory.sqlite3
  study/study.sqlite3
  learning/learning.sqlite3
  executive/
  execution/execution.sqlite3
  cache/ artifacts/ logs/
  metadata/state.json
  config.toml (optional)
```

Metadata has product version, umbrella state schema 1, UTC initialization/last-open timestamps, a random local instance UUID, and the exact component inventory. The UUID is local instance identity only; it is never transmitted or treated as a person/device identity.

Initialization permits only known top-level entries, creates structural directories/stores, validates each store, and atomically writes metadata last. A pre-metadata interruption can be retried. Once metadata exists, init only validates and preserves the instance; a missing database, unknown schema or corruption stops. No reset, deletion, automatic migration or uninstall hook exists.

## Runtime and operations

`SyuneRuntime.open` implements load/validate/open/build/health-ready. It requires metadata and every database before constructing the existing Memory, Study, Learning, Retrieval, Profile, Cognition, Council, Planner and Execution objects. It records a successful open only after construction. Context-manager close shuts Execution, Learning, Study and Memory stores once. Product health reuses HEALTHY/DEGRADED/UNHEALTHY vocabulary separately from cognitive scores.

CLI parsing is separate from domain services. Commands are `--version`, `version`, `init`, `health`, `status`, `config show`, `config validate`, `upgrade check`, and `mcp serve`, with human and `--json` output. Exit codes are documented. Normal errors show bounded messages; `--debug` opts into tracebacks.

MCP wire/tool contracts are unchanged. `python -m syune.gateway.mcp` and `syune mcp serve` both route through product config/state. Gateway repository construction accepts explicit product Memory/Study paths, while direct test/library construction remains compatible. MCP remains L1 advisory and does not open or expose supervised execution.

## Compatibility and upgrades

State schema 1 is the only product schema. All existing component data schemas remain version 1 and constructors continue their Phase 14 validation. Council/plans have no durable schema. `upgrade check` compares local metadata to software support without network or mutation. Current state needs no migration, and no earlier product schema exists, so a migration framework and mutating `upgrade` command would be unnecessary. Future/unknown/older incompatible metadata stops; downgrade is unsupported. Future migrations must be explicit and audited, never import/open side effects.

The state root is the backup boundary; stop processes and copy it, optionally excluding cache/logs. Full backup/restore hardening remains Phase 17. Removing the package preserves state.

## Security and architecture

The wheel contains no state, databases, `.env`, credentials, caches, logs, execution artifacts, checkout paths or legacy integration files. Product runtime has no HTTP/socket client, telemetry sender, generic shell/eval/exec, self-approval or L4 path. Build/runtime uses no ART-DEP-AI directory. Architecture checks authorize only CLI/product modules and retain prior boundaries.

Productization wraps existing behavior. No cognitive model, score, inference, Council, planning, approval, execution, learning or provenance semantics changed. No ADR was required because no frozen decision was relaxed; this document records Phase 15 lifecycle decisions.

## Compatibility statement and limitations

Validated: Windows 11, CPython 3.12.10, wheel and sdist, another working directory, two isolated roots, local stdio MCP, no network/provider at runtime health. Python declares 3.12 through pre-4; other OS validation and hardening are deferred to Phase 17. Optional provider behavior and compressed-media limits remain as Phase 14 documented.

Phase 14 limits remain: host restoration of plans, process-local circuit/rollback preimages, cooperative provider deadlines, separate-connection concurrency, no distributed runtime, trusted local sandbox, historical locator preservation, small curated cognitive judgments and Council scaling. Phase 15 adds no public service/auth/multi-tenancy, REST API, SDK stability, cloud, telemetry backend, destructive state tooling, legacy migration or L4 authority.
