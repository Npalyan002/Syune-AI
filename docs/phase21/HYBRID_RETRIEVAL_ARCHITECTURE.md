# Hybrid retrieval architecture

`Retriever`, `EmbeddingProvider`, and `VectorIndex` are replaceable contracts. `RetrieverCandidate` records memory ID, channel, raw/normalized score, reason, and rank. Production recall exposes `found_by`, fusion score, truth/temporal status, authorization decision, and final rank.

Flow: deterministic query analysis → routed candidate generation → temporal/truth eligibility → authorization → normalized fusion/reranking → duplicate/revision context suppression → bounded working context. Unauthorized content never enters working context or candidate output.
