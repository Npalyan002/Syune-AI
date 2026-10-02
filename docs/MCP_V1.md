# Lean MCP v1

The canonical Lean MCP server is a local stdio process. Start it with either:

```console
syune mcp serve
```

```console
python -m syune.gateway.mcp
```

Both commands expose the same eight-tool Lean surface:

| Tool | Meaning |
| --- | --- |
| `syune_health` | Health, version, mode, and capability information |
| `syune_remember` | Store governed plain-text memory |
| `syune_context` | Assemble bounded, governed context |
| `syune_revise` | Create a revision of existing memory |
| `syune_forget` | Apply the governed forget lifecycle operation |
| `syune_history` | Read revision history |
| `syune_audit` | Read bounded audit events |
| `syune_model` | Execute through an explicitly attached ModelGateway |

The server does not expose Study, cognition, Council, Planner, or Executive operations.
Older compatibility servers may still exist in source for compatibility testing, but
they are experimental/deprecated and are not the canonical Lean MCP v1 interface.

## Initialize state

The MCP server does not implicitly initialize state. Initialize an absolute state root:

```console
syune init --state-root /absolute/path/to/state
```

The stable SDK/MCP boundary requires an absolute state-root path.

## Generic host configuration

Register this verified MCP tuple in a host that accepts stdio servers:

```json
{
  "command": "/absolute/path/to/syune",
  "args": ["mcp", "serve"],
  "env": {
    "SYUNE_STATE_ROOT": "/absolute/path/to/initialized-state"
  }
}
```

Or invoke the installed module with the environment's Python executable:

```json
{
  "command": "/absolute/path/to/python",
  "args": ["-m", "syune.gateway.mcp"],
  "env": {
    "SYUNE_STATE_ROOT": "/absolute/path/to/initialized-state"
  }
}
```

SYUNE verifies the executable entry points, arguments, environment contract, stdio
transport, and MCP handshake. Where this tuple is registered and how configuration is
reloaded are host-specific; consult the host's current MCP documentation.

## Model access

Memory and context use in an MCP host requires no separate LLM API credential from
SYUNE. The host performs reasoning using its own model access. Only `syune_model`
requires an explicitly attached ModelGateway and configured provider.

See [MCP host integration](integrations/MCP_HOSTS.md) for Codex, Claude Code, Claude
Desktop, and generic-host guidance.
