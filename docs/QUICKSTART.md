# SYUNE quickstart

> Quickstart is a temporary demo. For persistent integration, run syune setup and syune doctor.

Requirements: Python 3.12 or newer (below 4) and a writable state directory. `uv` is optional.

Create a clean environment and install the published candidate (or a locally built wheel):

```powershell
py -3.12 -m venv .quickstart-venv
.\.quickstart-venv\Scripts\python.exe -m pip install syune==1.1.0
.\.quickstart-venv\Scripts\syune.exe --version
```

Run the quickstart directly. On first use it initializes a demo state under the system
temporary directory, then safely reuses that state on later runs:

```powershell
.\.quickstart-venv\Scripts\python.exe -m syune.quickstart
```

To keep demo state in a chosen location, pass an absolute or relative path. The
quickstart wrapper resolves relative CLI paths before it calls the strict SDK boundary:

```powershell
.\.quickstart-venv\Scripts\python.exe -m syune.quickstart --state-root .\syune-state
```

The workflow performs remember, governed context with FULL provenance, revision,
CURRENT and AS_OF retrieval, history, lifecycle, durable audit, shutdown, restart,
and persisted retrieval. It reports whether state was newly created and confirms clean
close. It requires no model credential. On POSIX use the equivalent
`.quickstart-venv/bin/python` and `.quickstart-venv/bin/syune` paths.

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

For host configuration, see [MCP host integration](integrations/MCP_HOSTS.md). For
single-file TXT, Markdown, and text-PDF ingestion through the SDK, see
[Study and ingestion](INGESTION.md).
