# Lean V1 API

Primary SDK operations are `remember`, `memory_get`, `recall`, `context`, `forget`, `history`, `audit`, and `model`. `study` and `source_status` support file ingestion. `health`, `status`, and `capabilities` are operational surfaces.

`context(ContextRequest(...))` returns bounded rendered text plus typed items, source IDs, relevance scores, truth-state metadata, and temporal/provenance validity. `model(ModelExecutionRequest(...))` requires an explicitly attached configured `ModelGateway`; no provider is silently selected.

`cognize`, `council`, and `plan` remain source-compatible but lazily load research modules and warn. They are reported unavailable in lean capability discovery.
