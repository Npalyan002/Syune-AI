# Changelog

## 1.0.1 - 2026-10-01

- Align package and runtime release metadata on version 1.0.1.
- Add canonical Homepage, Repository, Documentation, Issues and Changelog URLs to
  the package metadata.
- Add a release-triggered, OIDC-based PyPI Trusted Publishing workflow that builds
  the exact stable release tag.
- Add v1.0.1 publication-alignment release documentation.

Runtime semantics and the stable Public API v1 contract are unchanged from 1.0.0.

## 1.0.0 - 2026-09-30

- Promote the validated Lean v1 release candidate to the stable 1.0.0 product contract.
- Preserve governed memory, hybrid retrieval, bounded context, authorization, provenance,
  temporal/version and lifecycle controls, durable audit, ModelGateway, SDK, API and MCP.
- Keep learning, organizational learning, cognition, Council, Planner and Executive
  outside the stable contract and disabled by default.
- Retain the documented single-node, local-linear, provider-validation, audit-integrity,
  Linux-validation, Windows metadata and multi-process limitations.

No product behavior changed from `v1.0.0-rc1`.

## 1.0.0-rc1 - 2026-09-29

- Feature-frozen Lean v1: governed persistent memory, hybrid retrieval, bounded provenance context, temporal/version and lifecycle governance, durable correlated audit, SDK, Lean MCP, and ModelGateway.
- Explicit revision/history and detachable MEMORY_ONLY, CONTEXT_ONLY, MODEL_GATEWAY_ONLY, MEMORY_CONTEXT, and FULL_LEAN modes.
- Stable actionable errors and portable pip installation.
- Research cognition and learning remain experimental and disabled by default.
- Limitations: single-node SQLite, local-linear vectors, no distributed storage, and no new Anthropic/Gemini live validation.
- License the project under Apache License 2.0.

This candidate is not final `v1.0.0`.

This project follows Semantic Versioning while pre-1.0. Breaking public contract or persistent schema behavior increments MAJOR once public stability exists; backward-compatible capability increments MINOR; compatible fixes increment PATCH. Before 1.0, minor releases may still refine public surfaces and must document compatibility.

## 0.1.0 - 2026-09-24

- Establish the first installable standalone SYUNE product baseline.
- Add the `syune` CLI for version, init, health, status, config validation/inspection, upgrade compatibility checks, and MCP launch.
- Add typed configuration, isolated state roots, product metadata, component schema inventory, safe idempotent initialization, and lifecycle-managed runtime bootstrap.
- Preserve all Phase 14 cognitive and supervised-execution semantics.
- Add public API v1, the local synchronous Python SDK, stable public errors and serialization, version negotiation, capability discovery, host protocol, and MCP v1 cognition/Council/planning tools.
- Keep supervised execution outside the public v1 SDK and MCP surface.

No earlier semantic versions are asserted. The license decision that remained open in
the 0.1.0 development line is resolved for 1.0.0-rc1 with Apache License 2.0.
