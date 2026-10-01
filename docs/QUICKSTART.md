# SYUNE quickstart

Requirements: Python 3.12 or newer (below 4) and a writable state directory. `uv` is optional.

Create a clean environment and install the published candidate (or a locally built wheel):

```powershell
py -3.12 -m venv .quickstart-venv
.\.quickstart-venv\Scripts\python.exe -m pip install syune==1.0.1
.\.quickstart-venv\Scripts\syune.exe --version
```

Initialize the default user-local state and verify it:

```powershell
$state = Join-Path $env:TEMP "syune-v1-quickstart"
.\.quickstart-venv\Scripts\syune.exe init --state-root $state
.\.quickstart-venv\Scripts\python.exe -m syune.quickstart --state-root $state
.\.quickstart-venv\Scripts\syune.exe health --state-root $state
```

The workflow performs remember, governed context with FULL provenance, revision,
CURRENT and AS_OF retrieval, history, lifecycle, durable audit, shutdown, restart,
and persisted retrieval. It requires no model credential. On POSIX use the
equivalent `.quickstart-venv/bin/python` and `.quickstart-venv/bin/syune` paths.

For an explicit isolated instance, choose any writable absolute path:

```powershell
$state = Join-Path $env:TEMP "my-isolated-syune-state"
syune init --state-root $state
syune health --state-root $state
```

To launch the Lean local stdio MCP gateway:

```powershell
$env:SYUNE_STATE_ROOT = $state
syune mcp serve
```

MCP is optional. Startup and health require no network, cloud credentials, or model provider. Attach a configured `ModelGateway` only when generation is needed. Local state remains after package removal. No reset/delete-all command exists.
