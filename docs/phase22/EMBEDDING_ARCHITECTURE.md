# Embedding architecture

`EmbeddingProvider` exposes batch `embed()` plus an `EmbeddingIdentity`: provider, model, version, dimension, configuration, and derived `space_id`. `DeterministicEmbeddingProvider` remains test-only. `OpenAICompatibleEmbeddingProvider` is production-capable, batches requests, validates response order/count/dimension, has bounded timeout and maps transport/schema failures to explicit unavailability.

Every vector payload carries `embedding_space`. Index configuration checks dimension and probes stored payloads after restart. A mismatch raises `EmbeddingSpaceMismatch`; the required operator response is rebuild into a new collection or clear/re-index the derived store. Spaces are never silently mixed.

Real provider execution: `NOT_EXECUTED — no credentials/endpoint configured`.
