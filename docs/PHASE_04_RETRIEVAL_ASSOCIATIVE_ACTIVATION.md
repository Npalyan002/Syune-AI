# SYUNE Phase 04 — Retrieval / Associative Activation v1

**Scope:** deterministic, bounded, read-only associative recall over shared MemoryRepository. **Mode:** L1 ADVISORY.

## Cue, seeds, and index

`RecallCue` carries text, exact typed entity IDs, SourceIds, context IDs, optional UTC temporal context, and correlation ID. `RecallRequest` adds a typed run ID and optional result limit. `RetrievalConfig` versions the weights and resource limits. Empty or untyped cues fail explicitly.

`SeedIndex` is a storage-agnostic boundary. `InvertedSeedIndex` version `1` is an in-memory derivative of `MemoryRepository.iter_entities()`, built from Observation content, Concept labels, Claim statements, Episode descriptions, and Procedure steps while retaining entity type, field, and provenance SourceId. Tokens use Unicode word matching and case folding. Exact phrase containment adds a small lexical bonus. Exact IDs and SourceId/provenance links seed directly; lexical hits only seed activation, never determine final ranking. `rebuild()` clears and reconstructs the index from durable memory; `sync()` adds newly stored immutable entities. A cleared or incompatible index fails explicitly. Original source files are unnecessary for rebuilding.

## Associations and transient activation

Retrieval reads canonical Association endpoints through `associations_for`; no graph database is introduced. For each bounded path, `target contribution = source path magnitude × clamp(edge strength or 1, 0, 1) × hop_decay / fanout divisor`. The default hop decay is 0.6 and fanout normalization is off. Each path tracks visited IDs, so a cycle cannot revisit itself; independent paths may accumulate at one existing entity. Depth, fanout, edge, candidate, seed, activation threshold, result, and working-memory limits are configurable. Truncation is reported. `ActivationState` is constructed per request and never persisted.

## Ranking and pattern completion

The score is a weighted sum of visible seed, activation, salience, context, confidence, recency, provenance, and pattern components. Default weights are in `RetrievalConfig`; they are versioned v1 tuning values, not epistemic truth. Confidence is only one factor. Missing confidence contributes zero, not an inferred factual certainty. With no temporal context, recency is a deterministic neutral 0.5; otherwise it decays exponentially by age in days over a 365-day scale. Context uses explicit context IDs, neighboring association support, or a requested SourceId. Pattern completion adds a configured bonus only to an **existing** non-seed neighbor reached from at least two independent seed roots. No entity is invented. Final ordering is score descending, then typed ID/name. A bounded working-memory candidate tuple may optionally prefer distinct SourceIds. This is a retrieval-layer selection, not durable cognitive working memory.

Each `RecallCandidate` retains type, ID, rank, activation, score components, seed reasons, lexical tokens, Association ID paths, SourceId, locator, confidence metadata, and pattern support. Observation and Claim remain distinct. The score estimates recall relevance; it is never truth probability. `RecallResult` includes diagnostics, monotonic timing measurements, truncation metadata, and config version.

## Materialization and safety

An optional injected materialization checker can use the Phase 03A StudyService status for a SourceId. `PARTIAL_MEMORY` or `MISSING_MEMORY` raises `DEGRADED_MATERIALIZATION` instead of returning a healthy recall; no repair occurs. Without that integration, the retrieval layer can only inspect objects present in its repository. Recall does not call MemoryRepository writes or change association strengths, confidence, or long-term salience. There is no LLM, embedding, vector/graph DB, external search, MCP, agent dispatch, or Executive behavior.

## Benchmark baseline and limits

`scripts/benchmark_phase04.py` generates reproducible synthetic chains and reports index build and repeated recall p50/p95 for 100, 1,000, and 10,000 concepts. On Windows 11 / Python 3.12.10 with five repeats, full recall p50 was 0.694, 4.159, and 41.554 ms respectively; p95 was 0.708, 4.161, and 53.192 ms. These are local baseline observations, not release thresholds. In-memory `associations_for` scans direct edges linearly; this is the main scaling limit. No production storage or indexing choice is implied.
