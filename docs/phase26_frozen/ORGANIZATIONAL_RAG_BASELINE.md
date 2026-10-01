# Organizational RAG Baseline

Organizational RAG is a strong baseline, not a weakened control. It receives exactly the same eligible organizational experience IDs as SYUNE organizational learning; the same model, task prompt, authorization, purpose, temporal cutoff, top-k, and context cap; and equivalent retrieval telemetry. It returns raw episodic evidence rather than promoted procedures.

Ranking must use the repository's existing retrieval stack and frozen parameters. Deduplication may remove byte-identical copies but may not discard contradictory or unfavorable eligible evidence. Both raw evidence and learned procedures are escaped, delimited, and labeled untrusted context. Token-normalized results are primary; unconstrained best effort, if run, is secondary.

