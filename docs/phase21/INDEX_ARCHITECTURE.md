# Index architecture

The inverted index uses postings and BM25-style scoring rather than a query-time full memory scan. `sync()` incrementally adds unseen immutable memories and updates the vector index without rebuilding existing entries. Rebuild remains deterministic after restart because memory is authoritative.

`LocalVectorIndex` is a deterministic development backend and performs linear vector search. It is explicitly replaceable by an ANN implementation through `VectorIndex`; 10K–100M scale points were not executed and must not be inferred. Eligibility checks prevent stale, superseded, invalidated, expired, or access-restricted hits from reaching context even if a derived index still contains an ID.
