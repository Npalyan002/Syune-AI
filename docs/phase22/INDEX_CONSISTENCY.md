# Index consistency

States are `SYNCED`, `LAGGING`, `DEGRADED`, and `REBUILD_REQUIRED`. Health reports backend, canonical/indexed counts, lag, embedding failures, ANN failures, fallback count, and synchronization latency.

New records use batch embedding/upsert without rebuilding existing entries. Lexical entries remain usable if semantic indexing fails. Superseded, invalidated, or newly restricted records may remain physically present in a derived index, but canonical truth, time, and authorization gates remove them before context.

Restart reconnects to a persistent Qdrant collection after space validation or rebuilds derived indexes from canonical memory. Partial failure is `DEGRADED`; space mismatch requires rebuild.
