# ADR-0010 - Observation as a Non-Epistemic Memory Entity

**Status:** ACCEPTED
**Applies to:** SYUNE v1 compatibility surface

## Context

The compatibility ingestion surface must retain perceived source content without declaring that content true. A literal perceived fragment is not a claim or concept, and Memory cannot depend on Study's parser model.

## Decision

Add `ObservationId` and the canonical `Observation` Memory entity. An Observation records only that SYUNE perceived or extracted a representation from a source or environment. It does **not** assert that its content is true. For v1, Observation contains typed identity, text content, content kind, provenance, observed/created UTC timestamps, optional extraction confidence, and schema version. Extraction confidence concerns perception quality, not epistemic truth.

Extend the generic memory-node ID union, MemoryTrace represented-entity union, repository structural put/get, and generic association endpoints to admit ObservationId. MemoryTrace references the Observation, preserving the distinction between perceived representation and encoding history. Memory has no Study import or Study workflow identity.

## Rationale

The safe flow is Source -> Study PerceivedBlock -> Memory Observation -> MemoryTrace -> possible future semantic cognition. Treating source text as Claim would imply assertion; treating it as Concept would invent abstraction. An untyped MemoryTrace payload would weaken type and provenance guarantees. Observation can later represent perception from non-document sources without making Memory depend on a parser.

## Consequences and boundaries

Study may create Observations from perceived blocks while preserving SourceId and precise locators. It may not automatically create trusted Claims or Concepts. Observation may participate in generic associations, but this decision grants no semantic derivation or execution authority.
