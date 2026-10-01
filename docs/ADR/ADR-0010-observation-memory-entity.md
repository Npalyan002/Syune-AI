# ADR-0010 - Observation as a Non-Epistemic Memory Entity

**Status:** ACCEPTED
**Baseline:** additive Memory Kernel ontology correction for Phase 03

## Context

Phase 03 must retain perceived source content without declaring that content true. The existing MemoryTrace could reference only Concept, Claim, Evidence, Episode, or Procedure IDs. A literal perceived fragment fits none of those semantic types. Memory cannot depend on Study's PerceivedBlock.

## Decision

Add `ObservationId` and the canonical `Observation` Memory entity. An Observation records only that SYUNE perceived or extracted a representation from a source or environment. It does **not** assert that its content is true. For v1, Observation contains typed identity, text content, content kind, provenance, observed/created UTC timestamps, optional extraction confidence, and schema version. Extraction confidence concerns perception quality, not epistemic truth.

Extend the generic memory-node ID union, MemoryTrace represented-entity union, repository structural put/get, and generic association endpoints to admit ObservationId. MemoryTrace references the Observation, preserving the distinction between perceived representation and encoding history. Memory has no Study import or Study workflow identity.

## Rationale

The safe flow is Source -> Study PerceivedBlock -> Memory Observation -> MemoryTrace -> possible future semantic cognition. Treating source text as Claim would imply assertion; treating it as Concept would invent abstraction. An untyped MemoryTrace payload would weaken type and provenance guarantees. Observation can later represent perception from non-document sources without making Memory depend on a parser.

## Consequences and boundaries

Phase 03 may create Observations from perceived blocks while preserving SourceId and precise locators. It may not automatically create trusted Claims or Concepts. Observation may participate in generic associations, but this ADR introduces no semantic derivation, retrieval, contradiction reasoning, or execution.

This accepted ADR authorizes only the minimal Memory Kernel contract extension. Study parsing, Retrieval, RAG, embeddings, LLM calls, MCP, agent dispatch, and Executive behavior remain outside this patch. The Phase 00 shared-memory, provenance, and L1 ADVISORY invariants remain binding.
