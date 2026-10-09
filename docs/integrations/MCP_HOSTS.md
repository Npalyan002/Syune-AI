# MCP host integration

SYUNE 1.1 prepares a persistent integration and validates it before you touch host configuration:

```console
pip install syune==2.0.0
syune setup
syune doctor
```

For automation, choose a host explicitly:

```console
syune setup --host codex
syune setup --host claude-code
syune setup --host claude-desktop
syune setup --host generic
syune setup --host python
```

Add `--state-root <absolute-path>` to select a different persistent state. The default is
`%LOCALAPPDATA%\SYUNE\default` on Windows, `$XDG_STATE_HOME/syune/default` when
`XDG_STATE_HOME` is set, and `~/.local/state/syune/default` otherwise.

For MCP hosts, setup saves and displays a verified tuple with the absolute Python
executable, arguments `-m syune.gateway.mcp`, and `SYUNE_STATE_ROOT` set to the
initialized absolute state path. Setup performs a real stdio initialization, calls
`syune_health`, and verifies all eight Lean tools. It never edits host configuration.

## Host Model Mode

The host continues to perform reasoning. SYUNE supplies governed memory and bounded
context over MCP. No separate LLM API key is required for the seven memory/context tools.
`syune_model` needs ModelGateway only when provider execution is explicitly configured.

## Register the generated tuple

Use the saved JSON artifact and the host's current official mechanism:

- Codex: [official MCP documentation](https://developers.openai.com/codex/mcp)
- Claude Code: [official MCP documentation](https://docs.anthropic.com/en/docs/claude-code/mcp)
- Claude Desktop: [official Anthropic MCP documentation](https://docs.anthropic.com/en/docs/mcp)
- Generic clients: map `command`, `args`, and `env` to the stdio server schema.

Host schemas can change independently, so SYUNE does not guess or mutate them.

## Python SDK

`syune setup --host python` initializes persistent state and writes a minimal SDK
example. It does not create MCP configuration.

## Doctor

`syune doctor` checks package version, effective state, readability, writability,
compatibility, the executable, a real stdio handshake, health, and the canonical 8/8
tool surface. `syune doctor --json` supports automation. Missing ModelGateway
configuration is optional and does not fail doctor.
