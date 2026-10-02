# Known limitations and post-v1 roadmap

- Single-node SQLite; no distributed or multi-node guarantee.
- WAL readers and ordinary writers are supported; high-contention multi-process writes are not a claimed topology.
- Default vector backend is local-linear, not production ANN.
- Anthropic and Gemini ModelGateway transports are not implemented. Concrete OpenAI and
  OpenAI-compatible adapters are internal deployment components rather than turnkey
  stable public configuration surfaces.
- Stable Study handles individual TXT, Markdown, and text-based PDF files only. There is
  no folder/repository ingestion, OCR, web ingestion, or stable multimodal provider.
- Learning and research cognition are excluded from v1 and disabled.
- Compatibility learning/execution databases remain in fresh schema-v1 state but are not opened by Lean startup.
- Windows rapid metadata replacement remains a post-v1 investigation.
- Audit is durable but not cryptographically tamper-evident.

Post-v1 candidates are production ANN, distributed storage, additional provider
validation, compatibility-store cleanup, and the Windows metadata edge case. No dates.
