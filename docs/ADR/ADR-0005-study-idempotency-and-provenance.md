# ADR-0005 — Study Idempotency And Provenance

**Status:** Accepted  
**Baseline:** v001 / Baseline 0.1

## Decision

Study uses stable source/version IDs, whole-source hashes, block fingerprints, checkpoints, and bidirectional provenance.

## Rationale

Retry, rename, revision, retraction, and audit must preserve history without duplicate durable memory.

## Consequences and boundaries

No ingestion or parser runtime is authorized in Phase 00.

See [Constitution](../SYUNE_CONSTITUTION_v001.md) and [Blueprint](../SYUNE_BLUEPRINT_v001.md).
