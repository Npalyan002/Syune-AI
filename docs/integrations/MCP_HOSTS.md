# MCP host integration

SYUNE can connect to Codex, Claude Code, Claude Desktop, and generic stdio MCP clients.
The verified SYUNE-side tuple is:

- command: the absolute path to `syune`
- arguments: `mcp`, `serve`
- environment: `SYUNE_STATE_ROOT` set to an initialized absolute state path

An equivalent tuple uses the absolute Python executable with arguments
`-m`, `syune.gateway.mcp`.

## Before connecting

```console
pip install syune==1.0.3
syune init --state-root /absolute/path/to/state
```

Then register one of the generic JSON patterns in the [Lean MCP contract](../MCP_V1.md).
The server does not initialize state automatically.

## Host guidance

| Host | SYUNE support | Host-specific responsibility |
| --- | --- | --- |
| Codex | Generic stdio MCP | Register the tuple using current Codex MCP documentation |
| Claude Code | Generic stdio MCP | Register the tuple using current Claude Code MCP documentation |
| Claude Desktop | Generic stdio MCP | Register the tuple using current Claude Desktop MCP documentation |
| Other MCP clients | Generic stdio MCP | Map command, arguments, and environment to the client's server configuration |

SYUNE does not prescribe or guess third-party UI locations, configuration filenames, or
client commands. Those interfaces can change independently. Client configuration reload
or restart behavior is also host-specific.

## Verified by SYUNE

- both canonical entry points;
- local stdio transport;
- the eight-tool Lean server;
- `SYUNE_STATE_ROOT` configuration;
- protocol initialization and handshake;
- memory/context operation without separate provider credentials.

## Not asserted by SYUNE

- native adapters for every agent framework;
- a particular host's current UI or configuration-file location;
- automatic host configuration editing;
- Study/file ingestion through Lean MCP.

The host continues to perform reasoning with its own model access. ModelGateway is
optional and is used only when an application explicitly delegates model execution to
SYUNE.
