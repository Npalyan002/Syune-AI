# Retrieval fusion

Channel scores are normalized to `[0,1]`. Lexical ranking combines query coverage and BM25 saturation. Semantic scores use cosine similarity. Exact/entity signals are deterministic. Associative activation remains the existing bounded graph signal.

Multi-channel evidence receives deterministic reciprocal-rank-fusion support. Fusion affects relevance ranking only; it cannot override truth, time, or authorization eligibility.
