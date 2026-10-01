# Migration plan

- P0: route all future structured cognition, decision, planning and knowledge-construction calls
  through `ModelGateway`; do not add direct provider transport.
- P1: evaluate provider-backed perception migration when it needs generative structured output.
- P2: share transport/accounting primitives with embedding and reranking integrations where useful;
  do not force non-generative workloads into the text gateway.

Phase 26–28 runners remain frozen benchmark-only evidence.
