# Lean V1 deployment

Install the package, run `syune init --state-root <absolute-path>`, then `syune health`. Configure `[study] roots` only when file ingestion is needed. Default feature flags: model gateway on; semantic retrieval, learning, and research cognition off.

Provider credentials and routes belong in host-owned ModelGateway construction. SYUNE does not enable telemetry. Back up the state root atomically; memory and registry SQLite files are the active lean stores. Legacy learning/execution files in schema-v1 state are compatibility artifacts and are not opened by default.
