# ANN architecture

Qdrant was selected because it is mature, persistent, supports HNSW ANN, batch upsert, deletion, payload filtering, statistics, and health checks, while its HTTP API avoids coupling core contracts to a client SDK. `QdrantVectorIndex` implements create/configure, batch upsert, search with filters, delete, stats, and health. Protocol behavior is tested with a deterministic fake transport; a live Qdrant benchmark was not executed.

The local `LocalVectorIndex` remains a linear, non-production CI adapter. The production architecture removes the required full-vector-scan assumption when Qdrant is configured. Canonical data never lives only in Qdrant.

ANN production path: `READY` architecturally; live ANN scale validation: `NOT_EXECUTED`.
