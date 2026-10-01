# Phase 22 benchmark delta

PRE is `docs/evals/phase22/pre/PRE_PHASE_22.json`; POST scale evidence is `docs/evals/phase22/post/POST_PHASE_22_SCALE.json`.

The deterministic reference remains: task success, recall, and authorized useful recall 100%; precision 61.90%; p95 0.6302 ms; zero permission violations, cross-agent leakage, and false-memory selections. Phase 22 scale results are not merged into that small deterministic result.

At 100K, lexical p95 was 96.29 ms versus 5.50 ms at 10K; recall stayed 100% and precision 20% on the scale workload. This exposes an unresolved broad-postings path, not ANN performance.
