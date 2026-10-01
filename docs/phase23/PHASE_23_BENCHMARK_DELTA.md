# Phase 23 benchmark delta

PRE preserves the Phase 21/22.1 deterministic baseline: task success 100%, recall 100%, precision 61.90%, abstention 100%, false-memory selections 0, temporal and contradiction accuracy 100%, permission violations 0, cross-agent leakage 0, and 100K lexical P95 0.1015 ms.

POST lifecycle-specific synthetic replay preserved returned hits and context size while reducing active/index records by 58.74%; P95 changed from 22.426 ms (unmanaged replay) to 7.204 ms (managed replay). These workload numbers are not comparable to the Phase 22.1 single-token scale fixture. Full task-quality regression evidence remains the inherited deterministic baseline pending a working pytest environment.
