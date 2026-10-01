# ADR-0005 — Study Idempotency And Provenance

**Status:** Accepted  
**Applies to:** SYUNE v1 compatibility surface

## Decision

Study uses stable source/version IDs, whole-source hashes, block fingerprints, checkpoints, and bidirectional provenance.

## Rationale

Retry, rename, revision, retraction, and audit must preserve history without duplicate durable memory.

## Consequences and boundaries

Ingestion remains an explicit caller action. It does not silently delete sources, duplicate durable observations on retry, or promote perceived content to factual truth. This compatibility surface is outside the minimal Lean workflow but remains supported by the v1 package.
