# Phase 22.1 implementation

`PHASE_22_1_STATUS = PASS`

Ordinary recall no longer materializes canonical snapshots. Repository change cursors drive incremental sync; the retrieval index maintains bounded truth groups and supersession lookups. Lexical planning starts with selective postings, caps candidates, and uses bounded top-K. Health uses repository counters. Recovery rebuild remains an explicit O(N) operation.

Mutable policy/truth replacements are journaled and re-indexed. Canonical authorization and temporal checks remain final gates. Index/query methods use a re-entrant lock for same-process consistency.
