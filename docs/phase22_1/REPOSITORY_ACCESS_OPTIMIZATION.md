# Repository access optimization

`MemoryRepository` now exposes `get_many`, `entity_count`, `changes_since`, and `replace`. The in-memory adapter records monotonic changes; SQLite stores a durable `change_journal`. Inserts, security changes, supersession, invalidation, and generic updates use the same lightweight mechanism.

Recall resolves only candidate IDs and bounded truth peers. Full `iter_entities` remains for audit, migration, explicit rebuild fallback, and truth-event reporting.
