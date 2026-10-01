# Dependency audit

Runtime dependencies remain `mcp>=2,<3` and `pypdf>=6,<7`. MCP is transport-only and PDF is Study-only; neither belongs to memory/retrieval/context internals. No provider SDK is required because adapters use provider-neutral contracts and injected transports.

The default runtime import graph excludes learning, council, cognition, executive, and cognitive transactions. SQLite is standard-library storage. Development uses pytest only. Recommendation: move MCP and PDF to extras in the next packaging-major release; doing so now would break the published install contract.
