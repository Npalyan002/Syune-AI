# Contradiction model

Deterministic classification uses structured `fact_key`, `fact_value`, `context_key`, and validity intervals:

- differing contexts: `CONTEXTUAL_DIFFERENCE`
- non-overlapping validity: `REVISION`
- same key/context/time with unequal values: `CONTRADICTION`
- insufficient structure: `POSSIBLE_CONTRADICTION`
- equal values: `NONE`

No insertion-time LLM is used. Current retrieval exposes the contradiction status and, when equally verified conflicting records exist, uses the most recently recorded eligible item as current belief while retaining both history and an audit event.
