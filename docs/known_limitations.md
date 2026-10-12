# Known limitations and roadmap

- Single-node SQLite; no distributed or multi-node guarantee.
- WAL readers and ordinary writers are supported; high-contention multi-process writes are not a claimed topology.
- Default vector backend is local-linear, not production ANN.
- Native semantic retrieval uses deterministic feature hashing (`deterministic-token-v1`,
  64 dimensions). Add and Search do not invoke a generative LLM, but the organizer's
  interpretation of this vectorizer under Agent Memory Leaderboard embedding policy
  remains under review.
- Anthropic and Gemini ModelGateway transports are not implemented. Concrete OpenAI and
  OpenAI-compatible adapters are internal deployment components rather than turnkey
  stable public configuration surfaces.
- Stable Study handles individual TXT, Markdown, and text-based PDF files only. There is
  no folder/repository ingestion, OCR, web ingestion, or stable multimodal provider.
- Learning and research cognition remain experimental or disabled and are outside the
  stable v2 product boundary.
- Compatibility learning/execution databases remain in fresh schema-v1 state but are not opened by Lean startup.
- Windows rapid metadata replacement remains an open investigation.
- Audit is durable but not cryptographically tamper-evident.
- The AML adapter implements Textual Memory only. It has no official AML score or
  leaderboard ranking, and native retrieval can legitimately return fewer than `top_k`.

Roadmap candidates are production ANN, distributed storage, additional provider
validation, compatibility-store cleanup, and the Windows metadata edge case. No dates.
