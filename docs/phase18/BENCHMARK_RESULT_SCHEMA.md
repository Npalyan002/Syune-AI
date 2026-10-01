# Benchmark result schema

The normative machine-readable schema is `contracts/schemas/benchmark/v1/result.schema.json`. The runtime additionally validates required fields, cost status, and the invariant `passed + failed == case_count` before raw output is written.

Each result identifies the run timestamp, Git commit and tree state, system and adapter version, model controls, dataset identity and hash, benchmark version, cases and failures, metrics, tokens, latency, cost, storage, warnings, unsupported capabilities, and individual case samples. Nullable values mean unmeasured or inapplicable; they are never silently converted to zero.

Raw files live in `docs/evals/phase18/raw/<run_id>.json`. The writer uses exclusive creation and refuses an existing run ID. Raw evidence is append-only. Derived Markdown and comparisons may be regenerated.
