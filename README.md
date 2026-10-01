# SYUNE

**Stable release:** 1.0.0 · **Public API:** v1

SYUNE is a governed memory, context and model-execution runtime for AI systems.
It provides persistent memory with authorization, provenance, temporal/version controls,
lifecycle rules, bounded context, durable audit, and a provider-neutral model gateway.

SYUNE is not an AGI, truth engine, autonomous organization, or self-learning enterprise
brain. Research cognition, Council, Planner, Executive and learning code is retained for
compatibility and research but disabled by default.

## Install and run

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install syune==1.0.0
.\.venv\Scripts\syune.exe init --state-root C:\syune-state
.\.venv\Scripts\python.exe -m syune.quickstart --state-root C:\syune-state
```

From a source checkout, replace the install command with `python -m pip install .`.
Python integrations begin with `Syune.open(state_root=...)`. An external agent requests
governed context, sends it to its chosen model, and retains the SYUNE audit correlation.
The optional stdio server is `syune mcp serve`.

Deployment is single-node SQLite. The default vector backend is local-linear, not a
production ANN service. Read [installation](docs/installation.md),
[quickstart](docs/QUICKSTART.md), [public API](docs/PUBLIC_API_V1.md),
[backup/restore](docs/backup_restore.md), [threat model](docs/threat_model.md), and
[known limitations](docs/known_limitations.md).

SYUNE is licensed under the [Apache License 2.0](LICENSE).
