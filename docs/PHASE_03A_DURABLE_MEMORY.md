# SYUNE Phase 03A — Durable Memory Reference Store

**Scope:** local reference persistence for the existing shared Memory Kernel. **Mode:** L1 ADVISORY.

Phase 03 stored Study status durably while its in-memory MemoryRepository lost derived objects after restart. Phase 03A adds `SQLiteMemoryRepository` behind the same structural `MemoryRepository` contract. The in-memory adapter remains available. Memory entities and their ontology are unchanged, and `syune.memory` has no Study dependency.

## Adapter and internal format

The adapter uses only Python `sqlite3`, with a configurable path (recommended `.syune/state/memory.sqlite3`). A `metadata` row records internal schema version `1`; incompatible or unversioned existing schemas fail on open. One `entities` table holds Source, Observation, Concept, Claim, Evidence, Episode, Procedure, and MemoryTrace. One `associations` table holds direct structural edges. There are no domain-specific stores. The deterministic tagged JSON payload is private to this adapter and is not a public serialization contract. ActivationState remains transient.

Typed IDs, UTC timestamps, tuples, enum polarity, Confidence, SourceLocator, Provenance, and association metadata round-trip exactly. Duplicate IDs fail; Evidence claim, MemoryTrace target, and Association endpoint references are checked like the in-memory adapter. `put_many` is an atomic logical batch in SQLite and rolls back on failure. Study uses it for each Observation/MemoryTrace pair; it records the derived-ID ledger only after the pair succeeds, and transitions to ENCODED only after all ledgered objects and the Source are present. This is local transaction ordering, not a distributed transaction between the two SQLite databases.

## Study consistency

`StudyService.materialization_status(revision_id)` compares the StudyRegistry ledger with MemoryRepository structural existence. Its states are `MATERIALIZED`, `PARTIAL_MEMORY`, `MISSING_MEMORY`, and `NOT_ENCODED`. A duplicate returns its classification plus this materialization state; missing or partial memory is explicitly exposed rather than reported as healthy. Automatic repair is deferred. Reopening both stores needs no reparsing to rehydrate memory by typed ID. Existing in-memory Study tests still run, while durable integration uses the SQLite adapter through dependency injection.

## Limits

SQLite is a single-process local reference implementation and does not select final production persistence. The two SQLite stores do not share a distributed transaction; a crash after memory commit but before Study ledger/status commit can leave extra durable objects, which deterministic IDs and retry can reconcile. Missing-memory detection handles the reverse inconsistency. Public wire serialization, migration beyond schema rejection, replication, graph/vector storage, Retrieval, semantic interpretation, and source retraction propagation remain deferred. Observation remains a record of perception, not truth.
