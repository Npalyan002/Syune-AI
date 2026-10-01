# Reranking and context optimization

The initial reranker is deterministic and cheap: existing relevance components, associative activation, entity/context fit, learned bounded adjustments, and channel fusion. Verification is used for eligibility/preference, never as a relevance substitute.

Working context applies relative-score trimming, exact duplicate suppression, revision suppression, and the configured capacity. The full authorized candidate list remains available for explanations. `INSUFFICIENT_EVIDENCE` is returned when no sufficiently supported candidate survives.
