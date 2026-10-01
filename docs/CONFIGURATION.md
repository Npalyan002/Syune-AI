# SYUNE configuration

Resolution order is hard safety defaults, TOML config, environment, then explicit CLI arguments. Safety ceilings remain bounded by runtime types and cannot be widened by config. A config file is optional. The resolver checks `--config`, then `SYUNE_CONFIG`, then `<resolved_state_root>/config.toml` if present.

Example TOML (paths must be absolute):

```toml
[state]
root = "<absolute-state-path>"

[study]
roots = ["<absolute-library-path>"]

[retrieval]
max_results = 16

[logging]
level = "INFO"

[mcp]
shadow_read_only = false
```

Stable environment variables:

| Variable | Meaning |
| --- | --- |
| `SYUNE_STATE_ROOT` | Absolute product state root. |
| `SYUNE_CONFIG` | Absolute TOML config path. |
| `SYUNE_STUDY_ROOTS` | OS-path-separated approved existing Study roots. |
| `SYUNE_MAX_RECALL_RESULTS` | MCP recall ceiling, 1 through 32. |
| `SYUNE_LOG_LEVEL` | `ERROR`, `WARNING`, `INFO`, or `DEBUG`. |
| `SYUNE_MCP_SHADOW_READ_ONLY` | `1` removes the Study write tool; `0` keeps the configured surface. |

`syune config show` prints the effective secret-free model; `syune config validate` fails before runtime open for malformed/unknown keys, relative paths, missing Study roots, invalid enums/types, or widened limits. There are no credential fields. Telemetry is fixed OFF and no environment setting enables it.

The default state root is `%LOCALAPPDATA%\SYUNE` on Windows (with a user-profile fallback) and `$XDG_STATE_HOME/syune` or `~/.local/state/syune` elsewhere. CLI state/config/log options are supplied after the leaf command, for example `syune health --state-root C:/state --json`.
