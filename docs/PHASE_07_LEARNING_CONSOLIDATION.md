# SYUNE Phase 07 — Learning and Consolidation v1

**Mode:** L1 ADVISORY. Phase 07 adds explicit experience-dependent plasticity while canonical memory remains authoritative and immutable.

## Contracts and philosophy

`LearningSignal` is an immutable typed record with `LearningSignalId`, one of five v1 kinds, UTC occurrence time, 1–32 typed canonical targets, explicit source identity, idempotency key, `ProvenanceId`, optional correlation/context/outcome, and an explicit human feedback label. Human feedback requires `LearningSource.HUMAN`; it is contextual usefulness feedback and never objective truth. `LearningProposal`, `PlasticityState`, `ConsolidationBatch`, and `ConsolidationResult` are immutable typed contracts. Persistent schemas use version `1` and reject incompatible versions.

The allowed signals are `POSITIVE_OUTCOME`, `NEGATIVE_OUTCOME`, `CO_ACTIVATION`, `HUMAN_FEEDBACK`, and `SOURCE_RETRACTION_NOTICE`. Calls to `LearningService.record()` are the only signal intake. Recall has no learning hook.

## Ledger and overlay

`SQLiteLearningStore` implements the storage-agnostic `LearningLedger` and `PlasticityOverlay` protocols in one configurable SQLite database. It stores immutable signals, target indexes, overlay state, proposals, batches, and append-only audit rows. WAL with `synchronous=NORMAL` provides local crash-safe transactions with good append throughput. Schema mismatch fails explicitly; no migration is attempted.

The overlay holds only bounded utility, salience, and association deltas, a retraction review flag, update count, and timestamp. It never rewrites Observation content, Claim/Evidence confidence, provenance, MemoryTrace, Source, or canonical Association objects. Proposal audit rows trace target → proposal → signal → batch. Rollback restores pre-batch overlay snapshots, retains signals and proposals, and marks the batch/proposals rolled back.

## Policy and consolidation

`PlasticityPolicy` v1 defaults to total bounds `[-0.5,+0.5]`. Positive outcome raw deltas are utility `+0.20`, salience `+0.10`; negative outcome uses `-0.20`, `-0.10`; explicit co-activation uses association `+0.15`; retraction uses utility `-0.30` and sets a review flag. Human labels map to the corresponding positive or negative utility/salience adjustment. Claim/Evidence confidence is untouched.

Each update applies diminishing returns: positive change is `raw × (max-current)/max`; negative change is `raw × (max+current)/max`, followed by a hard clamp. Consolidation deterministically orders pending signals, expands source retraction to provenance-linked entities, produces proposals, and applies overlay/proposal/batch/processed markers in one `BEGIN IMMEDIATE` transaction. Signal and proposal limits are configurable. Batch IDs and proposal IDs are deterministic UUID5 values; checksums cover ordered signals, proposals, and policy version. A processed signal cannot apply twice after restart.

Co-activation v1 strengthens only an existing canonical association between two explicit entity targets. Its overlay relation is named `coactivation:<sorted typed IDs>` and does not invent a semantic relation or canonical edge.

## Retrieval integration

Retrieval defines the read-only `PlasticityView` protocol and default zero-valued `NullPlasticityView`; it does not import `syune.learning` or SQLite. `StorePlasticityView` adapts the durable overlay. Canonical association strength remains the baseline and the bounded learned association delta adjusts traversal strength. Candidate score components separately expose `learned_association`, `learned_salience`, and `learned_utility`. The score remains relevance/activation, never truth probability.

Explicit negative learning can lower ranking but cannot erase an entity; exact ID/source recall remains available. Repeated ordinary recall constructs no signal, changes no overlay, and writes no ledger record.

## Retraction, persistence, and limits

A source retraction notice finds existing derived memory by provenance, reduces its learned utility, and sets the overlay review flag. Canonical source-derived records and confidence remain intact; no Claim is declared false. Restart reopens signals, overlay, proposals, batches, and audit history without reapplication.

There is no decay, generated replay, background daemon, MCP learning mutation tool, LLM/provider call, embedding/vector/graph database, domain profile, Council, agent dispatch, Control Core integration, Executive behavior, or ART-DEP-AI learning integration. Study lifecycle state is unchanged; consolidation here describes explicit adaptive overlay work and does not claim verification or truth.

## Performance

`scripts/benchmark_phase07.py` measures durable append, consolidation p50/p95 across three repetitions, overlay lookup, and Retrieval overhead for 100, 1,000, and 10,000 signals. On Windows / Python 3.12, the validation run observed append throughput of 4,252 / 3,507 / 2,771 signals/s; consolidation p50 of 14.31 / 130.71 / 1,901.17 ms and p95 of 14.56 / 131.09 / 1,931.05 ms; overlay lookup p95 of 0.014 / 0.014 / 0.014 ms; and learned-view retrieval p50 overhead of 0.036 / 0.035 / 0.035 ms. These are local observations, not release thresholds. At 10,000 signals, transactionally recording proposal audit rows dominates consolidation time.
