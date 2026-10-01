# Lean architecture

The active flow is `host → SDK → authorization → retrieval → context → optional ModelGateway`, backed by memory, provenance, temporal/version metadata, lifecycle, and audit. Context consumes governed recall candidates. No learning, council, planner, executive, or cognitive transaction occurs on this path. The detailed diagram is in [LEAN_V1_ARCHITECTURE.md](LEAN_V1_ARCHITECTURE.md).
