# Truncation stress

The deterministic matrix proves finish reason `length` is classified as `TRUNCATED_OUTPUT` before
parsing, persisted, retried only when policy permits, and terminates finitely. Phase 29.2 added a
live 25–150% capacity curve across plain, native and compact strategies: all calls through 75%
committed, while every 100–150% call terminated as `TRUNCATED_OUTPUT` from provider finish metadata.
See `LIVE_TRUNCATION_STRESS.md` and `evidence/truncation_live_v1/report.json`.
