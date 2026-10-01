# ADR-0009 — Runtime Language

**Status:** ACCEPTED
**Applies to:** SYUNE v1
**Decision:** Python 3.12+ with uv for the primary SYUNE runtime.

## Context

SYUNE requires one supported implementation language and dependency workflow for its runtime and public package.

## Decision

- Python is the primary SYUNE runtime language; the minimum supported version is Python 3.12.
- uv is the Python project and dependency manager.
- The primary package namespace is `syune`.
- SYUNE remains provider-agnostic. Foundation models are replaceable processors behind provider boundaries, not the cognitive system itself.
- Rust is reserved solely as an optional performance-acceleration layer for components shown by benchmarks to be latency-critical. It must not become a second cognitive runtime.
- A justified future Rust optimization may use PyO3/maturin or a clean service boundary. Its adoption requires measured benefit and a separate implementation decision.
- TypeScript is not part of the SYUNE core runtime. It may later serve external SDKs, UI, browser, or web integrations.

## Rationale

Python has a mature AI/ML and multimodal ecosystem, broad graph/vector/storage adapters, MCP/REST/SDK tooling, test support, and cross-platform development support. It supports async and background work while allowing performance-critical paths to be isolated and measured. Python 3.12 establishes a clear support floor; uv provides one consistent project and dependency workflow. The `syune` namespace preserves the canonical product identity.

Keeping Rust optional avoids splitting cognitive behavior across two runtimes before profiling demonstrates a need. Keeping TypeScript outside the core preserves one primary runtime while allowing integration surfaces to use the language best suited to them.

## Consequences and boundaries

Any Rust acceleration must have benchmark evidence, a narrowly defined boundary, and no independent runtime authority. Provider adapters continue to respect provider-neutral contracts. See the [Lean v1 architecture](../architecture/LEAN_V1_ARCHITECTURE.md).
