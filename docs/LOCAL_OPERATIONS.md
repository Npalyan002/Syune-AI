# Local operations

## Initialize and inspect

`syune init` creates only missing product directories and empty current-version stores. Product metadata is committed last. Repeating init validates state and preserves databases, audit history, learning overlays, artifacts, config and instance identity. Unknown root entries, corrupt metadata, unsupported schemas, or a missing database from an already initialized instance stop initialization. No reset or state deletion command exists.

`syune health` opens the lifecycle-managed graph, validates component schemas, rebuilds the local retrieval index, reports `HEALTHY`, `DEGRADED`, or `UNHEALTHY`, records a successful open, then closes SQLite handles. `syune status` reports the configured instance without secrets. Exit codes are 0 success, 1 unexpected internal failure, 2 invalid input/config, 3 not initialized, 4 unhealthy/degraded operation, and 5 blocked/safety failure.

## MCP and shutdown

Set `SYUNE_STATE_ROOT` to an initialized absolute state path and run `syune mcp serve`.
The canonical Lean MCP server exposes memory, context, governance, audit, lifecycle, and
optional explicitly configured model execution. It does not expose Study. Stop the stdio
process normally; its context manager closes databases.

Single-file TXT, Markdown, and text-PDF Study is available through the Python SDK. Study
requires one or more configured absolute allowed roots; see [Study and ingestion](INGESTION.md).

## Compatibility and upgrades

Run `syune upgrade check`. Product state schema 1 and the component schemas listed in
metadata are supported by v1.1.0. No schema transition is required for this release and
there is no mutating `upgrade` command. Older, unknown, or future schemas stop startup.
Downgrade is unsupported. A future migration must be explicit, audited, validated, and
transactional where possible; opening newer software must never trigger one implicitly.

## Backup and uninstall

With SYUNE processes stopped, back up the entire state root. Critical paths are
`memory/`, `study/`, `learning/`, `execution/`, `executive/`, `artifacts/`, `metadata/`,
and `config.toml` when present. Compatibility directories may exist even though their
research services are disabled by default. `cache/` and `logs/` may be excluded. Package
uninstall has no hook and leaves state untouched.

## Troubleshooting

- “not initialized”: run `syune init` with the same state/config arguments.
- “absolute path”: correct state, config, or Study roots; current working directory is never an implicit product root.
- “unsupported product/component schema”: stop and preserve the state; do not edit metadata or databases manually.
- “missing component databases”: restore the complete state backup. Init will not silently recreate an initialized instance's missing data.
- SDK Study requires approved existing roots in `SYUNE_STUDY_ROOTS` or `config.toml`.
- Use `--debug` only for local diagnosis; normal failures omit tracebacks and private source content.
