# Local operations

## Initialize and inspect

`syune init` creates only missing product directories and empty current-version stores. Product metadata is committed last. Repeating init validates state and preserves databases, audit history, learning overlays, artifacts, config and instance identity. Unknown root entries, corrupt metadata, unsupported schemas, or a missing database from an already initialized instance stop initialization. No reset or state deletion command exists.

`syune health` opens the lifecycle-managed graph, validates component schemas, rebuilds the local retrieval index, reports `HEALTHY`, `DEGRADED`, or `UNHEALTHY`, records a successful open, then closes SQLite handles. `syune status` reports the configured instance without secrets. Exit codes are 0 success, 1 unexpected internal failure, 2 invalid input/config, 3 not initialized, 4 unhealthy/degraded operation, and 5 blocked/safety failure.

## MCP and shutdown

Configure one or more absolute Study roots and run `syune mcp serve`. It uses the same state root, memory and Study databases as the CLI. Stop the stdio process normally; its context manager closes databases. MCP stays L1 advisory and cannot invoke the L3 execution runtime.

## Compatibility and upgrades

Run `syune upgrade check`. Product state schema 1 and component schemas listed in metadata are supported by 0.1.0. No schema transition is needed, so Phase 15 intentionally contains no migration engine or `upgrade` mutation command. Older/unknown/future schemas stop. Downgrade is unsupported. A future known migration must be explicit, audited, pre/post-validated and transactional where possible; opening newer software must never trigger one automatically.

## Backup and uninstall

With SYUNE processes stopped, back up the entire state root. Critical paths are `memory/`, `study/`, `learning/`, `execution/`, `executive/`, `artifacts/`, `metadata/`, and `config.toml` when present. `cache/` and `logs/` may be excluded. Phase 17 will harden backup/restore. Package uninstall has no hook and leaves state untouched.

## Troubleshooting

- “not initialized”: run `syune init` with the same state/config arguments.
- “absolute path”: correct state, config, or Study roots; current working directory is never an implicit product root.
- “unsupported product/component schema”: stop and preserve the state; do not edit metadata or databases manually.
- “missing component databases”: restore the complete state backup. Init will not silently recreate an initialized instance's missing data.
- MCP requires Study roots: set `SYUNE_STUDY_ROOTS` to approved existing directories.
- Use `--debug` only for local diagnosis; normal failures omit tracebacks and private source content.
