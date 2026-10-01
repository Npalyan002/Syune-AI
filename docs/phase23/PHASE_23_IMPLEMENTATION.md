# Phase 23 implementation

Phase 23 implements gap `G12` with an orthogonal lifecycle envelope, durable SQLite state/events, an in-memory parity adapter, lifecycle-aware incremental indexes, explicit archive retrieval, deterministic retention, and a bounded cursor maintenance service.

Runtime flow is `put/register -> ACTIVE -> reinforce/consolidate -> archive/forget -> explicit purge`. Truth, temporal validity, authorization, and lifecycle remain independent gates. Ordinary retrieval admits only `ACTIVE`; an authorized explicit-ID request may set `include_archived`.

The implementation is intentionally policy machinery, not Verified Experience Learning. It does not infer strategies or causal rules.
