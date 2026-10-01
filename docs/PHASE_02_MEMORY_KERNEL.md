# SYUNE Phase 02 - Memory Kernel

**Scope:** Python 3.12+ structural memory runtime. **Mode:** L1 ADVISORY. **Package:** `syune`.

## Implemented primitives and relationships

`syune.core` provides typed opaque UUID wrappers (`MemoryId`, `SourceId`, `SourceVersionId`, `ContentBlockId`, `ConceptId`, `ClaimId`, `EvidenceId`, `EpisodeId`, `ProcedureId`, `AssociationId`, `MemoryTraceId`, `ProvenanceId`, `ActivationRunId`), an injectable ID factory, `utc_now` / `require_utc`, and immutable `Confidence` in [0, 1]. Confidence is evidence-state metadata, not calibrated objective probability. Durable objects reject naive or non-UTC timestamps.

`syune.memory` provides a distinct `Source` object, source locators for page/section/time/block/span/region, and `Provenance` carrying source/version identity, optional derivation process and pipeline version, timestamp, and parent provenance IDs. Typed immutable entities are `Concept`, `Claim`, `Evidence`, `Episode`, `Procedure`, `Association`, and `MemoryTrace`. Derived entities and associations require provenance, confidence, creation time, and schema version. Evidence can support, contradict, or qualify one or more claims. Associations connect typed node IDs; optional strength is inert data. A trace references a typed derived entity and keeps encoding time separate from content. `ActivationState` is transient data only.

The shared repository has no Creative/Finance/Systems/Strategy partitions. Source truth and derived records are separate. No mutable label or path is an ID. Objects are immutable; duplicate IDs are rejected instead of silently replacing historical meaning. A later explicit revision policy remains open.

## ADR-0010 additive Observation contract

[ADR-0010](ADR/ADR-0010-observation-memory-entity.md) adds `ObservationId` and immutable `Observation` to the shared Memory Kernel. It stores perceived text, content kind, provenance with exact source locator, observed/created UTC time, schema version, and optional extraction confidence. `None` means extraction confidence is unknown. Neither that value nor a MemoryTrace confidence is an assertion that the perceived text is true.

Observation is a typed non-epistemic memory entity. MemoryTrace may point to ObservationId, and Observation can be structurally stored and associated with any generic memory node. The reference adapter requires an Observation to exist before storing a trace that references it. Memory imports no Study type; a future StudyEncoder can map its operational PerceivedBlock into this Memory entity.

## Repository boundary

`MemoryRepository` is a storage-agnostic protocol with structural put/get/existence, add/get association, and direct association listing. `InMemoryReferenceRepository` is ephemeral and deterministic, intended only for tests and local demonstrations. It validates association endpoint existence and rejects duplicate entity/association IDs. It is not a production persistence choice and exposes no semantic, vector, full-text, ranking, or traversal operation.

## Example

```python
from datetime import datetime, timezone
from syune.core import ClaimId, ConceptId, Confidence, ProvenanceId, SourceId
from syune.memory import Association, Claim, Concept, InMemoryReferenceRepository, Provenance, Source
from syune.core import AssociationId

at = datetime.now(timezone.utc)
source_id = SourceId.new()
provenance = Provenance(ProvenanceId.new(), source_id, at)
source = Source(source_id, "observation", "Example observation", at)
claim = Claim(ClaimId.new(), "A test assertion", provenance, Confidence(0.6), at)
concept = Concept(ConceptId.new(), "A concept", provenance, Confidence(0.7), at)
repo = InMemoryReferenceRepository()
for item in (source, claim, concept):
    repo.put(item)
repo.add_association(Association(
    AssociationId.new(), claim.id, concept.id, "associated_with",
    provenance, Confidence(0.5), at,
))
assert repo.get(claim.id) == claim
```

## Explicit omissions and next boundaries

No Study ingestion, parsing, folder watch, fingerprinting, retrieval, RAG, embeddings, vector or graph database, graph traversal, spreading activation, ranking, LLM/provider call, MCP runtime, agent dispatch, Executive autonomy, or ART-DEP-AI integration exists. Event names are frozen, but payloads and serialization are not; no event data type or bus was introduced. No public wire schema is committed.

PHASE 03 may later create Source/Provenance/Memory objects from studied material. PHASE 04 may later use the structural kernel for candidate generation and activation. Neither behavior is implemented here.

## Open questions

Physical persistence and distribution, source-version storage strategy, explicit revision/invalidation mechanics, association-type vocabulary and strength semantics, event payload shapes, public serialization, and confidence calibration remain deferred. These do not change the frozen Phase 00 architecture.
